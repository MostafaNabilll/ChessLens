# ChessLens dbt Project

dbt transformations for the ChessLens --> personal chess analytics platform. Follows a medallion architecture (bronze → silver → gold) on top of DuckDB.

## Lineage

![ChessLens Lineage](../docs/dbt_lineage.png)

## Architecture

### Bronze Layer
Raw data from the chess.com API with no transformations. Acts as the source of truth.

| Model | Description |
|-------|-------------|
| `bronze_raw_games` | One row per game, raw JSON preserved, ingestion timestamp added |

### Silver Layer
Cleaned, typed, and deduplicated game records. JSON fields parsed into proper columns. Incremental materialization. only new games are processed on subsequent runs.

| Model | Description |
|-------|-------------|
| `silver_games` | Parsed game records with player perspective applied (ratings, results, openings) |

### Gold Layer
Analytics-ready aggregations powering the Streamlit dashboard.

| Model | Description |
|-------|-------------|
| `gold_tilt_analysis` | Consecutive loss streak detection and performance impact measurement |
| `gold_time_of_day` | Win rate patterns by hour of day, day of week, and time control |
| `gold_opening_trends` | Monthly opening performance with improving/declining/stable trend classification |
| `gold_opponent_analysis` | Performance segmented by opponent rating range with upset tracking |
| `gold_sessions` | Playing sessions detected by 30-min gap, partitioned by time control |
| `gold_time_control_comparison` | Side-by-side metrics across bullet, blitz, rapid, and daily |

## Setup

```bash
# From the project root, activate your virtual environment
.\venv\Scripts\Activate

# Navigate to the dbt project
cd dbt_chesslens

# Install dbt packages
dbt deps

# Run all models
dbt run

# Run tests
dbt test

# Full refresh (rebuilds incremental models from scratch)
dbt build --full-refresh

# Generate and view documentation
dbt docs generate
dbt docs serve
```

## Configuration

The chess.com username is configured as a dbt variable in `dbt_project.yml`:

```yaml
vars:
  chess_username: 'Maxime-ana'
```

Update this to your own chess.com username before running.

## Testing

Schema tests are defined in `models/schema.yml` covering:
- Primary key uniqueness and not-null constraints
- Accepted values for categorical columns (time_class, result, player_color, etc.)
- Not-null checks on critical fields (ratings, timestamps, game IDs)

Run all tests with:
```bash
dbt test
```

## Key Design Decisions

**Incremental silver layer** : silver_games uses incremental materialization with `end_at` as the watermark. New games from the chess.com API are processed without rebuilding the full table.

**Gold as full table rebuilds** : all gold models are materialized as tables, not incremental. Aggregations like win rates and session detection depend on the full dataset, so incremental would require recalculating everything anyway.

**Player perspective in silver** : the chess.com API returns data from both white and black perspectives. Silver determines which side the player was on once, then all downstream columns (ratings, results) are from the player's perspective.

**CTE-based transformations** : silver and gold models use CTEs to avoid repeating logic. Player color is determined once in a base CTE and reused throughout.

**Session detection** : sessions are partitioned by time_class so rating tracking is meaningful within each time control. A 30-minute gap between games of the same type starts a new session.