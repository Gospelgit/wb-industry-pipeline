"""Hide the last 5 years, forecast them from earlier years, and compare each model's error."""

import sys

import duckdb

from models import MODELS

INDICATOR = "EG.ELC.ACCS.ZS"
# First hidden year can be given on the command line, e.g. python ml\backtest.py 2015
FIRST_TEST_YEAR = int(sys.argv[1]) if len(sys.argv) > 1 else 2020
TEST_YEARS = list(range(FIRST_TEST_YEAR, FIRST_TEST_YEAR + 5))
MIN_TRAIN_YEARS = 10


def load_series(con):
    """One list of (year, value) per country, only for countries that pass the coverage rule."""
    rows = con.execute(
        """
        SELECT country_iso3, year, value
        FROM fct_indicator_values
        WHERE indicator_id = ?
          AND has_value
          AND NOT is_low_coverage
        ORDER BY country_iso3, year
        """,
        [INDICATOR],
    ).fetchall()
    series = {}
    for country, year, value in rows:
        series.setdefault(country, []).append((year, value))
    return series


def clip(x):
    """Electricity access is a percentage, so keep forecasts between 0 and 100."""
    return min(max(x, 0.0), 100.0)


def main():
    con = duckdb.connect("data/warehouse.duckdb", read_only=True)
    series = load_series(con)
    con.close()

    totals = {name: [] for name in MODELS}
    print(f"{'country':<8}{'2019 level':>12}" + "".join(f"{name:>14}" for name in MODELS))

    for country, points in series.items():
        train = [v for y, v in points if y < TEST_YEARS[0]]
        actual = {y: v for y, v in points if y in TEST_YEARS}
        if len(train) < MIN_TRAIN_YEARS or len(actual) < len(TEST_YEARS):
            print(f"{country:<8} skipped (not enough data)")
            continue

        row = f"{country:<8}{train[-1]:>12.1f}"
        for name, model in MODELS.items():
            forecast = [clip(x) for x in model(train, len(TEST_YEARS))]
            errors = [abs(f - actual[y]) for f, y in zip(forecast, TEST_YEARS)]
            mae = sum(errors) / len(errors)
            totals[name].append(mae)
            row += f"{mae:>14.2f}"
        print(row)

    print("-" * (20 + 14 * len(MODELS)))
    print(f"{'average':<20}" + "".join(f"{sum(t) / len(t):>14.2f}" for t in totals.values()))
    print("\nNumbers are mean absolute error in percentage points. Lower is better.")


if __name__ == "__main__":
    main()