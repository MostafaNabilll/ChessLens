# ChessLens

A personal chess analytics platform that reveals patterns chess.com doesn't show you.

Built end-to-end: API ingestion, medallion architecture transformations, orchestration, and an interactive dashboard.

![Dashboard Overview](docs/dashboard_overview.png)

![Tilt Tracker](docs/dashboard_tilt.png)

## What It Does

Chess.com gives you basic stats. ChessLens goes deeper:

- **Tilt Analysis** - tracks how consecutive losses affect your next game
- **Time-of-Day Patterns** - heatmap of when you play your best chess
- **Session Insights** - how session length impacts your rating
- **Opening Trends** - monthly win rate trends with improving/declining detection
- **Opponent Analysis** - performance by opponent strength with upset tracking
- **Time Control Comparison** - side-by-side metrics across bullet, blitz, rapid

## Sample Findings (from 1,379 games)

- **No tilt detected.** Win rate after 3+ consecutive losses: 59.5%. Normal win rate: 50.4%. Losing streaks apparently make me focus harder.
- **Night chess is bad.** Monday night blitz: 14.3% win rate. Tuesday night blitz: 20%. The data says close the laptop after midnight.
- **Scotch Game is improving.** Rapid win rate went from 44% in January to 61% in March. The study is paying off.
- **18% of bullet games lost on time.** Nearly one in five. Bullet might not be my format.
- **6-10 game sessions are the sweet spot.** Shorter sessions average -0.9 rating. 6-10 game sessions average +7.1.
- **14-game win streak.** Didn't know about this until the data surfaced it.
- **White slightly better.** 51.5% win rate as white vs 48.8% as black.

## Architecture

```
chess.com API → Python ingestion → DuckDB (bronze)
                                      ↓
                                  dbt-core (silver)
                                      ↓
                                  dbt-core (gold)
                                      ↓
                                  Streamlit dashboard

Dagster orchestrates the full pipeline on a daily schedule.
```

### dbt Lineage

![dbt Lineage](docs/dbt_lineage.png)

### Dagster Pipeline

![Dagster Run](docs/dagster_run.png)

## Stack

| Layer          | Tool              | Why                                                    |
|----------------|-------------------|--------------------------------------------------------|
| Ingestion      | Python + requests | Direct API calls with rate limiting and backfill logic |
| Storage        | DuckDB            | Local analytical database, fits in memory              |
| Transformation | dbt-core          | Medallion architecture with tests and documentation    |
| Orchestration  | Dagster           | Asset-based DAG with dbt integration and scheduling    |
| Dashboard      | Streamlit + Plotly| Interactive filters, heatmaps, and trend charts        |

## Data Model

![ERD](docs/erd.png)

### Bronze
Raw JSON from the chess.com API stored as-is. Source of truth.

### Silver
Parsed, typed, deduplicated game records. Player perspective applied (ratings, results, openings). Incremental materialization.

### Gold

| Model                        | What It Answers                                          |
|------------------------------|----------------------------------------------------------|
| `gold_tilt_analysis`         | Does losing make me lose more?                           |
| `gold_time_of_day`           | When am I sharpest?                                      |
| `gold_sessions`              | How many games should I play in one sitting?             |
| `gold_opening_trends`        | Which openings are improving or declining?               |
| `gold_opponent_analysis`     | How do I perform against stronger vs weaker opponents?   |
| `gold_time_control_comparison`| Am I better at blitz or rapid?                          |

## Setup

### Prerequisites
- Python 3.10+
- A chess.com account with game history

### Installation

```bash
git clone https://github.com/MostafaNabilll/chesslens.git
cd chesslens

python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\Activate

pip install -r requirements.txt
```

### Configuration

Create a `.env` file in the project root:

```
CHESS_USERNAME=your_chess_com_username
CHESSLENS_DB_PATH=full/path/to/chesslens/data/chesslens.duckdb
```

Update the chess username in `dbt_chesslens/dbt_project.yml`:

```yaml
vars:
  chess_username: 'your_chess_com_username'
```

### Run the Pipeline

```bash
# Backfill all historical games
python ingestion/extract.py --backfill

# Run dbt transformations
cd dbt_chesslens
dbt build
cd ..

# Launch the dashboard
streamlit run dashboard/app.py

# Or use Dagster to orchestrate everything
dagster dev -m orchestration.definitions
```

## Project Structure

```
chesslens/
├── ingestion/
│   └── extract.py              # Chess.com API ingestion with backfill and incremental
├── dbt_chesslens/
│   ├── models/
│   │   ├── bronze/             # Raw data, no transformations
│   │   ├── silver/             # Cleaned, typed, deduplicated
│   │   └── gold/               # Analytics-ready aggregations
│   ├── models/schema.yml       # Column docs and tests
│   ├── dbt_project.yml
│   └── profiles.yml
├── orchestration/
│   ├── assets.py               # Dagster assets (ingestion + dbt)
│   └── definitions.py          # Job, schedule, and resource config
├── dashboard/
│   └── app.py                  # Streamlit app with 6 analytics pages
├── data/                       # DuckDB database (gitignored)
├── docs/                       # Screenshots and documentation
├── .env.example
├── requirements.txt
└── README.md
```

## Key Design Decisions

**DuckDB over Spark** - 1,300 games fit in memory. Using distributed computing here would be overengineering.

**Dagster over Airflow** - The asset model maps to the medallion pattern. Built-in dbt integration. Local dev without Docker.

**Incremental silver, full-refresh gold** - Silver appends new games. Gold models are aggregations over all data, so they rebuild fully each run.

**Player perspective in silver** - Chess.com returns data for both sides. Silver figures out which side is the player once in a CTE. Everything downstream uses the clean columns.

## Roadmap

- **Multi-user support** - username input on the dashboard triggers ingestion and transformation for any chess.com player
- **Game replay viewer** - interactive move-by-move replay with board visualization, powered by PGN data
- **PGN parsing** - extract move count, game duration, and time-per-move analysis
- **Win rate by color** - performance comparison as white vs black
- **Deployed dashboard** - Streamlit Cloud deployment for public access

## License

MIT