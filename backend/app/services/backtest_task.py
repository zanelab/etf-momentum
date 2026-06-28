"""Backtest task lifecycle: JSON file persistence under data/backtest_tasks/."""
from __future__ import annotations

import json
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from app.services.types import StrategyParams

TASK_DIR = Path(__file__).resolve().parents[2] / "data" / "backtest_tasks"


def _ensure_dir() -> Path:
    TASK_DIR.mkdir(parents=True, exist_ok=True)
    return TASK_DIR


def _task_path(task_id: str) -> Path:
    return _ensure_dir() / f"{task_id}.json"


def create_task(
    *,
    start,
    end,
    params: StrategyParams,
    static_pool: list[str],
    themes: dict,
    display_names: dict,
) -> str:
    task_id = uuid.uuid4().hex[:12]
    payload = {
        "task_id": task_id,
        "status": "running",
        "created_at": datetime.utcnow().isoformat(),
        "request": {
            "start": start.isoformat() if hasattr(start, "isoformat") else str(start),
            "end": end.isoformat() if hasattr(end, "isoformat") else str(end),
            "params": params.model_dump(),
            "static_pool": static_pool,
            "themes": themes,
            "display_names": display_names,
        },
        "result": None,
    }
    _task_path(task_id).write_text(json.dumps(payload, ensure_ascii=False))
    return task_id


def get_task(task_id: str) -> dict[str, Any] | None:
    path = _task_path(task_id)
    if not path.exists():
        return None
    return json.loads(path.read_text())


def _update(task_id: str, **fields) -> None:
    path = _task_path(task_id)
    payload = json.loads(path.read_text())
    payload.update(fields)
    path.write_text(json.dumps(payload, ensure_ascii=False))


def mark_running(task_id: str) -> None:
    _update(task_id, status="running", started_at=datetime.utcnow().isoformat())


def mark_completed(task_id: str, result: dict[str, Any]) -> None:
    _update(
        task_id,
        status="completed",
        completed_at=datetime.utcnow().isoformat(),
        result=result,
    )


def mark_failed(task_id: str, error: str) -> None:
    _update(
        task_id,
        status="failed",
        completed_at=datetime.utcnow().isoformat(),
        error=error,
    )
