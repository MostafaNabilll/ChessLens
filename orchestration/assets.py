from dagster import asset, AssetExecutionContext
from dagster_dbt import DbtCliResource, dbt_assets
from pathlib import Path
import os
import sys
import json


sys.path.insert(0, str(Path(__file__).parent.parent))
from ingestion.extract import incremental

DBT_PROJECT_DIR = Path(__file__).parent.parent / "dbt_chesslens"
DBT_PROFILES_DIR = DBT_PROJECT_DIR
DBT_MANIFEST_PATH = DBT_PROJECT_DIR / "target" / "manifest.json"


@asset(group_name="ingestion")
def raw_games():
    """Pull latest games from chess.com API into DuckDB."""
    username = os.getenv("CHESS_USERNAME")
    incremental(username)


@dbt_assets(manifest=DBT_MANIFEST_PATH)
def chesslens_dbt_assets(context: AssetExecutionContext, dbt: DbtCliResource):
    username = os.getenv("CHESS_USERNAME")
    yield from dbt.cli(
        ["build", "--vars", json.dumps({"chess_username": username})],
        context=context
    ).stream()