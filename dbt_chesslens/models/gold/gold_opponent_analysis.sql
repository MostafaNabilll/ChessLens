{{
    config(
        materialized = 'table',
        schema = 'gold'
    )
}}

WITH games_with_bucket AS (
    SELECT
        *,
        CASE 
            WHEN rating_diff > 200 THEN 'much_lower'
            WHEN rating_diff BETWEEN 50 AND 200 THEN 'lower'
            WHEN rating_diff BETWEEN -50 AND 50 THEN 'equal'
            WHEN rating_diff BETWEEN -200 AND -50 THEN 'higher'
            ELSE 'much_higher'
        END AS rating_bucket,
        1.0 / (1 + POWER(10, (-rating_diff / 400.0))) AS expected_win_rate
    FROM {{ ref('silver_games') }}
)

SELECT
    username,
    time_class,
    rating_bucket,
    COUNT(*) AS games_played,
    AVG(CASE WHEN result = 'win' THEN 1 ELSE 0 END) AS win_rate,
    AVG(opponent_rating) AS avg_opponent_rating,
    SUM(CASE WHEN result = 'win' AND expected_win_rate < 0.5 THEN 1 ELSE 0 END) AS upset_wins,
    AVG(CASE WHEN result = 'win' AND expected_win_rate < 0.5 THEN 1.0 ELSE 0 END) AS upset_rate

FROM games_with_bucket
GROUP BY 1, 2, 3