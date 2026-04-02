{{
    config(
        materialized = 'table',
        schema = 'gold'
    )
}}

WITH stats AS (
    SELECT
        username,
        time_class,
        COUNT(*) AS total_games,
        AVG(CASE WHEN result = 'win' THEN 1 ELSE 0 END) AS win_rate,
        AVG(CASE WHEN result_type = 'timeout' THEN 1 ELSE 0 END) AS timeout_loss_rate,
        MAX(player_rating) AS peak_rating
    FROM {{ ref('silver_games') }}
    GROUP BY 1,2
),

current_ratings AS (
    SELECT
        username,
        time_class,
        player_rating AS current_rating,
        ROW_NUMBER() OVER (PARTITION BY username, time_class ORDER BY end_at DESC) AS rn
    FROM {{ ref('silver_games') }}
),

top_opening AS (
    SELECT
        username,
        time_class,
        opening_family,
        COUNT(*) AS games_played,
        ROW_NUMBER() OVER (PARTITION BY username, time_class ORDER BY COUNT(*) DESC) AS rn
    FROM {{ ref('silver_games') }}
    GROUP BY 1, 2, 3
)

SELECT
    s.*,
    cr.current_rating,
    t.opening_family AS most_played_opening
FROM stats s
LEFT JOIN current_ratings cr 
    ON s.username = cr.username 
    AND s.time_class = cr.time_class 
    AND cr.rn = 1
LEFT JOIN top_opening t 
    ON s.username = t.username 
    AND s.time_class = t.time_class 
    AND t.rn = 1