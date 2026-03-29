{{
    config(
        materialized ='incremental',
        schema = 'silver',
        unique_key = 'game_id'
    )
}}


WITH base AS (
    SELECT
        game_json,
        game_url,
        username,
        CASE
            WHEN LOWER(json_extract_string(game_json, '$.white.username')) = LOWER(username) THEN 'white'
            ELSE 'black'
        END AS player_color
    FROM {{ ref('bronze_raw_games') }}
),

ratings AS (
    SELECT
        *,
        CASE 
            WHEN player_color = 'white' THEN json_extract(game_json, '$.white.rating')::INT
            ELSE json_extract(game_json, '$.black.rating')::INT
        END AS player_rating,
        CASE 
            WHEN player_color = 'white' THEN json_extract(game_json, '$.black.rating')::INT
            ELSE json_extract(game_json, '$.white.rating')::INT
        END AS opponent_rating,
        CASE
            WHEN player_color = 'white' THEN json_extract_string(game_json, '$.white.result')
            ELSE json_extract_string(game_json, '$.black.result')
        END AS raw_result,
        CASE
            WHEN player_color = 'white' THEN json_extract_string(game_json, '$.black.result')
            ELSE json_extract_string(game_json, '$.white.result')
        END AS opponent_result_type
    FROM base
)


SELECT
    json_extract_string(game_json, '$.uuid') AS game_id,
    username,
    to_timestamp(json_extract(game_json, '$.end_time')::BIGINT) AS end_at,
    json_extract_string(game_json, '$.time_control') AS time_control,
    json_extract_string(game_json, '$.time_class') AS time_class,
    player_color,
    player_rating,
    opponent_rating,
    player_rating - opponent_rating AS rating_diff,
    CASE
        WHEN raw_result = 'win' THEN 'win'
        WHEN raw_result IN ('repetition', 'stalemate', 'timevsinsufficient', 'insufficient', 'agreed', '50moves') THEN 'draw'
        ELSE 'loss'
    END AS result,
    raw_result as result_type,
    opponent_result_type,
    REPLACE(
        REGEXP_EXTRACT(json_extract_string(game_json, '$.eco'), '/openings/(.*)',1),
        '-', ' '
    ) AS opening_name,
    REGEXP_REPLACE(
        REPLACE(
            REGEXP_EXTRACT(json_extract_string(game_json, '$.eco'), '/openings/(.*)', 1),
            '-', ' '
        ),
        '\s+\d+\..*$', ''
    ) AS opening_family,
    json_extract_string(game_json, '$.eco') AS opening_eco,
    json_extract_string(game_json, '$.pgn') as pgn
FROM ratings