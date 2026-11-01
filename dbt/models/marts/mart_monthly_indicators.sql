-- One row per month, one column per indicator: the wide table a dashboard reads.
--
-- Rules per indicator:
--   CPI and unemployment rate: the monthly value (reference date = first day of the month).
--   USD/CAD: average of the daily rates published in the month, with the number of days.
--   Policy rate: the rate in effect on the last day of the month, that is, the latest
--   observation on or before month end. Carrying it forward covers days with no value
--   (Valet has a few gaps, for example 2022-08-02).
-- Months run from the first to the last month with any observation, so the latest rows can
-- have nulls for series that are not published yet.

with observations as (

    select * from {{ ref('fct_observation') }}

),

months as (

    select distinct
        month_start,
        month_end
    from {{ ref('dim_date') }}
    where month_start between
        (select cast(date_trunc('month', min(date_day)) as date) from observations)
        and (select cast(date_trunc('month', max(date_day)) as date) from observations)

),

monthly_values as (

    select
        cast(date_trunc('month', date_day) as date)               as month_start,
        max(case when indicator_key = 'cpi_ontario' then value end)  as cpi_ontario,
        max(case when indicator_key = 'unemployment_ontario' then value end)
                                                                  as unemployment_rate_ontario,
        round(avg(case when indicator_key = 'usd_cad' then value end), 4)
                                                                  as usd_cad_avg,
        count(case when indicator_key = 'usd_cad' then 1 end)        as usd_cad_days
    from observations
    group by 1

),

policy_rate_at_month_end as (

    select
        months.month_start,
        observations.value as policy_rate_end_of_month
    from months
    inner join observations
        on observations.indicator_key = 'policy_rate'
        and observations.date_day <= months.month_end
    qualify row_number() over (
        partition by months.month_start
        order by observations.date_day desc
    ) = 1

)

select
    months.month_start,
    monthly_values.cpi_ontario,
    round(
        100 * (
            monthly_values.cpi_ontario
            / lag(monthly_values.cpi_ontario, 12) over (order by months.month_start)
            - 1
        ),
        1
    )                                          as cpi_ontario_yoy_pct,
    monthly_values.unemployment_rate_ontario,
    monthly_values.usd_cad_avg,
    coalesce(monthly_values.usd_cad_days, 0)   as usd_cad_days,
    policy_rate_at_month_end.policy_rate_end_of_month
from months
left join monthly_values on monthly_values.month_start = months.month_start
left join policy_rate_at_month_end on policy_rate_at_month_end.month_start = months.month_start
