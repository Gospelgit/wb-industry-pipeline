import duckdb

con = duckdb.connect("data/warehouse.duckdb", read_only=True)

# Score every year-on-year change against that country's own usual changes.
# GDP is in dollars, so we use its % growth instead of the raw change.
con.execute("""
    CREATE TEMP TABLE scored AS
    WITH changes AS (
        SELECT country_iso3, indicator_id, year, value,
               CASE WHEN indicator_id = 'NY.GDP.MKTP.KD'
                    THEN 100 * (value / lag(value) OVER w - 1)
                    ELSE value - lag(value) OVER w
               END AS change
        FROM fct_indicator_values
        WHERE has_value
        WINDOW w AS (PARTITION BY country_iso3, indicator_id ORDER BY year)
    ),
    usual AS (
        SELECT country_iso3, indicator_id,
               median(change) AS typical_change,
               mad(change)    AS typical_spread
        FROM changes
        WHERE change IS NOT NULL
        GROUP BY country_iso3, indicator_id
    ),
    indicator_spread AS (
        -- How much this indicator usually moves, across all 16 countries
        SELECT indicator_id, mad(change) AS indicator_spread
        FROM changes
        WHERE change IS NOT NULL
        GROUP BY indicator_id
    )
    SELECT c.*, u.typical_change, u.typical_spread, i.indicator_spread,
           (c.change - u.typical_change)
             / greatest(1.4826 * u.typical_spread,
                        1.4826 * i.indicator_spread,
                        0.1) AS score
    FROM changes c
    JOIN usual u USING (country_iso3, indicator_id)
    JOIN indicator_spread i USING (indicator_id)
    WHERE c.change IS NOT NULL
""")

print("How many changes would be flagged at each cut-off:")
con.sql("""
    SELECT count(*)                                AS all_changes,
           count(*) FILTER (WHERE abs(score) > 3)   AS above_3,
           count(*) FILTER (WHERE abs(score) > 3.5) AS above_3_5,
           count(*) FILTER (WHERE abs(score) > 5)   AS above_5
    FROM scored
""").show()

print("The 15 most unusual changes:")
con.sql("""
    SELECT country_iso3, indicator_id, year,
           round(change, 1)         AS change,
           round(typical_change, 1) AS typical,
           round(score, 1)          AS score
    FROM scored
    ORDER BY abs(score) DESC
    LIMIT 15
""").show()


print("Benin's 2022 electricity jump, for reference:")
con.sql("""
    SELECT country_iso3, year, round(change, 1) AS change, round(score, 1) AS score,
           (SELECT count(*) FROM scored s2 WHERE abs(s2.score) > abs(s.score)) + 1 AS rank
    FROM scored s
    WHERE country_iso3 = 'BEN' AND indicator_id = 'EG.ELC.ACCS.ZS' AND year = 2022
""").show()