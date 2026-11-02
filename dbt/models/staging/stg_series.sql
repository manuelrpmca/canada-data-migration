-- One row per configured series (config/series.yml, as synced by `cdm ingest`).

select
    cast(series_key as varchar) as indicator_key,
    cast(source as varchar)     as source,
    cast(series_id as varchar)  as series_id,
    cast(product_id as bigint)  as product_id,
    cast(name as varchar)       as indicator_name,
    cast(unit as varchar)       as unit,
    cast(frequency as varchar)  as frequency,
    cast(start_date as date)    as start_date,
    cast(verified as boolean)   as is_verified
from {{ source('raw', 'series') }}
