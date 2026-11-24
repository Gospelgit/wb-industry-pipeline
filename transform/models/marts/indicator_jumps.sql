-- One row per year-on-year change, scored against what is normal for that country and indicator

with changes as (
    select
        country_iso3,
        indicator_id,
        year,
        value,
        case
            when indicator_id = 'NY.GDP.MKTP.KD'   -- GDP is in dollars, so use % growth
                then 100 * (value / lag(value) over w - 1)
            else value - lag(value) over w
        end as change
    from {{ ref('fct_indicator_values') }}
    where has_value
    window w as (partition by country_iso3, indicator_id order by year)
),

country_usual as (
    select
        country_iso3,
        indicator_id,
        median(change) as typical_change,
        mad(change)    as country_spread
    from changes
    where change is not null
    group by country_iso3, indicator_id
),

indicator_usual as (
    select
        indicator_id,
        mad(change) as indicator_spread
    from changes
    where change is not null
    group by indicator_id
),

scored as (
    select
        c.country_iso3,
        c.indicator_id,
        c.year,
        c.value,
        c.change,
        cu.typical_change,
        -- never treat a country as calmer than the indicator usually is
        greatest(1.4826 * cu.country_spread, 1.4826 * iu.indicator_spread, 0.1) as normal_wobble,
        (c.change - cu.typical_change)
            / greatest(1.4826 * cu.country_spread, 1.4826 * iu.indicator_spread, 0.1) as score
    from changes as c
    inner join country_usual as cu using (country_iso3, indicator_id)
    inner join indicator_usual as iu using (indicator_id)
    where c.change is not null
)

select
    s.*,
    abs(s.score) > {{ var('jump_score_threshold') }} as is_unusual,
    r.country_iso3 is not null                        as is_reviewed,
    r.note                                            as review_note
from scored as s
left join {{ ref('reviewed_jumps') }} as r
    on s.country_iso3 = r.country_iso3
   and s.indicator_id = r.indicator_id
   and s.year = r.year