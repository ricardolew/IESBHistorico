from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

import pandas as pd


PART_FILE = "part.parquet"


def stable_hash(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def partition_dir(root: Path, dataset: str, **partitions: int | str) -> Path:
    path = root / dataset
    for key, value in partitions.items():
        path = path / f"{key}={value}"
    return path


def partition_file(root: Path, dataset: str, **partitions: int | str) -> Path:
    return partition_dir(root, dataset, **partitions) / PART_FILE


def write_partition(
    frame: pd.DataFrame,
    root: Path,
    dataset: str,
    compression: str = "zstd",
    **partitions: int | str,
) -> Path:
    target_dir = partition_dir(root, dataset, **partitions)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / PART_FILE
    tmp_target = target_dir / f"{PART_FILE}.{stable_hash({'dataset': dataset, 'partitions': partitions})}.tmp"
    frame.to_parquet(tmp_target, index=False, compression=compression)
    tmp_target.replace(target)
    return target


def replace_dataset(frame: pd.DataFrame, root: Path, dataset: str, compression: str = "zstd") -> Path:
    target_dir = root / dataset
    tmp_dir = root / f".{dataset}.{stable_hash({'rows': len(frame), 'columns': list(frame.columns)})}.tmp"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(tmp_dir / PART_FILE, index=False, compression=compression)
    if target_dir.exists():
        shutil.rmtree(target_dir)
    tmp_dir.replace(target_dir)
    return target_dir / PART_FILE


def dataset_glob(root: Path, dataset: str) -> str:
    return str((root / dataset / "**" / "*.parquet").resolve()).replace("\\", "/")


def read_dataset(root: Path, dataset: str, columns: list[str] | None = None) -> pd.DataFrame:
    files = sorted((root / dataset).glob("**/*.parquet"))
    if not files:
        return pd.DataFrame(columns=columns or [])
    return pd.concat((pd.read_parquet(file, columns=columns) for file in files), ignore_index=True)


def remove_tmp_paths(root: Path) -> None:
    for path in root.glob("**/*.tmp"):
        if path.is_file():
            path.unlink()
    for path in root.glob("**/*.tmp"):
        if path.is_dir():
            shutil.rmtree(path)
