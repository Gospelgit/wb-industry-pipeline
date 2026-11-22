-- One row per indicator, with a short name and unit for charts

select distinct
    v.indicator_id,
    v.indicator_name,
    i.short_name,
    i.unit,
    i.theme
from {{ ref('stg_indicator_values') }} as v
left join {{ ref('indicators') }} as i
    on v.indicator_id = i.indicator_id