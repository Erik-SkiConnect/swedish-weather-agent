#!/usr/bin/env python3
"""
Offline test for weather_agent.py -- mocks the Open-Meteo HTTP call so we
can verify the CSV parsing, merge/dedupe, and write logic without network
access.
"""

import json
import os
import sys
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import weather_agent
from regions import REGIONS


def fake_response(region):
    """Build a fake Open-Meteo JSON response for a given region."""
    base_min = round(region["lat"] / 10 - 3, 1)
    base_max = round(region["lat"] / 10 + 5, 1)
    return {
        "daily": {
            "time": ["2026-06-15", "2026-06-16", "2026-06-17"],
            "temperature_2m_min": [base_min, base_min + 0.5, base_min - 0.3],
            "temperature_2m_max": [base_max, base_max + 1.2, base_max - 0.8],
        }
    }


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def fake_get(url, params=None, timeout=None):
    # Find region by lat/lon
    for region in REGIONS:
        if abs(region["lat"] - params["latitude"]) < 1e-6 and abs(region["lon"] - params["longitude"]) < 1e-6:
            return FakeResponse(fake_response(region))
    raise ValueError("Unknown region in fake_get")


def main():
    test_dir = "/home/claude/weather_agent_test"
    os.makedirs(test_dir, exist_ok=True)
    csv_path = os.path.join(test_dir, weather_agent.CSV_FILENAME)
    if os.path.exists(csv_path):
        os.remove(csv_path)

    with mock.patch.object(weather_agent, "requests") as mock_requests:
        mock_requests.get.side_effect = fake_get

        # --- Run 1: fresh CSV ---
        new_rows = weather_agent.fetch_all_regions()
        print(f"Run 1: fetched {len(new_rows)} rows (expected {len(REGIONS) * 3})")
        assert len(new_rows) == len(REGIONS) * 3

        existing_rows = []
        combined = weather_agent.append_rows(existing_rows, new_rows)
        csv_bytes = weather_agent.rows_to_csv_bytes(combined)
        with open(csv_path, "wb") as f:
            f.write(csv_bytes)
        print(f"Run 1: wrote {len(combined)} rows to {csv_path}")
        assert len(combined) == 30

        # --- Run 2: re-run same "day" -> should dedupe, not double ---
        with open(csv_path, "rb") as f:
            existing_rows = weather_agent.csv_bytes_to_rows(f.read())
        new_rows_2 = weather_agent.fetch_all_regions()
        combined_2 = weather_agent.append_rows(existing_rows, new_rows_2)
        print(f"Run 2 (same data, re-run): {len(combined_2)} rows (expected 30, no duplicates)")
        assert len(combined_2) == 30

        # --- Run 3: simulate a new day's data appended ---
        # Modify fake data slightly to represent a new forecast date set
        global fake_response
        orig_fake_response = fake_response

        def fake_response_day2(region):
            r = orig_fake_response(region)
            r["daily"]["time"] = ["2026-06-16", "2026-06-17", "2026-06-18"]
            return r

        with mock.patch(__name__ + ".fake_response", side_effect=fake_response_day2):
            pass  # patching module-level function used via closure won't apply; do inline instead

        # Simpler: directly construct new_rows for day2 manually
        new_rows_3 = []
        for region in REGIONS:
            for date in ["2026-06-16", "2026-06-17", "2026-06-18"]:
                new_rows_3.append({
                    "date": date,
                    "region": region["name"],
                    "postal_codes": region["postal_codes"],
                    "min_c": 1.0,
                    "max_c": 10.0,
                })

        with open(csv_path, "rb") as f:
            existing_rows = weather_agent.csv_bytes_to_rows(f.read())
        combined_3 = weather_agent.append_rows(existing_rows, new_rows_3)
        # Expect union of dates 06-15..06-18 = 4 days * 10 regions = 40 rows
        print(f"Run 3 (new day appended): {len(combined_3)} rows (expected 40)")
        assert len(combined_3) == 40

        csv_bytes_3 = weather_agent.rows_to_csv_bytes(combined_3)
        with open(csv_path, "wb") as f:
            f.write(csv_bytes_3)

    print("\nFinal CSV sample (first 6 lines):")
    with open(csv_path) as f:
        for i, line in enumerate(f):
            if i >= 6:
                break
            print(" ", line.rstrip())

    print("\nAll tests passed.")


if __name__ == "__main__":
    main()
