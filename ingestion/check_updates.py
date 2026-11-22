import json
import os
import sys
from pathlib import Path

import requests

from fetch_indicators import BASE_URL, COUNTRIES, INDICATORS

STATE_FILE = Path("state/last_updated.json")


def latest_dates():
    """Ask the API when each indicator was last updated. One row each, so it's quick."""
    dates = {}
    for indicator in INDICATORS:
        url = f"{BASE_URL}/country/{';'.join(COUNTRIES)}/indicator/{indicator}"
        response = requests.get(url, params={"format": "json", "per_page": 1}, timeout=60)
        response.raise_for_status()
        dates[indicator] = response.json()[0]["lastupdated"]
    return dates


def main():
    new = latest_dates()
    old = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}

    changed = [i for i in new if new[i] != old.get(i)]
    for i in changed:
        print(f"{i}: {old.get(i, 'never seen')} -> {new[i]}")
    if not changed:
        print("No new data since the last successful run.")

    # Only record the dates when asked, after the pipeline has succeeded
    if "--save" in sys.argv:
        STATE_FILE.parent.mkdir(exist_ok=True)
        STATE_FILE.write_text(json.dumps(new, indent=2) + "\n")
        print(f"Saved dates to {STATE_FILE}")

    # Tell GitHub Actions the result. Does nothing when run on your laptop.
    if "GITHUB_OUTPUT" in os.environ:
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"changed={'true' if changed else 'false'}\n")


if __name__ == "__main__":
    main()