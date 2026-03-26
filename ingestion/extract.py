"""
ChessLens - Chess.com Game Ingestion

Pulls your games from the chess.com public API and loads them into DuckDB.

Usage:
    python extract.py --backfill              # Pull all historical games
    python extract.py                          # Pull current month only (incremental)
    python extract.py --username someone_else  # Pull a different player's games

API docs: https://www.chess.com/news/view/published-data-api
"""
from dotenv import load_dotenv
import argparse
import os
import requests
import duckdb
import time
import json 

load_dotenv() 

BASE_URL = "https://api.chess.com/pub"

HEADERS = {
    "User-Agent": "ChessLens/1.0 (github.com/MostafaNabilll/chesslens)"
}

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "chesslens.duckdb")


def get_game_archives(username: str) -> list[str]:
    """Fetch all monthly archive URLs for a given chess.com player."""
    archives_endpoint = f"{BASE_URL}/player/{username}/games/archives"
    response = requests.get(archives_endpoint, headers=HEADERS)
    response.raise_for_status()
    data = response.json()
    archives = data.get("archives", [])
    print(f"Found {len(archives)} monthly archives")
    return archives


def get_games_for_month(archive_url: str) -> list[dict]:
    """Fetch all games for a single monthly archive URL."""
    time.sleep(1)
    response = requests.get(archive_url, headers=HEADERS)
    response.raise_for_status()
    data = response.json()
    games = data.get('games', [])
    print(f"Found {len(games)} games for {archive_url}")
    return games


def load_to_duckdb(games: list[dict], db_path: str):
    """Load raw game JSON into DuckDB, skipping duplicates."""
    conn = duckdb.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS raw_games (
            game_url TEXT PRIMARY KEY,
            game_json JSON
        )
    """)
    for game in games:
        game_url = game.get('url')
        if not game_url:
            continue
        try:
            conn.execute("""
                INSERT INTO raw_games (game_url, game_json)
                VALUES (?, ?)
                ON CONFLICT (game_url) DO NOTHING
            """, (game_url, json.dumps(game)))
        except Exception as e:
            print(f'Error inserting game {game_url}: {e}')
    conn.close()
    print(f"Loaded {len(games)} games into DuckDB")


def backfill(username: str):
    """Pull all historical games from chess.com and load into DuckDB."""
    archives = get_game_archives(username)
    for archive_url in archives:
        print(f"Processing archive: {archive_url}")
        games = get_games_for_month(archive_url)
        load_to_duckdb(games, DB_PATH)
    print(f"Backfill complete. Processed {len(archives)} monthly archives.")


def incremental(username: str):
    """Pull only the current month's games and load into DuckDB."""
    current_year = time.strftime("%Y")
    current_month = time.strftime("%m")
    archive_url = f"{BASE_URL}/player/{username}/games/{current_year}/{current_month}"
    print(f"Processing incremental load for {archive_url}")
    games = get_games_for_month(archive_url)
    load_to_duckdb(games, DB_PATH)
    print(f"Incremental load complete. Processed {len(games)} games for {current_year}-{current_month}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ChessLens - Ingest chess.com games")
    parser.add_argument("--username", default=os.getenv("CHESS_USERNAME"), help="Chess.com username")
    parser.add_argument("--backfill", action="store_true", help="Pull all historical games")
    args = parser.parse_args()

    if not args.username:
        print("Error: provide --username or set CHESS_USERNAME env var")
        exit(1)

    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    if args.backfill:
        print(f"Backfilling all games for {args.username}...")
        backfill(args.username)
    else:
        print(f"Incremental load for {args.username}...")
        incremental(args.username)