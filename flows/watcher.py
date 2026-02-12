from __future__ import annotations

from pathlib import Path

from prefect.deployments import Deployment
from prefect.server.schemas.schedules import CronSchedule

from src.watcher.main import watcher_flow, FEEDS_PATH


def build_watcher_deployment(config_path: Path | None = None) -> Deployment:
    schedule = CronSchedule(cron="*/5 * * * *", timezone="UTC")
    return Deployment.build_from_flow(
        flow=watcher_flow,
        name="watcher-prod",
        version=None,
        parameters={"config_path": str(config_path or FEEDS_PATH)},
        schedule=schedule,
    )


if __name__ == "__main__":
    deployment = build_watcher_deployment()
    deployment.apply()
