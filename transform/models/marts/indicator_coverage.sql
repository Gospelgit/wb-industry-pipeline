-- One row per country and indicator: how complete is the data?

with counts as (
    select
        country_iso3,
        country_name,
        indicator_id,
        indicator_name,
        count(*)                                as years_total,
        count(*) filter (where has_value)       as years_with_data,
        min(year) filter (where has_value)      as first_year_with_data,
        max(year) filter (where has_value)      as last_year_with_data
    from {{ ref('stg_indicator_values') }}
    group by country_iso3, country_name, indicator_id, indicator_name
)

select
    *,
    round(100.0 * years_with_data / years_total, 1)  as coverage_pct,
    years_with_data * 1.0 / years_total < 0.5        as low_coverage
from counts