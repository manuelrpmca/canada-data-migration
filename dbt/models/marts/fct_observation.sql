-- One row per indicator per reference date: the long ("tall") fact table.
-- Adding an indicator adds rows, never columns.

select
    indicator_key || '|' || cast(ref_date as varchar) as observation_id,
    indicator_key,
    ref_date                                          as date_day,
    value,
    ingested_at,
    updated_at,
    run_id
from {{ ref('stg_observations') }}
