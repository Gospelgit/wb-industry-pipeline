import json
from datetime import date
from pathlib import Path

import duckdb
import requests

from fetch_indicators import COUNTRIES  # reuse the same 16 countries

URL = "https://api.worldbank.org/v2/country/" + ";".join(COUNTRIES)
OUT_DIR = Path("data/reference")
DB_PATH = "data/warehouse.duckdb"


def fetch():
    """Get details for all 16 countries in one request."""
    response = requests.get(URL, params={"format": "json", "per_page": 100}, timeout=60)
    response.raise_for_status()
    payload = response.json()
    if len(payload) < 2 or "message" in payload[0]:
        raise ValueError(f"API error: {payload}")
    return payload


def to_float(text):
    """Coordinates come as text, and can be empty."""
    return float(text) if text else None


def main():
    payload = fetch()

    # Save the untouched response, like we do for indicators
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_file = OUT_DIR / f"countries_{date.today().isoformat()}.json"
    out_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    rows = [
        (
            c["id"],
            c["iso2Code"],
            c["name"],
            c["region"]["value"].strip(),
            c["incomeLevel"]["id"],
            c["incomeLevel"]["value"],
            c["lendingType"]["value"],
            c["capitalCity"],
            to_float(c["latitude"]),
            to_float(c["longitude"]),
        )
        for c in payload[1]
    ]

    con = duckdb.connect(DB_PATH)
    # Small reference table, so we replace it whole on every run
    con.execute("""
        CREATE OR REPLACE TABLE raw_countries (
            country_iso3    VARCHAR,
            country_iso2    VARCHAR,
            country_name    VARCHAR,
            region          VARCHAR,
            income_level_id VARCHAR,
            income_level    VARCHAR,
            lending_type    VARCHAR,
            capital_city    VARCHAR,
            latitude        DOUBLE,
            longitude       DOUBLE
        )
    """)
    con.executemany("INSERT INTO raw_countries VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)

    print(f"Saved {out_file} and loaded {len(rows)} countries")
    con.sql("""
        SELECT country_iso3, country_name, income_level, lending_type
        FROM raw_countries
        ORDER BY country_name
    """).show()
    con.close()


if __name__ == "__main__":
    main()