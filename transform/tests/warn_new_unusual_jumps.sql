{{ config(severity='warn') }}

-- Warns about unusual jumps in recent years that nobody has reviewed yet.
-- To silence one after checking it, add it to seeds/reviewed_jumps.csv with a note.

select country_iso3, indicator_id, year, round(change, 1) as change, round(score, 1) as score
from {{ ref('indicator_jumps') }}
where is_unusual
  and not is_reviewed
  and year > (select max(year) from {{ ref('indicator_jumps') }}) - {{ var('jump_recent_years') }}