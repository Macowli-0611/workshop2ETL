#!/usr/bin/env python3
"""
Captures Airflow UI screenshots for the reliability evidence (Tests A-E)
and the Metabase dashboard screenshot.

Runs in the official Playwright image attached to the compose network:
    docker run --rm --network workshop2etl_workshop2_net -v "$PWD":/work -w /work \
        mcr.microsoft.com/playwright/python:v1.47.0-jammy \
        python scripts/capture_airflow_evidence.py

Airflow is reached as http://airflow:8080 (service name). Local-only setup:
the UI runs with SIMPLE_AUTH_MANAGER_ALL_ADMINS, so no login is needed.
"""

import os
from playwright.sync_api import sync_playwright

BASE = os.getenv("AIRFLOW_URL", "http://airflow:8080")
METABASE = os.getenv("METABASE_URL", "http://metabase:3000")
DAG = "reliable_music_pipeline"
EVID = "docs/evidence"


def shot(page, url, out, *, graph=False, wait_text=None, clip_selector=None, scroll_log_bottom=False):
    page.goto(url, wait_until="networkidle")
    if wait_text:
        try:
            page.get_by_text(wait_text).first.wait_for(timeout=20000)
        except Exception:  # still capture; the image is reviewed manually
            print(f"[!] '{wait_text}' not visible on {url}")
    if graph:
        page.get_by_role("button", name="Show Graph (Press g)").click()
        page.wait_for_selector(".react-flow__node", timeout=20000)
        page.wait_for_timeout(1500)
        fit = page.locator("button.react-flow__controls-fitview")
        if fit.count():
            fit.click()
            page.wait_for_timeout(800)
    page.wait_for_timeout(1200)
    if scroll_log_bottom:  # show the final ERROR lines instead of library start-up noise
        page.mouse.move(1200, 800)
        for _ in range(15):
            page.mouse.wheel(0, 3000)
            page.wait_for_timeout(150)
        page.wait_for_timeout(800)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if clip_selector:
        page.locator(clip_selector).first.screenshot(path=out)
    else:
        page.screenshot(path=out)
    print("[+]", out)


def ensure_grid(page):
    btn = page.get_by_role("button", name="Show Grid (Press g)")
    if btn.count():
        btn.click()
        page.wait_for_timeout(800)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1600, "height": 950}, device_scale_factor=1.5,
                                color_scheme="light")
        # First visit issues the session token and redirects to the home page
        page.goto(BASE, wait_until="networkidle")
        page.wait_for_timeout(3000)
        run = lambda r: f"{BASE}/dags/{DAG}/runs/{r}"  # noqa: E731
        task = lambda r, t: f"{BASE}/dags/{DAG}/runs/{r}/tasks/{t}"  # noqa: E731

        # Test A - successful run
        shot(page, run("test_a_success"), f"{EVID}/test_a_success/a1_grid_task_states.png", wait_text="7 Task Instances")
        shot(page, run("test_a_success"), f"{EVID}/test_a_success/a2_graph_success.png", graph=True)
        ensure_grid(page)
        shot(page, task("test_a_success", "load_dw"), f"{EVID}/test_a_success/a3_load_dw_log.png", wait_text="RECONCILIATION")

        # Test B - controlled critical failure
        shot(page, run("test_b_controlled_failure"), f"{EVID}/test_b_controlled_failure/b1_grid_failed_run.png", wait_text="7 Task Instances")
        shot(page, run("test_b_controlled_failure"), f"{EVID}/test_b_controlled_failure/b2_graph_failed_run.png", graph=True)
        ensure_grid(page)
        shot(page, task("test_b_controlled_failure", "validate_grammys_raw"),
             f"{EVID}/test_b_controlled_failure/b3_failed_task_log.png", wait_text="BATCH CONTEXT",
             scroll_log_bottom=True)

        # Test C - safe rerun
        shot(page, run("test_c_safe_rerun"), f"{EVID}/test_c_safe_rerun/c1_grid_rerun.png", wait_text="7 Task Instances")
        shot(page, task("test_c_safe_rerun", "load_dw"), f"{EVID}/test_c_safe_rerun/c2_load_dw_log.png", wait_text="RECONCILIATION")

        # Test D - selective retry of a transient failure
        shot(page, run("test_d_transient_retry"), f"{EVID}/test_d_selective_retry/d1_grid_retry_run.png", wait_text="7 Task Instances")
        shot(page, f"{task('test_d_transient_retry', 'extract_grammys')}?try_number=1",
             f"{EVID}/test_d_selective_retry/d2_attempt1_failed_log.png", wait_text="BATCH CONTEXT")
        shot(page, f"{task('test_d_transient_retry', 'extract_grammys')}?try_number=2",
             f"{EVID}/test_d_selective_retry/d3_attempt2_success_log.png", wait_text="BATCH CONTEXT")

        # Test E - prepared gate blocks the load
        shot(page, run("test_e_prepared_gate"), f"{EVID}/test_e_prepared_gate/e1_graph_prepared_gate.png", graph=True)
        ensure_grid(page)
        shot(page, task("test_e_prepared_gate", "validate_prepared"),
             f"{EVID}/test_e_prepared_gate/e2_validate_prepared_log.png", wait_text="BATCH CONTEXT",
             scroll_log_bottom=True)

        # DAG overview: all runs in the grid
        shot(page, f"{BASE}/dags/{DAG}", f"{EVID}/dag_overview_all_runs.png")

        # BI dashboard (Metabase public link written by scripts/setup_metabase.py)
        uuid_file = f"{EVID}/kpi/metabase_public_uuid.txt"
        if os.path.exists(uuid_file):
            uuid = open(uuid_file).read().strip()
            page.set_viewport_size({"width": 1600, "height": 1500})
            page.goto(f"{METABASE}/public/dashboard/{uuid}", wait_until="networkidle")
            page.wait_for_timeout(8000)
            page.screenshot(path=f"{EVID}/kpi/metabase_dashboard.png", full_page=True)
            print("[+]", f"{EVID}/kpi/metabase_dashboard.png")
        browser.close()


if __name__ == "__main__":
    main()
