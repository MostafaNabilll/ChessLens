{{ 
    config(
        materialized = 'table',
        schema = 'bronze'
    )
}}

SELECT
    *,
    CURRENT_TIMESTAMP AS ingested_at
FROM {{ source('raw', 'raw_games') }}
