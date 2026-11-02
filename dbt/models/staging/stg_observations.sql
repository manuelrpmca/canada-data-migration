-- One row per indicator per reference date. Renames and casts only; no joins (ADR 0007).
--
-- The DuckDB raw table has a primary key, so the deduplication below removes nothing today.
-- It stays because the BigQuery target (M5) does not enforce keys, and the model must give
-- the same guarantee on both.

with source as (

    select * from {{ source('raw', 'observations') }}

),

deduplicated as (

    select
        *,
        row_number() over (
            partition by series_key, ref_date
            order by updated_at desc
        ) as row_num
    from source

)

select
    cast(series_key as varchar)    as indicator_key,
    cast(source as varchar)        as source,
    cast(series_id as varchar)     as series_id,
    cast(ref_date as date)         as ref_date,
    cast(value as double)          as value,
    cast(ingested_at as timestamp) as ingested_at,
    cast(updated_at as timestamp)  as updated_at,
    cast(run_id as varchar)        as run_id
from deduplicated
where row_num = 1
