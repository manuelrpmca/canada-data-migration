-- Between its first and last month, every monthly series has one value per month.
-- A gap would mean a lost load, not a missing publication.

with coverage as (

    select
        fct.indicator_key,
        min(fct.date_day) as first_month,
        max(fct.date_day) as last_month,
        count(*)          as months_loaded
    from {{ ref('fct_observation') }} as fct
    inner join {{ ref('dim_indicator') }} as ind on ind.indicator_key = fct.indicator_key
    where ind.frequency = 'monthly'
    group by fct.indicator_key

)

select
    indicator_key,
    first_month,
    last_month,
    months_loaded,
    datediff('month', first_month, last_month) + 1 as months_expected
from coverage
where months_loaded <> datediff('month', first_month, last_month) + 1
