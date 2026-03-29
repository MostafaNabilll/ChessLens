{{
    config(
        materialized = 'table',
        schema = 'gold'
    )
}}

WITH ordered_games AS (
    SELECT
        username,
        game_id,
        end_at,
        result,
        time_class,
        player_rating,
        opponent_rating,
        rating_diff,
        result_type,
        -- This creates a new group number every time you win or draw
        SUM(CASE WHEN result != 'loss' THEN 1 ELSE 0 END) 
            OVER (PARTITION BY username ORDER BY end_at) AS loss_group
    FROM {{ ref('silver_games') }}
),

-- Count the streak within each group
streaks AS (
    SELECT
        *,
        CASE 
            WHEN result = 'loss' THEN 
                ROW_NUMBER() OVER (PARTITION BY username, loss_group ORDER BY end_at) - 1
            ELSE 0
        END AS loss_streak
    FROM ordered_games
),

-- Get the streak BEFORE each game
with_prior_streak AS (
    SELECT
        *,
        LAG(loss_streak, 1, 0) OVER (PARTITION BY username ORDER BY end_at) AS consecutive_losses_before
    FROM streaks
)

SELECT
    username,
    game_id,
    end_at,
    time_class,
    result,
    result_type,
    player_rating,
    opponent_rating,
    consecutive_losses_before,
    -- Flag if tilted (3+ consecutive losses before this game)
    CASE WHEN consecutive_losses_before >= 3 THEN true ELSE false END AS is_tilted
FROM with_prior_streak