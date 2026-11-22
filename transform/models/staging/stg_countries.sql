-- Clean country details

select
    country_iso3,
    country_iso2,
    country_name,
    region,
    income_level,
    lending_type,
    capital_city,
    latitude,
    longitude
from {{ source('raw', 'raw_countries') }}