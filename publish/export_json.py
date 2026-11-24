import json
from datetime import datetime, timezone
from pathlib import Path

import duckdb

DB_PATH = "data/warehouse.duckdb"
OUT_DIR = Path("public_data")
STATE_FILE = Path("state/last_updated.json")

# One JSON file per table the website needs
EXPORTS = {
    "countries": """
        SELECT country_iso3, country_name, region, income_level,
               latitude, longitude,
               ecowas_first_year, ecowas_last_year, is_current_ecowas_member
        FROM dim_country
        ORDER BY country_name
    """,
    "indicators": """
        SELECT indicator_id, short_name, indicator_name, unit, theme
        FROM dim_indicator
        ORDER BY theme, short_name
    """,
    "values": """
        SELECT country_iso3, indicator_id, year,
               round(value, 4) AS value,
               is_provisional, is_low_coverage, is_ecowas_member
        FROM fct_indicator_values
        ORDER BY indicator_id, country_iso3, year
    """,
    "forecasts": """
        SELECT country_iso3, indicator_id, year, forecast, low, high,
               model, trained_through
        FROM fct_indicator_forecasts
        ORDER BY indicator_id, country_iso3, year
    """,
    "jumps": """
        SELECT country_iso3, indicator_id, year,
               round(change, 2) AS change,
               round(score, 1)  AS score,
               is_reviewed, review_note
        FROM indicator_jumps
        WHERE is_unusual
        ORDER BY abs(score) DESC
    """,
    "coverage": """
        SELECT country_iso3, indicator_id, years_with_data, years_total,
               coverage_pct, first_year_with_data, last_year_with_data, low_coverage
        FROM indicator_coverage
        ORDER BY indicator_id, country_iso3
    """,
}


def main():
    OUT_DIR.mkdir(exist_ok=True)
    con = duckdb.connect(DB_PATH, read_only=True)

    row_counts = {}
    for name, query in EXPORTS.items():
        out_file = OUT_DIR / f"{name}.json"
        con.execute(f"COPY ({query}) TO '{out_file.as_posix()}' (FORMAT json, ARRAY true)")
        row_counts[name] = con.execute(f"SELECT count(*) FROM ({query})").fetchone()[0]
        print(f"Wrote {out_file} ({row_counts[name]} rows)")

    # A small file describing this export, for the website's status bar
    meta = {
        "exported_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "data_run_date": con.execute("SELECT max(run_date) FROM raw_indicator_values").fetchone()[0],
        "world_bank_last_updated": json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {},
        "row_counts": row_counts,
        "tests_passed": True,  # this script only runs after dbt build succeeds
    }
    (OUT_DIR / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(f"Wrote {OUT_DIR / 'meta.json'}")
    con.close()


if __name__ == "__main__":
    main()