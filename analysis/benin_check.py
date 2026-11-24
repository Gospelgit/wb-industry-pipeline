import duckdb

con = duckdb.connect("data/warehouse.duckdb", read_only=True)

# Benin's electricity access year by year, with the change from the year before.
# Togo and Nigeria are shown alongside as neighbours to compare with.
con.sql("""
    SELECT year,
           max(value) FILTER (WHERE country_iso3 = 'BEN') AS benin,
           round(benin - lag(benin) OVER (ORDER BY year), 2) AS benin_change,
           max(value) FILTER (WHERE country_iso3 = 'TGO') AS togo,
           max(value) FILTER (WHERE country_iso3 = 'NGA') AS nigeria
    FROM fct_indicator_values
    WHERE indicator_id = 'EG.ELC.ACCS.ZS'
      AND year >= 2010
    GROUP BY year
    ORDER BY year
""").show(max_rows=30)