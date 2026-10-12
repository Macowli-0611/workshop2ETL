#!/usr/bin/env python3
"""
Builds the BI dashboard in Metabase on top of the Data Warehouse (dw_music_analytics).

Run inside the Airflow container once `docker compose up` has started Metabase:
    docker compose exec airflow python /opt/airflow/scripts/setup_metabase.py

Idempotent: on first run it completes the Metabase setup with MB_ADMIN_EMAIL /
MB_ADMIN_PASSWORD from .env; later runs log in, archive the previous dashboard and
recreate it. Every question is native SQL over the DW analytical views
(vw_kpi1_audio_profile, vw_kpi2_genre_uplift, vw_kpi3_decade_trends), never over CSV files.
A public (read-only, local) link is enabled so the dashboard can be captured as evidence.
"""

import os
import sys
import time
import requests

MB = os.getenv("METABASE_URL", "http://metabase:3000")
DASHBOARD_NAME = "Workshop-2 · Spotify x Grammy KPIs (DW)"
COLLECTION_NAME = "Workshop-2 ETL"


class MB_API:
    def __init__(self, base):
        self.base = base
        self.s = requests.Session()

    def call(self, method, path, **kw):
        r = self.s.request(method, f"{self.base}/api{path}", timeout=60, **kw)
        if r.status_code >= 400:
            sys.exit(f"[!] {method} {path} -> {r.status_code}: {r.text[:400]}")
        return r.json() if r.content else {}


def wait_ready(api):
    for _ in range(90):
        try:
            if requests.get(f"{MB}/api/health", timeout=5).json().get("status") == "ok":
                return
        except requests.RequestException:
            pass
        time.sleep(4)
    sys.exit("[!] Metabase did not become healthy")


def authenticate(api):
    email, password = os.environ["MB_ADMIN_EMAIL"], os.environ["MB_ADMIN_PASSWORD"]
    props = api.call("GET", "/session/properties")
    token = props.get("setup-token")
    if token and not props.get("has-user-setup"):
        res = api.call("POST", "/setup", json={
            "token": token,
            "user": {"email": email, "password": password, "first_name": "Workshop", "last_name": "Admin",
                     "site_name": "Workshop-2 ETL"},
            "prefs": {"site_name": "Workshop-2 ETL", "site_locale": "en", "allow_tracking": False},
        })
        print("[+] Metabase initial setup completed")
        session_id = res["id"]
    else:
        session_id = api.call("POST", "/session", json={"username": email, "password": password})["id"]
    api.s.headers["X-Metabase-Session"] = session_id


def ensure_database(api):
    details = {
        "host": os.getenv("POSTGRES_HOST", "postgres"),
        "port": int(os.getenv("POSTGRES_PORT", "5432")),
        "dbname": os.getenv("DW_DB_NAME", "dw_music_analytics"),
        "user": os.environ["POSTGRES_USER"],
        "password": os.environ["POSTGRES_PASSWORD"],
        "ssl": False,
    }
    for db in api.call("GET", "/database").get("data", []):
        if db["details"].get("dbname") == details["dbname"]:
            # keep the stored credentials in sync with .env (e.g. after a password rotation)
            api.call("PUT", f"/database/{db['id']}", json={"details": details})
            return db["id"]
    db = api.call("POST", "/database", json={
        "engine": "postgres",
        "name": "DW Music Analytics (PostgreSQL)",
        "details": details,
    })
    print(f"[+] DW connection registered in Metabase (id={db['id']})")
    return db["id"]


def ensure_collection(api):
    for c in api.call("GET", "/collection"):
        if c.get("name") == COLLECTION_NAME and not c.get("archived"):
            return c["id"]
    return api.call("POST", "/collection", json={"name": COLLECTION_NAME, "color": "#509EE3"})["id"]


def archive_previous(api, collection_id):
    for item in api.call("GET", f"/collection/{collection_id}/items").get("data", []):
        kind = {"dashboard": "dashboard", "card": "card"}.get(item["model"])
        if kind:
            api.call("PUT", f"/{kind}/{item['id']}", json={"archived": True})


def card(api, db_id, collection_id, name, description, sql, display, viz):
    return api.call("POST", "/card", json={
        "name": name,
        "description": description,
        "collection_id": collection_id,
        "display": display,
        "dataset_query": {"type": "native", "native": {"query": sql}, "database": db_id},
        "visualization_settings": viz,
    })["id"]


CARDS = [
    # (name, description, sql, display, viz, (row, col, size_x, size_y))
    ("KPI-01 · Popularity uplift of Grammy winners",
     "RQ-01: mean Spotify popularity of awarded tracks minus catalog mean (distinct tracks).",
     """SELECT ROUND(MAX(avg_popularity) FILTER (WHERE award_status='Grammy Winner')
                   - MAX(avg_popularity) FILTER (WHERE award_status='General Catalog'), 2) AS popularity_uplift
        FROM vw_kpi1_audio_profile""",
     "scalar", {"scalar.suffix": " pts"}, (0, 0, 6, 3)),
    ("Awarded tracks matched in the catalog",
     "Distinct Spotify tracks matched to a Grammy award by the integration contract.",
     "SELECT n_tracks FROM vw_kpi1_audio_profile WHERE award_status = 'Grammy Winner'",
     "scalar", {}, (0, 6, 6, 3)),
    ("KPI-03 · Explicit share of awarded tracks, 2010s",
     "RQ-03: % of distinct awarded tracks flagged explicit in the latest decade.",
     "SELECT pct_explicit FROM vw_kpi3_decade_trends ORDER BY decade DESC LIMIT 1",
     "scalar", {"scalar.suffix": " %"}, (0, 12, 6, 3)),
    ("Catalog tracks in the DW",
     "Distinct tracks in dim_track loaded by load_dw.",
     "SELECT COUNT(*) AS tracks FROM dim_track",
     "scalar", {}, (0, 18, 6, 3)),
    ("KPI-01 · Audio profile: Grammy winners vs catalog",
     "RQ-01: mean audio features per award status (vw_kpi1_audio_profile).",
     """SELECT award_status, f.feature, f.value
        FROM vw_kpi1_audio_profile,
             LATERAL (VALUES ('Danceability', avg_danceability), ('Energy', avg_energy),
                             ('Valence', avg_valence), ('Acousticness', avg_acousticness)) AS f(feature, value)
        ORDER BY f.feature, award_status""",
     "bar", {"graph.dimensions": ["feature", "award_status"], "graph.metrics": ["value"],
             "graph.show_values": True, "graph.y_axis.title_text": "Mean value (0-1)"}, (3, 0, 12, 7)),
    ("KPI-03 · Explicit and collaboration share by decade",
     "RQ-03: % of distinct awarded tracks that are explicit / collaborations (vw_kpi3_decade_trends).",
     "SELECT decade, pct_explicit, pct_collaboration FROM vw_kpi3_decade_trends ORDER BY decade",
     "line", {"graph.dimensions": ["decade"], "graph.metrics": ["pct_explicit", "pct_collaboration"],
              "graph.show_values": True, "graph.y_axis.title_text": "% of awarded tracks"}, (3, 12, 12, 7)),
    ("KPI-02 · Popularity uplift by genre (>= 5 awarded tracks)",
     "RQ-02: winner mean popularity minus catalog mean, per genre (vw_kpi2_genre_uplift).",
     """SELECT genre_name, popularity_uplift FROM vw_kpi2_genre_uplift
        WHERE n_winner_tracks >= 5 ORDER BY popularity_uplift DESC LIMIT 12""",
     "row", {"graph.dimensions": ["genre_name"], "graph.metrics": ["popularity_uplift"],
             "graph.show_values": True}, (10, 0, 12, 8)),
    ("KPI-02 · Genre detail with sample sizes",
     "RQ-02 detail: sample sizes behind each genre comparison.",
     """SELECT genre_name, n_winner_tracks, n_catalog_tracks, avg_pop_winners, avg_pop_catalog, popularity_uplift
        FROM vw_kpi2_genre_uplift WHERE n_winner_tracks >= 5 ORDER BY popularity_uplift DESC""",
     "table", {}, (10, 12, 12, 8)),
]


def main():
    api = MB_API(MB)
    wait_ready(api)
    authenticate(api)
    db_id = ensure_database(api)
    api.call("POST", f"/database/{db_id}/sync_schema")
    collection_id = ensure_collection(api)
    archive_previous(api, collection_id)

    dashcards = []
    for i, (name, desc, sql, display, viz, (row, col, sx, sy)) in enumerate(CARDS, start=1):
        cid = card(api, db_id, collection_id, name, desc, sql, display, viz)
        dashcards.append({"id": -i, "card_id": cid, "row": row, "col": col, "size_x": sx, "size_y": sy,
                          "parameter_mappings": [], "visualization_settings": {}})

    dash = api.call("POST", "/dashboard", json={
        "name": DASHBOARD_NAME, "collection_id": collection_id,
        "description": "All questions query the dimensional Data Warehouse dw_music_analytics (analytical views).",
    })
    api.call("PUT", f"/dashboard/{dash['id']}", json={"dashcards": dashcards, "width": "full"})

    api.call("PUT", "/setting/enable-public-sharing", json={"value": True})
    public = api.call("POST", f"/dashboard/{dash['id']}/public_link")
    print(f"[+] Dashboard id={dash['id']} with {len(dashcards)} cards")
    print(f"[+] Admin URL : http://localhost:{os.getenv('METABASE_PORT', '3000')}/dashboard/{dash['id']}")
    print(f"[+] Public URL: http://localhost:{os.getenv('METABASE_PORT', '3000')}/public/dashboard/{public['uuid']}")
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "evidence", "kpi",
                           "metabase_public_uuid.txt"), "w") as f:
        f.write(public["uuid"] + "\n")


if __name__ == "__main__":
    main()
