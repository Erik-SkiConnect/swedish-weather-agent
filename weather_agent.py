#!/usr/bin/env python3
"""
Swedish Weather Agent
======================

Fetches a 3-day min/max temperature forecast for 10 predefined Swedish
regions from the Open-Meteo API and appends the results to a cumulative
CSV file.

If this project folder lives inside your OneDrive (or Google Drive /
Dropbox) folder, the CSV will sync to the cloud automatically -- no
extra upload code needed.

Usage:
    python weather_agent.py

Logging:
    All runs are logged to weather_agent.log (in the same directory),
    including successes, row counts, and any errors.
"""

import csv
import io
import logging
import os
import sys
from datetime import datetime, timezone

import requests

from regions import REGIONS

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------

CSV_FILENAME = "weather_forecast_sweden.csv"
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
CSV_FIELDNAMES = ["date", "region", "postal_codes", "min_c", "max_c"]

LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "weather_agent.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("weather_agent")


# ----------------------------------------------------------------------
# Step 1: Fetch forecast data from Open-Meteo
# ----------------------------------------------------------------------

def fetch_forecast(region: dict) -> list[dict]:
    """
    Call Open-Meteo for a single region and return a list of row dicts
    (one per forecast day) ready to be written to the CSV.
    """
    params = {
        "latitude": region["lat"],
        "longitude": region["lon"],
        "daily": "temperature_2m_max,temperature_2m_min",
        "forecast_days": 3,
        "timezone": "Europe/Stockholm",
    }

    response = requests.get(OPEN_METEO_URL, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    daily = data["daily"]
    dates = daily["time"]
    mins = daily["temperature_2m_min"]
    maxs = daily["temperature_2m_max"]

    rows = []
    for date, tmin, tmax in zip(dates, mins, maxs):
        rows.append({
            "date": date,
            "region": region["name"],
            "postal_codes": region["postal_codes"],
            "min_c": round(tmin, 1),
            "max_c": round(tmax, 1),
        })
    return rows


def fetch_all_regions() -> list[dict]:
    """
    Fetch forecast rows for all configured regions.
    Raises if any single region fails (fail-fast so the run is logged
    as an error and no partial data is appended).
    """
    all_rows = []
    for region in REGIONS:
        log.info("Fetching forecast for region: %s (%.2f, %.2f)",
                 region["name"], region["lat"], region["lon"])
        rows = fetch_forecast(region)
        all_rows.extend(rows)
        log.info("  -> got %d rows", len(rows))
    return all_rows


# ----------------------------------------------------------------------
# Step 2: CSV handling (local read/append/write)
# ----------------------------------------------------------------------

def csv_bytes_to_rows(csv_bytes: bytes) -> list[dict]:
    """Parse CSV file content (as bytes) into a list of row dicts."""
    text = csv_bytes.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))
    return list(reader)


def rows_to_csv_bytes(rows: list[dict]) -> bytes:
    """Serialize a list of row dicts into CSV file content (bytes)."""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDNAMES)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return output.getvalue().encode("utf-8")


def append_rows(existing_rows: list[dict], new_rows: list[dict]) -> list[dict]:
    """
    Append new rows to existing rows.

    De-duplicates on (date, region) so re-running the agent on the same
    day does not create duplicate entries -- existing rows for the same
    date/region are replaced with the freshly fetched values.
    """
    key = lambda r: (r["date"], r["region"])
    existing_by_key = {key(r): r for r in existing_rows}

    for row in new_rows:
        existing_by_key[key(row)] = row

    # Keep stable ordering: sort by date then region name
    combined = sorted(existing_by_key.values(), key=lambda r: (r["date"], r["region"]))
    return combined


# ----------------------------------------------------------------------
# Main pipeline
# ----------------------------------------------------------------------

def main() -> int:
    start = datetime.now(timezone.utc)
    log.info("=" * 60)
    log.info("Weather agent run started at %s UTC", start.isoformat())

    local_csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), CSV_FILENAME)

    try:
        # 1. Fetch new forecast data
        new_rows = fetch_all_regions()
        log.info("Fetched %d total rows (%d regions x 3 days)", len(new_rows), len(REGIONS))

        # 2. Load existing CSV (if present)
        if os.path.exists(local_csv_path):
            with open(local_csv_path, "rb") as f:
                existing_rows = csv_bytes_to_rows(f.read())
            log.info("Loaded %d existing rows from local CSV", len(existing_rows))
        else:
            existing_rows = []
            log.info("No existing local CSV found -- starting fresh")

        # 3. Merge / append
        combined_rows = append_rows(existing_rows, new_rows)
        log.info("CSV now contains %d total rows after merge", len(combined_rows))

        # 4. Write updated CSV locally (syncs to OneDrive automatically
        #    if this folder is inside your OneDrive directory)
        csv_bytes = rows_to_csv_bytes(combined_rows)
        with open(local_csv_path, "wb") as f:
            f.write(csv_bytes)
        log.info("Wrote updated CSV to %s", local_csv_path)

    except Exception:
        log.exception("Weather agent run FAILED")
        return 1

    end = datetime.now(timezone.utc)
    log.info("Weather agent run completed successfully in %.1fs", (end - start).total_seconds())
    return 0


if __name__ == "__main__":
    sys.exit(main())
    