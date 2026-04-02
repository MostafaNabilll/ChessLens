{{
    config(
        materialized = 'table',
        schema = 'gold'
        )
}}

SELECT
    username,
    EXTRACT(HOUR FROM end_at) AS hour_of_day,
    DAYOFWEEK(end_at) AS day_of_week,
    CASE
        WHEN EXTRACT(HOUR FROM end_at) BETWEEN 6 and 11 THEN 'morning'
        WHEN EXTRACT(HOUR FROM end_at) BETWEEN 12 and 17 THEN 'afternoon'
        WHEN EXTRACT(HOUR FROM end_at) BETWEEN 18 and 23 THEN 'evening'
        ELSE 'night'
    END as hour_bucket,
    time_class,
    COUNT(*) AS games_played,
    AVG(CASE WHEN result = 'win' THEN 1 ELSE 0 END) AS win_rate,
    AVG(rating_diff) AS avg_opponent_gap

FROM {{ ref('silver_games') }}
GROUP BY 1, 2, 3, 4, 5
