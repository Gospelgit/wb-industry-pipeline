import duckdb

con = duckdb.connect("data/warehouse.duckdb", read_only=True)

con.sql("""
    SELECT country_iso3, year, is_ecowas_member
    FROM fct_indicator_values
    WHERE indicator_id = 'NV.IND.MANF.ZS'
      AND country_iso3 IN ('MRT', 'MLI', 'NGA')
      AND year IN (2000, 2001, 2024, 2025)
    ORDER BY country_iso3, year
""").show()