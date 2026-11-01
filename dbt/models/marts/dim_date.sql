-- Calendar, one row per day, covering whole years from the first to the last observation.
--
-- Business days: neither source publishes a holiday calendar. The Bank of Canada publishes
-- USD/CAD only on its business days, while the policy rate series has a value on every
-- weekday, holidays included (M1 note). So a weekday is a business day when it has a USD/CAD
-- observation. After the last USD/CAD observation the calendar is not known yet, and
-- is_business_day is null.

with bounds as (

    select
        min(ref_date) as first_date,
        max(ref_date) as last_date
    from {{ ref('stg_observations') }}

),

fx_days as (

    select ref_date
    from {{ ref('stg_observations') }}
    where indicator_key = 'usd_cad'

),

last_fx as (

    select max(ref_date) as last_fx_date from fx_days

),

spine as (

    {{ date_spine(
        "select date_trunc('year', first_date) from bounds",
        "select date_trunc('year', last_date) + interval 1 year - interval 1 day from bounds"
    ) }}

)

select
    spine.date_day,
    extract(year from spine.date_day)                        as year,
    extract(quarter from spine.date_day)                     as quarter,
    extract(month from spine.date_day)                       as month,
    extract(day from spine.date_day)                         as day_of_month,
    extract(isodow from spine.date_day)                      as iso_day_of_week,
    cast(date_trunc('month', spine.date_day) as date)        as month_start,
    cast(
        date_trunc('month', spine.date_day) + interval 1 month - interval 1 day as date
    )                                                        as month_end,
    extract(isodow from spine.date_day) in (6, 7)            as is_weekend,
    fx_days.ref_date is not null                             as has_fx_observation,
    case
        when spine.date_day > last_fx.last_fx_date then null
        else extract(isodow from spine.date_day) not in (6, 7)
            and fx_days.ref_date is not null
    end                                                      as is_business_day
from spine
cross join last_fx
left join fx_days on fx_days.ref_date = spine.date_day
