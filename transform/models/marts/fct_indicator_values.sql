-- One row per country, indicator and year, with quality and membership flags

select
    v.country_iso3,
    v.indicator_id,
    v.year,
    v.value,
    v.has_value,
    ys.is_provisional,
    cov.low_coverage                                  as is_low_coverage,
    coalesce(
        v.year between m.first_member_year
               and coalesce(m.last_member_year, 9999),
        false
    )                                                 as is_ecowas_member
from {{ ref('stg_indicator_values') }} as v
left join {{ ref('indicator_year_status') }} as ys
    on v.indicator_id = ys.indicator_id
   and v.year = ys.year
left join {{ ref('indicator_coverage') }} as cov
    on v.country_iso3 = cov.country_iso3
   and v.indicator_id = cov.indicator_id
left join {{ ref('ecowas_membership') }} as m
    on v.country_iso3 = m.country_iso3