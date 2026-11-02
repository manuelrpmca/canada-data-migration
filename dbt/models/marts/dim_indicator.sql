-- One row per indicator: what it measures, who publishes it, and the attribution to show.

with series as (

    select * from {{ ref('stg_series') }}

),

publishers as (

    select * from {{ ref('source_publishers') }}

),

coverage as (

    select
        indicator_key,
        min(ref_date) as first_ref_date,
        max(ref_date) as last_ref_date,
        count(*)      as observation_count
    from {{ ref('stg_observations') }}
    group by indicator_key

)

select
    series.indicator_key,
    series.indicator_name,
    series.unit,
    series.frequency,
    series.source,
    publishers.publisher,
    series.series_id,
    series.product_id,
    series.is_verified,
    coverage.first_ref_date,
    coverage.last_ref_date,
    coalesce(coverage.observation_count, 0) as observation_count,
    publishers.attribution,
    publishers.licence_name,
    publishers.licence_url
from series
left join publishers on publishers.source = series.source
left join coverage on coverage.indicator_key = series.indicator_key
