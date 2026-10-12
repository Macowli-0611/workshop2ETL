#!/usr/bin/env python3
"""
Builds the standalone defense deck: docs/presentation/presentation.html

- Layout and content: scripts/presentation_template.html
- Images: evidence screenshots (docs/evidence/...), the Metabase dashboard and the
  figures saved in notebooks/data_profiling.ipynb. They are cropped to the relevant
  region, re-encoded as WebP and embedded as data URIs, so the deck is a single file
  that works offline. Clicking a screenshot in the deck opens the full image.

Placeholders in the template:
    %%IMG:<key>%%   cropped / slide-sized image
    %%FULL:<key>%%  full image for the zoom view

Requires Pillow (installed in the Airflow image):
    python3 scripts/build_presentation.py
"""

import base64
import io
import json
import os
import re

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EV = os.path.join(ROOT, "docs", "evidence")
TEMPLATE = os.path.join(ROOT, "scripts", "presentation_template.html")
OUTPUT = os.path.join(ROOT, "docs", "presentation", "presentation.html")

# key -> (source, crop box as fractions (left, top, right, bottom) or None)
IMAGES = {
    "a1": ("test_a_success/a1_grid_task_states.png", (0.04, 0.0, 0.80, 0.66)),
    "a2": ("test_a_success/a2_graph_success.png", None),
    "a2_crop": ("test_a_success/a2_graph_success.png", (0.05, 0.38, 0.70, 0.66)),
    "a3": ("test_a_success/a3_load_dw_log.png", None),
    "a3_crop": ("test_a_success/a3_load_dw_log.png", (0.245, 0.46, 0.66, 0.70)),
    "b2": ("test_b_controlled_failure/b2_graph_failed_run.png", None),
    "b2_crop": ("test_b_controlled_failure/b2_graph_failed_run.png", (0.05, 0.38, 0.70, 0.66)),
    "b3": ("test_b_controlled_failure/b3_failed_task_log.png", None),
    "b3_crop": ("test_b_controlled_failure/b3_failed_task_log.png", (0.245, 0.668, 0.70, 0.79)),
    "c2": ("test_c_safe_rerun/c2_load_dw_log.png", None),
    "c2_crop": ("test_c_safe_rerun/c2_load_dw_log.png", (0.245, 0.46, 0.66, 0.70)),
    "d2": ("test_d_selective_retry/d2_attempt1_failed_log.png", None),
    "d2_crop": ("test_d_selective_retry/d2_attempt1_failed_log.png", (0.245, 0.25, 0.60, 0.56)),
    "d3": ("test_d_selective_retry/d3_attempt2_success_log.png", None),
    "d3_crop": ("test_d_selective_retry/d3_attempt2_success_log.png", (0.245, 0.25, 0.60, 0.585)),
    "e1": ("test_e_prepared_gate/e1_graph_prepared_gate.png", None),
    "e1_crop": ("test_e_prepared_gate/e1_graph_prepared_gate.png", (0.05, 0.38, 0.70, 0.66)),
    "e2": ("test_e_prepared_gate/e2_validate_prepared_log.png", None),
    "e2_crop": ("test_e_prepared_gate/e2_validate_prepared_log.png", (0.245, 0.668, 0.70, 0.79)),
    "overview": ("dag_overview_all_runs.png", None),
    "overview_crop": ("dag_overview_all_runs.png", (0.045, 0.12, 0.228, 0.40)),
    "mb": ("kpi/metabase_dashboard.png", (0.0, 0.0, 1.0, 0.83)),
    "lk": ("kpi/looker_studio_dashboard.png", None),
    "prof1": ("notebook:0", None),
    "prof_missing": ("notebook:0", (0.0, 0.0, 0.345, 1.0)),
    "prof_duration": ("notebook:0", (0.335, 0.0, 0.67, 1.0)),
}

MAX_WIDTH = 2000
QUALITY = 88


def notebook_figures():
    """Returns the PNG figures saved in the executed profiling notebook, in order."""
    with open(os.path.join(ROOT, "notebooks", "data_profiling.ipynb"), encoding="utf-8") as f:
        nb = json.load(f)
    figs = []
    for cell in nb["cells"]:
        for out in cell.get("outputs", []):
            png = out.get("data", {}).get("image/png")
            if png:
                figs.append(base64.b64decode(png))
    return figs


def load(source: str) -> Image.Image:
    if source.startswith("notebook:"):
        figs = notebook_figures()
        idx = int(source.split(":")[1])
        if idx >= len(figs):
            raise SystemExit("Execute notebooks/data_profiling.ipynb first (no saved figures found).")
        return Image.open(io.BytesIO(figs[idx])).convert("RGB")
    return Image.open(os.path.join(EV, source)).convert("RGB")


def encode(img: Image.Image) -> str:
    if img.width > MAX_WIDTH:
        img = img.resize((MAX_WIDTH, round(img.height * MAX_WIDTH / img.width)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "WEBP", quality=QUALITY, method=6)
    return "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def render_images() -> dict:
    cache, uris = {}, {}
    for key, (source, box) in IMAGES.items():
        if source not in cache:
            cache[source] = load(source)
        img = cache[source]
        if box:
            w, h = img.size
            img = img.crop((round(box[0] * w), round(box[1] * h), round(box[2] * w), round(box[3] * h)))
        uris[key] = encode(img)
    return uris


def build():
    with open(TEMPLATE, encoding="utf-8") as f:
        html = f.read()
    uris = render_images()

    def sub(match):
        key = match.group(2)
        if key not in uris:
            raise SystemExit(f"Unknown image key in template: {key}")
        return uris[key]

    html = re.sub(r"%%(IMG|FULL):([a-z0-9_]+)%%", sub, html)
    # Test E figures come from the run's integration report
    with open(os.path.join(EV, "runs", "test_e_prepared_gate", "integration_report.json"), encoding="utf-8") as f:
        integ = json.load(f)["integration"]
    html = html.replace("%%E_MATCHED%%", f"{integ['matched_spotify_rows']:,}")
    html = html.replace("%%E_RATE%%", f"{integ['match_rate_rows_pct']:.2f}%")
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Generated {os.path.relpath(OUTPUT, ROOT)} ({len(html) / 1e6:.1f} MB, {len(uris)} images)")


if __name__ == "__main__":
    build()
