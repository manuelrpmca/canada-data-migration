-- One row per series per ingest run.

select
    cast(run_id as varchar)          as run_id,
    cast(series_key as varchar)      as indicator_key,
    cast(source as varchar)          as source,
    cast(status as varchar)          as run_status,
    cast(started_at as timestamp)    as started_at,
    cast(finished_at as timestamp)   as finished_at,
    cast(request_start as date)      as request_start,
    cast(rows_received as integer)   as rows_received,
    cast(inserted as integer)        as rows_inserted,
    cast(updated as integer)         as rows_updated,
    cast(unchanged as integer)       as rows_unchanged,
    cast(message as varchar)         as message
from {{ source('raw', 'run_log') }}
