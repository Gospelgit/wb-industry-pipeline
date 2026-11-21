-- One row per indicator and year: how many countries have reported?

with counts as (
    select
        indicator_id,
        year,
        count(*)                          as countries_total,
        count(*) filter (where has_value) as countries_reported
    from {{ ref('stg_indicator_values') }}
    group by indicator_id, year
)

select
    *,
    countries_reported * 1.0 / countries_total < 0.5 as is_provisional
from counts