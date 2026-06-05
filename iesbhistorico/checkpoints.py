from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class BuildCheckpoint:
    path: Path
    run_key: str
    completed_steps: set[str] = field(default_factory=set)
    step_results: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path, run_key: str) -> "BuildCheckpoint":
        if not path.exists():
            return cls(path=path, run_key=run_key)
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("run_key") != run_key:
            return cls(path=path, run_key=run_key)
        return cls(
            path=path,
            run_key=run_key,
            completed_steps=set(payload.get("completed_steps", [])),
            step_results=dict(payload.get("step_results", {})),
        )

    def is_complete(self, step_id: str) -> bool:
        return step_id in self.completed_steps

    def mark_complete(self, step_id: str, result: object) -> None:
        self.completed_steps.add(step_id)
        self.step_results[step_id] = {
            "completed_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "result": _jsonable(result),
        }
        self.save()

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "run_key": self.run_key,
            "completed_steps": sorted(self.completed_steps),
            "step_results": self.step_results,
        }
        tmp_path = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp_path.replace(self.path)

    def reset(self) -> None:
        self.completed_steps.clear()
        self.step_results.clear()
        if self.path.exists():
            self.path.unlink()


def _jsonable(value: object) -> object:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)
