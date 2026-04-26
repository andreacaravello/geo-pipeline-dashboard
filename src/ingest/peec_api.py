"""
Peec AI REST API ingest — designed for GitHub Actions / CI environments.

This script is the CI counterpart to src/ingest/peec.py (which uses
Strawberry AI + MCP in interactive mode). It calls Peec's REST API directly
using a PEEC_API_KEY secret, so the GitHub Actions workflow can run fully
unattended on a daily cron schedule.

Business rules (same as peec.py, never violate):
  - Brand prompts are ALWAYS segregated; never mixed into SoV calculations.
  - Active-prompts-only filter: list_prompts first, then filter brand report
    to those prompt_ids. This prevents archived prompts from distorting SoV.

Environment variables (all required unless noted):
  PEEC_API_KEY     - Peec REST API key (store as GitHub Secret)
  PEEC_PROJECT_ID  - Peec project ID (defaults to project ID)
  DAYS_BACK        - days of history to pull (default: 30)

Outputs:
  data/processed/peec_non_brand.csv   - non-brand prompts only
  data/processed/peec_brand_only.csv  - brand prompts only
  data/processed/ingestion_log.txt    - appended run log
"""

from __future__ import annotations

import os
import sys
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)

PEEC_BASE_URL = "https://api.peec.ai/v1"
PROJECT_ID = os.environ.get("PEEC_PROJECT_ID", "")
DAYS_BACK = int(os.environ.get("DAYS_BACK", "30"))
API_KEY = os.environ.get("PEEC_API_KEY", "")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _auth_headers() -> dict[str, str]:
    if not API_KEY:
        log.error("PEEC_API_KEY is not set. Add it as a GitHub Secret named PEEC_API_KEY.")
        sys.exit(1)
    return {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}


def _date_range() -> tuple[str, str]:
    end = datetime.now(tz=timezone.utc).date()
    start = end - timedelta(days=DAYS_BACK)
    return str(start), str(end)


def fetch_active_prompt_ids(client: httpx.Client) -> list[str]:
    """List active (non-archived) prompt IDs. Required first step."""
    resp = client.get(f"{PEEC_BASE_URL}/projects/{PROJECT_ID}/prompts")
    resp.raise_for_status()
    data = resp.json()
    prompts = data if isinstance(data, list) else data.get("items", data.get("prompts", []))
    active_ids = [
        p["id"] for p in prompts
        if not p.get("archived", False) and not p.get("is_archived", False)
    ]
    log.info("Found %d active prompts (filtered from %d total)", len(active_ids), len(prompts))
    return active_ids


def fetch_brand_report(client, prompt_ids, start_date, end_date):
    """Fetch brand report filtered to active prompts only."""
    params = {
        "project_id": PROJECT_ID,
        "start_date": start_date,
        "end_date": end_date,
        "dimensions": ["topic_id", "date", "brand_name", "brand_id"],
    }
    if prompt_ids:
        params["prompt_ids"] = ",".join(prompt_ids)
    resp = client.get(f"{PEEC_BASE_URL}/projects/{PROJECT_ID}/brand-report", params=params)
    if resp.status_code == 405:
        resp = client.post(
            f"{PEEC_BASE_URL}/projects/{PROJECT_ID}/brand-report",
            json={**params, "prompt_ids": prompt_ids},
        )
    resp.raise_for_status()
    data = resp.json()
    rows = data if isinstance(data, list) else data.get("items", data.get("rows", []))
    log.info("Fetched %d rows (%s -> %s)", len(rows), start_date, end_date)
    return rows


def segregate_and_write(rows, processed_dir):
    """Split rows into brand-only and non-brand CSVs."""
    if not rows:
        pd.DataFrame().to_csv(processed_dir / "peec_non_brand.csv", index=False)
        pd.DataFrame().to_csv(processed_dir / "peec_brand_only.csv", index=False)
        return 0, 0
    df = pd.DataFrame(rows)
    if "brand_prompt" in df.columns:
        raw = df["brand_prompt"].astype(str).str.strip().str.lower()
        df["brand_prompt"] = raw.isin({"true", "1", "yes", "y", "t"})
    elif "is_brand_prompt" in df.columns:
        raw = df["is_brand_prompt"].astype(str).str.strip().str.lower()
        df["brand_prompt"] = raw.isin({"true", "1", "yes", "y", "t"})
        df = df.drop(columns=["is_brand_prompt"])
    else:
        df["brand_prompt"] = False
    brand_mask = df["brand_prompt"].fillna(False).astype(bool)
    non_brand = df.loc[brand_mask].copy()
    brand = df.loc[brand_mask].copy()
    non_brand.to_csv(processed_dir / "peec_non_brand.csv", index=False)
    brand.to_csv(processed_dir / "peec_brand_only.csv", index=False)
    log.info("Wrote %d non-brand + %d brand rows", len(non_brand), len(brand))
    return len(non_brand), len(brand)


def append_log(processed_dir, non_brand, brand):
    ts = datetime.now(tz=timezone.utc).isoformat(timespec="seconds")
    line = (f"{ts}\tpeec_api\tinput_files=0\t"
            f"output_rows={non_brand + brand}\t"
            f"outputs=peec_non_brand.csv,peec_brand_only.csv\n")
    with (processed_dir / "ingestion_log.txt").open("a", encoding="utf-8") as f:
        f.write(line)


def main():
    root = _repo_root()
    processed_dir = root / "data" / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)
    headers = _auth_headers()
    start_date, end_date = _date_range()
    log.info("Pulling Peec SoV: project=%s  %s -> %s", PROJECT_ID, start_date, end_date)
    with httpx.Client(headers=headers, timeout=60) as client:
        prompt_ids = fetch_active_prompt_ids(client)
        rows = fetch_brand_report(client, prompt_ids, start_date, end_date)
    non_brand_count, brand_count = segregate_and_write(rows, processed_dir)
    append_log(processed_dir, non_brand_count, brand_count)
    log.info("Done. %d non-brand + %d brand rows written.", non_brand_count, brand_count)


if __name__ == "__main__":
    main()
