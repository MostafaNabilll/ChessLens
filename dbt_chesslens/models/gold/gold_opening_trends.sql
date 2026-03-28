{{
    config(
        materialized = 'table',
        schema = 'gold'
    )
}}

WITH monthly_stats AS (
    SELECT
        opening_family,
        time_class,
        date_trunc('month', end_at) AS month,
        COUNT(*) AS games_played,
        AVG(CASE WHEN result = 'win' THEN 1 ELSE 0 END) AS win_rate,
        AVG(opponent_rating) AS avg_opponent_rating
    FROM {{ ref('silver_games') }}
    GROUP BY 1, 2, 3
    HAVING COUNT(*) >= 5
),

with_trends AS (
    SELECT
        *,
        LAG(win_rate) OVER (PARTITION BY opening_family, time_class ORDER BY month) AS prev_month_win_rate
    FROM monthly_stats
)

SELECT
    opening_family,
    time_class,
    month,
    games_played,
    win_rate,
    avg_opponent_rating,
    prev_month_win_rate,
    CASE
        WHEN prev_month_win_rate IS NULL THEN 'new'
        WHEN win_rate > prev_month_win_rate + 0.05 THEN 'improving'
        WHEN win_rate < prev_month_win_rate - 0.05 THEN 'declining'
        ELSE 'stable'
    END AS trend
FROM with_trends