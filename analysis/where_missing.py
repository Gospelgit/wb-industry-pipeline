import duckdb

con = duckdb.connect("data/warehouse.duckdb", read_only=True)

# Only look at the most recent download
LATEST = "(SELECT MAX(run_date) FROM raw_indicator_values)"

print("Gaps by country")
con.sql(f"""
    SELECT indicator_id,
           country_name,
           COUNT(*) - COUNT(value)                    AS missing,
           MIN(year) FILTER (WHERE value IS NOT NULL) AS first_year_with_data,
           MAX(year) FILTER (WHERE value IS NOT NULL) AS last_year_with_data
    FROM raw_indicator_values
    WHERE run_date = {LATEST}
    GROUP BY indicator_id, country_name
    HAVING COUNT(*) - COUNT(value) > 0
    ORDER BY indicator_id, missing DESC
""").show(max_rows=100)

print("Gaps by year (out of 16 countries)")
con.sql(f"""
    SELECT year,
           COUNT(*) FILTER (WHERE indicator_id = 'TX.VAL.MANF.ZS.UN' AND value IS NULL) AS exports,
           COUNT(*) FILTER (WHERE indicator_id = 'NV.IND.MANF.ZS'    AND value IS NULL) AS manufacturing,
           COUNT(*) FILTER (WHERE indicator_id = 'EG.ELC.ACCS.ZS'    AND value IS NULL) AS electricity
    FROM raw_indicator_values
    WHERE run_date = {LATEST}
    GROUP BY year
    ORDER BY year
""").show(max_rows=100)