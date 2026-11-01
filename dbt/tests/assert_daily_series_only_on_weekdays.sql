-- The Bank of Canada publishes daily series on weekdays only.

select fct.indicator_key, fct.date_day
from {{ ref('fct_observation') }} as fct
inner join {{ ref('dim_indicator') }} as ind on ind.indicator_key = fct.indicator_key
inner join {{ ref('dim_date') }} as d on d.date_day = fct.date_day
where ind.frequency = 'daily'
  and d.is_weekend
