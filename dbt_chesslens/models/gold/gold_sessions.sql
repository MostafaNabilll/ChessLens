{{
    config(
        materialized = 'table',
        schema = 'gold'
    )
}}

WITH gaps AS (
    SELECT
        *,
        LAG(end_at) OVER (PARTITION BY username, time_class ORDER BY end_at) AS prev_end_at,
        CASE 
            WHEN end_at - LAG(end_at) OVER (PARTITION BY username, time_class ORDER BY end_at) > INTERVAL '30 minutes'
                OR LAG(end_at) OVER (PARTITION BY username, time_class ORDER BY end_at) IS NULL
            THEN 1 ELSE 0
        END AS is_new_session
    FROM {{ ref('silver_games') }}
),

sessions AS (
    SELECT
        *,
        SUM(is_new_session) OVER (PARTITION BY username, time_class ORDER BY end_at) AS session_id
    FROM gaps
),

session_edges AS (
    SELECT DISTINCT
        username,
        session_id,
        time_class,
        FIRST_VALUE(player_rating) OVER (PARTITION BY username, session_id, time_class ORDER BY end_at) AS rating_start,
        LAST_VALUE(player_rating) OVER (
            PARTITION BY username, session_id, time_class ORDER BY end_at 
            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
        ) AS rating_end
    FROM sessions
)

SELECT
    s.username,
    s.session_id,
    s.time_class,
    MIN(s.end_at) AS session_start,
    MAX(s.end_at) AS session_end,
    COUNT(*) AS games_played,
    SUM(CASE WHEN s.result = 'win' THEN 1 ELSE 0 END) AS wins,
    SUM(CASE WHEN s.result = 'loss' THEN 1 ELSE 0 END) AS losses,
    SUM(CASE WHEN s.result = 'draw' THEN 1 ELSE 0 END) AS draws,
    se.rating_start,
    se.rating_end,
    se.rating_end - se.rating_start AS rating_delta
FROM sessions s
JOIN session_edges se 
    ON s.username = se.username 
    AND s.session_id = se.session_id 
    AND s.time_class = se.time_class
GROUP BY 1,2,3,10,11