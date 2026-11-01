-- Monthly series must use the first day of the month as the reference date; the mart's
-- monthly join relies on it.

select fct.indicator_key, fct.date_day
from {{ ref('fct_observation') }} as fct
inner join {{ ref('dim_indicator') }} as ind on ind.indicator_key = fct.indicator_key
where ind.frequency = 'monthly'
  and extract(day from fct.date_day) <> 1
