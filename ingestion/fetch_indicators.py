import json
import time
from datetime import date
from pathlib import Path

import requests

BASE_URL = "https://api.worldbank.org/v2"

COUNTRIES = [
    "BEN", "BFA", "CPV", "CIV", "GMB", "GHA", "GIN", "GNB",
    "LBR", "MLI", "MRT", "NER", "NGA", "SEN", "SLE", "TGO",
]

INDICATORS = [
    "NV.IND.MANF.ZS",
    "NV.IND.TOTL.ZS",
    "EG.ELC.ACCS.ZS",
    "SL.IND.EMPL.ZS",
    "NY.GDP.MKTP.KD",
    "TX.VAL.MANF.ZS.UN",
]

YEARS = "2000:2025"
PER_PAGE = 200  # small on purpose, so we see paging work


def get_page(indicator, page):
    """Fetch one page, retrying if the network blips."""
    url = f"{BASE_URL}/country/{';'.join(COUNTRIES)}/indicator/{indicator}"
    params = {"format": "json", "date": YEARS, "per_page": PER_PAGE, "page": page}

    for attempt in range(1, 4):
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            payload = response.json()
            break
        except requests.RequestException as error:
            print(f"  attempt {attempt} failed: {error}")
            if attempt == 3:
                raise
            time.sleep(5 * attempt)

    # The API sometimes hides errors inside a normal response
    if len(payload) < 2 or "message" in payload[0]:
        raise ValueError(f"API error for {indicator}: {payload}")

    return payload


def fetch_indicator(indicator, out_dir):
    """Fetch every page for one indicator and save each page."""
    page, pages = 1, 1
    while page <= pages:
        payload = get_page(indicator, page)
        meta, rows = payload[0], payload[1] or []
        pages = meta["pages"]

        out_file = out_dir / f"{indicator}_page{page}.json"
        out_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"  page {page}/{pages}: {len(rows)} rows")
        page += 1
    return meta["total"]


def main():
    out_dir = Path("data/raw") / date.today().isoformat()
    out_dir.mkdir(parents=True, exist_ok=True)

    for indicator in INDICATORS:
        print(f"Fetching {indicator}")
        total = fetch_indicator(indicator, out_dir)
        print(f"  done, {total} rows in total")


if __name__ == "__main__":
    main()