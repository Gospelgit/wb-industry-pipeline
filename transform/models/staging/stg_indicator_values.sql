-- Clean view of the latest download only

with latest_run as (
    select max(run_date) as run_date
    from {{ source('raw', 'raw_indicator_values') }}
)

select
    r.country_iso3,
    r.country_name,
    r.indicator_id,
    r.indicator_name,
    r.year,
    r.value,
    r.value is not null as has_value,
    r.run_date
from {{ source('raw', 'raw_indicator_values') }} as r
inner join latest_run using (run_date)