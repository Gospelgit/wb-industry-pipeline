-- One row per country, with its details and ECOWAS membership

select
    c.country_iso3,
    c.country_iso2,
    c.country_name,
    c.region,
    c.income_level,          -- today's World Bank classification, not historical
    c.lending_type,
    c.capital_city,
    c.latitude,
    c.longitude,
    m.first_member_year      as ecowas_first_year,
    m.last_member_year       as ecowas_last_year,
    m.last_member_year is null as is_current_ecowas_member
from {{ ref('stg_countries') }} as c
left join {{ ref('ecowas_membership') }} as m
    on c.country_iso3 = m.country_iso3