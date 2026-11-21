import duckdb

con = duckdb.connect("data/warehouse.duckdb", read_only=True)

print("Low coverage (under 50% of years)")
con.sql("""
    SELECT country_name, indicator_id, years_with_data, coverage_pct
    FROM indicator_coverage
    WHERE low_coverage
    ORDER BY coverage_pct
""").show()

print("Provisional years (fewer than half of countries reported)")
con.sql("""
    SELECT indicator_id, year, countries_reported, countries_total
    FROM indicator_year_status
    WHERE is_provisional
    ORDER BY indicator_id, year
""").show()