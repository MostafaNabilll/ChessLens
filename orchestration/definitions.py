from dagster import Definitions, ScheduleDefinition, define_asset_job
from dagster_dbt import DbtCliResource
from .assets import raw_games, chesslens_dbt_assets, DBT_PROJECT_DIR, DBT_PROFILES_DIR
import sys
from pathlib import Path
import shutil

chesslens_job = define_asset_job("chesslens_job", selection="*")

chesslens_schedule = ScheduleDefinition(
    job=chesslens_job,
    cron_schedule="0 6 * * *",
)

DBT_EXECUTABLE = shutil.which("dbt") or str(Path(sys.executable).parent / "dbt")

defs = Definitions(
    assets=[raw_games, chesslens_dbt_assets],
    schedules=[chesslens_schedule],
    resources={
        "dbt": DbtCliResource(
            project_dir=str(DBT_PROJECT_DIR),
            profiles_dir=str(DBT_PROFILES_DIR),
            dbt_executable=DBT_EXECUTABLE,
        ),
    },
)