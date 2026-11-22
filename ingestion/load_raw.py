import json
from datetime import datetime
from pathlib import Path

import duckdb

RAW_DIR = Path("data/raw")
DB_PATH = Path("data/warehouse.duckdb")


def latest_run_dir():
    """Find the newest dated folder in data/raw."""
    runs = sorted(p for p in RAW_DIR.iterdir() if p.is_dir())
    if not runs:
        raise SystemExit("No raw data found. Run fetch_indicators.py first.")
    return runs[-1]


def read_rows(run_dir):
    """Turn every row in every raw file into a flat tuple."""
    loaded_at = datetime.now()
    for file in sorted(run_dir.glob("*.json")):
        meta, rows = json.loads(file.read_text(encoding="utf-8"))
        for row in rows or []:
            yield (
                row["indicator"]["id"],
                row["indicator"]["value"],
                row["countryiso3code"],
                row["country"]["value"],
                int(row["date"]),
                row["value"],
                row["obs_status"] or None,
                run_dir.name,
                file.name,
                loaded_at,
            )


def main():
    run_dir = latest_run_dir()
    rows = list(read_rows(run_dir))

    con = duckdb.connect(str(DB_PATH))
    con.execute("""
        CREATE TABLE IF NOT EXISTS raw_indicator_values (
            indicator_id   VARCHAR,
            indicator_name VARCHAR,
            country_iso3   VARCHAR,
            country_name   VARCHAR,
            year           INTEGER,
            value          DOUBLE,
            obs_status     VARCHAR,
            run_date       VARCHAR,
            source_file    VARCHAR,
            loaded_at      TIMESTAMP
        )
    """)

    # Clear this run's rows first, so loading twice never creates duplicates
    con.execute("DELETE FROM raw_indicator_values WHERE run_date = ?", [run_dir.name])
    con.executemany(
        "INSERT INTO raw_indicator_values VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )

    count = con.execute(
        "SELECT COUNT(*) FROM raw_indicator_values WHERE run_date = ?",
        [run_dir.name],
    ).fetchone()[0]
    print(f"Loaded {count} rows from {run_dir}")
    con.close()


if __name__ == "__main__":
    main()