"""Forecast the next 5 years with the blend model, with ranges based on real backtest errors."""

from datetime import datetime, timezone

import duckdb

from backtest import INDICATOR, MIN_TRAIN_YEARS, clip, load_series
from models import MODELS

MODEL_NAME = "blend"
HORIZON = 5
BACKTEST_STARTS = [2015, 2020]  # the two hidden periods we tested on
RANGE_PERCENTILE = 0.8          # 80% of past misses were smaller than the range


def error_by_step(series, model):
    """How far off was the model 1, 2, ... 5 years ahead, across both backtests?"""
    misses = {h: [] for h in range(1, HORIZON + 1)}
    for start in BACKTEST_STARTS:
        for points in series.values():
            train = [v for y, v in points if y < start]
            actual = {y: v for y, v in points if start <= y < start + HORIZON}
            if len(train) < MIN_TRAIN_YEARS or len(actual) < HORIZON:
                continue
            forecast = [clip(x) for x in model(train, HORIZON)]
            for h in range(1, HORIZON + 1):
                misses[h].append(abs(forecast[h - 1] - actual[start + h - 1]))

    widths = {}
    for h, values in misses.items():
        values.sort()
        widths[h] = values[round(RANGE_PERCENTILE * (len(values) - 1))]
        # Uncertainty should never shrink further ahead
        if h > 1:
            widths[h] = max(widths[h], widths[h - 1])
    return widths


def main():
    con = duckdb.connect("data/warehouse.duckdb")
    series = load_series(con)
    model = MODELS[MODEL_NAME]
    widths = error_by_step(series, model)
    print("Range half-widths by years ahead:", {h: round(w, 2) for h, w in widths.items()})

    created_at = datetime.now(timezone.utc)
    rows = []
    for country, points in series.items():
        values = [v for _, v in points]
        if len(values) < MIN_TRAIN_YEARS:
            continue
        last_year = points[-1][0]
        forecast = model(values, HORIZON)
        for h in range(1, HORIZON + 1):
            centre = clip(forecast[h - 1])
            rows.append((
                country, INDICATOR, last_year + h,
                round(centre, 2),
                round(clip(centre - widths[h]), 2),
                round(clip(centre + widths[h]), 2),
                MODEL_NAME, last_year, created_at,
            ))

    # Simple safety checks before saving anything
    assert rows, "No forecasts were produced"
    for row in rows:
        assert 0 <= row[4] <= row[3] <= row[5] <= 100, f"Bad range: {row}"

    con.execute("""
        CREATE OR REPLACE TABLE fct_indicator_forecasts (
            country_iso3    VARCHAR,
            indicator_id    VARCHAR,
            year            INTEGER,
            forecast        DOUBLE,
            low             DOUBLE,
            high            DOUBLE,
            model           VARCHAR,
            trained_through INTEGER,
            created_at      TIMESTAMPTZ
        )
    """)
    con.executemany("INSERT INTO fct_indicator_forecasts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)
    print(f"Saved {len(rows)} forecasts for {len(rows) // HORIZON} countries")

    con.sql("""
        SELECT country_iso3, year, forecast, low, high
        FROM fct_indicator_forecasts
        WHERE year = (SELECT max(year) FROM fct_indicator_forecasts)
        ORDER BY forecast DESC
    """).show()
    con.close()


if __name__ == "__main__":
    main()