-- Values outside these bounds are almost certainly a parsing or unit error, not news.
-- The bounds are sanity limits chosen for this project, wider than anything in the data
-- loaded so far (see the M2 note); they are not published thresholds.
-- Returns the offending rows; dbt fails the test when any row comes back.

with bounds as (

    select 'usd_cad' as indicator_key, 0.5 as min_value, 2.5 as max_value
    union all select 'policy_rate', 0.0, 25.0
    union all select 'cpi_ontario', 50.0, 400.0
    union all select 'unemployment_ontario', 0.0, 30.0

)

select
    fct.indicator_key,
    fct.date_day,
    fct.value,
    bounds.min_value,
    bounds.max_value
from {{ ref('fct_observation') }} as fct
left join bounds on bounds.indicator_key = fct.indicator_key
where bounds.indicator_key is null  -- a new indicator needs bounds here
   or fct.value < bounds.min_value
   or fct.value > bounds.max_value
