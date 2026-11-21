import duckdb

con = duckdb.connect("data/warehouse.duckdb", read_only=True)

print(con.sql("""
    SELECT indicator_id,
           COUNT(*)                AS total_rows,
           COUNT(value)            AS filled,
           COUNT(*) - COUNT(value) AS missing,
           ROUND(100.0 * (COUNT(*) - COUNT(value)) / COUNT(*), 1) AS pct_missing
    FROM raw_indicator_values
    GROUP BY indicator_id
    ORDER BY pct_missing DESC
"""))