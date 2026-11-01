-- The monthly mart has no missing months: the year-over-year change and any chart that
-- reads it assume one row per month.

select
    month_start,
    lag(month_start) over (order by month_start) as previous_month
from {{ ref('mart_monthly_indicators') }}
qualify previous_month is not null
    and datediff('month', previous_month, month_start) <> 1
