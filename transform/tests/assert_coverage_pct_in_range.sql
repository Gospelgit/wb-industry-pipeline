-- Fails if any coverage percentage is below 0 or above 100

select *
from {{ ref('indicator_coverage') }}
where coverage_pct < 0 or coverage_pct > 100