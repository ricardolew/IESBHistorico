from __future__ import annotations

import argparse
import hashlib
import json
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from iesbhistorico.analytics.phrase_timelines import rebuild_timelines
from iesbhistorico.checkpoints import BuildCheckpoint
from iesbhistorico.cli.ingest_raw import ingest_directory
from iesbhistorico.config import (
    DEFAULT_CHECKPOINT_PATH,
    DEFAULT_DATASET_PATH,
    DEFAULT_MODEL_PATH,
    PARQUET_DIR,
    RAW_DIR,
    ensure_data_dirs,
)
from iesbhistorico.downloader.nyt_downloader import download_month
from iesbhistorico.embeddings.embedding_cache import build_embedding_manifest
from iesbhistorico.features.build_dataset import build_dataset
from iesbhistorico.features.build_features import build_features
from iesbhistorico.logging_utils import configure_logging
from iesbhistorico.sampling import SAMPLED_MONTHS_PER_YEAR, one_year_per_decade, sampled_year_months
from iesbhistorico.storage.duckdb_store import validate_duckdb_parquet_views
from iesbhistorico.training.train_decade_model import train_model

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class BuildConfig:
    start_year: int
    end_year: int
    raw_dir: Path
    parquet_dir: Path
    dataset_path: Path
    model_path: Path
    min_count: int
    api_key: str | None
    skip_download: bool
    max_429_retries: int
    initial_backoff_seconds: float
    sample_one_year_per_decade: bool
    max_phrases_per_article: int | None
    context_radius: int
    checkpoint_path: Path
    reset_checkpoints: bool


def run_full_build(config: BuildConfig) -> None:
    ensure_data_dirs()
    _validate_year_range(config.start_year, config.end_year)

    LOGGER.info("Building dataset for years %s-%s", config.start_year, config.end_year)
    LOGGER.info("Raw directory: %s", config.raw_dir)
    LOGGER.info("Parquet source of truth: %s", config.parquet_dir)
    if config.sample_one_year_per_decade:
        LOGGER.info(
            "Sampling preset enabled: years=%s months=%s",
            one_year_per_decade(config.start_year, config.end_year),
            list(SAMPLED_MONTHS_PER_YEAR),
        )
    LOGGER.info("Max phrases per article: %s", config.max_phrases_per_article)
    LOGGER.info("Context radius: %s", config.context_radius)
    LOGGER.info("Training dataset: %s", config.dataset_path)
    LOGGER.info("Model output: %s", config.model_path)
    LOGGER.info("Checkpoint file: %s", config.checkpoint_path)

    checkpoint = BuildCheckpoint.load(config.checkpoint_path, _run_key(config))
    if config.reset_checkpoints:
        LOGGER.info("Resetting build checkpoints before starting")
        checkpoint.reset()

    steps: list[tuple[str, str, Callable[[], object]]] = [
        ("download", "Download NYT archive JSON", lambda: _download_year_range(config)),
        (
            "ingest_parquet",
            "Parse, clean, extract phrases, and replace year/month Parquet partitions",
            lambda: ingest_directory(
                config.raw_dir,
                config.parquet_dir,
                config.start_year,
                config.end_year,
                years=_selected_years(config),
                months=_selected_months(config),
                max_phrases_per_article=config.max_phrases_per_article,
                context_radius=config.context_radius,
            ),
        ),
        ("aggregate_timelines", "Recompute normalized phrase timeline Parquet", lambda: rebuild_timelines(config.parquet_dir)),
        ("build_features", "Recompute feature Parquet", lambda: build_features(config.parquet_dir, config.min_count)),
        ("build_embeddings", "Recompute embedding manifest Parquet", lambda: build_embedding_manifest(config.parquet_dir)),
        ("validate_duckdb", "Validate DuckDB analytical queries over Parquet", lambda: validate_duckdb_parquet_views(config.parquet_dir)),
        ("build_dataset", "Build training JSONL from feature Parquet", lambda: build_dataset(config.parquet_dir, config.dataset_path)),
        ("train_model", "Train decade probability model", lambda: train_model(config.dataset_path, config.model_path)),
    ]

    total_steps = len(steps)
    started = time.perf_counter()
    for index, (step_id, name, action) in enumerate(steps, start=1):
        if checkpoint.is_complete(step_id):
            LOGGER.info(
                "Step %s/%s skipped from checkpoint: %s (%.1f%% done)",
                index,
                total_steps,
                name,
                index / total_steps * 100,
            )
            continue
        step_started = time.perf_counter()
        LOGGER.info("Step %s/%s started: %s", index, total_steps, name)
        result = action()
        checkpoint.mark_complete(step_id, result)
        elapsed = time.perf_counter() - step_started
        LOGGER.info(
            "Step %s/%s complete: %s (%.1f%% done, %.2fs, result=%s)",
            index,
            total_steps,
            name,
            index / total_steps * 100,
            elapsed,
            _short_result(result),
        )
    LOGGER.info("Full build complete in %.2fs", time.perf_counter() - started)


def _download_year_range(config: BuildConfig) -> int:
    if config.skip_download:
        LOGGER.info("Download skipped by --skip-download")
        return 0
    if not config.api_key:
        LOGGER.info("Download skipped because --api-key was not provided; using existing files in %s", config.raw_dir)
        return 0

    months = _selected_year_months(config)
    downloaded = 0
    for index, (year, month) in enumerate(months, start=1):
        LOGGER.info(
            "Download progress: %s/%s months (%.1f%%) - %s-%02d",
            index,
            len(months),
            index / max(len(months), 1) * 100,
            year,
            month,
        )
        download_month(
            year,
            month,
            config.api_key,
            config.raw_dir,
            max_429_retries=config.max_429_retries,
            initial_backoff_seconds=config.initial_backoff_seconds,
        )
        downloaded += 1
    return downloaded


def _validate_year_range(start_year: int, end_year: int) -> None:
    if start_year > end_year:
        raise ValueError("--start-year must be less than or equal to --end-year")
    if start_year < 1850:
        LOGGER.warning("Start year %s is earlier than the default model fallback range.", start_year)


def _short_result(result: object) -> str:
    if isinstance(result, dict):
        return f"{len(result)} items"
    return str(result)


def _run_key(config: BuildConfig) -> str:
    payload = {
        "start_year": config.start_year,
        "end_year": config.end_year,
        "raw_dir": str(config.raw_dir.resolve()),
        "parquet_dir": str(config.parquet_dir.resolve()),
        "dataset_path": str(config.dataset_path.resolve()),
        "model_path": str(config.model_path.resolve()),
        "min_count": config.min_count,
        "skip_download": config.skip_download,
        "sample_one_year_per_decade": config.sample_one_year_per_decade,
        "max_phrases_per_article": config.max_phrases_per_article,
        "context_radius": config.context_radius,
    }
    encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _selected_year_months(config: BuildConfig) -> list[tuple[int, int]]:
    if config.sample_one_year_per_decade:
        return sampled_year_months(config.start_year, config.end_year)
    return [(year, month) for year in range(config.start_year, config.end_year + 1) for month in range(1, 13)]


def _selected_years(config: BuildConfig) -> set[int] | None:
    if not config.sample_one_year_per_decade:
        return None
    return set(one_year_per_decade(config.start_year, config.end_year))


def _selected_months(config: BuildConfig) -> set[int] | None:
    if not config.sample_one_year_per_decade:
        return None
    return set(SAMPLED_MONTHS_PER_YEAR)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the full immutable Parquet phrase decade dataset and model build pipeline."
    )
    parser.add_argument("--api-key", help="NYT Archive API key. If omitted, download is skipped.")
    parser.add_argument("--skip-download", action="store_true", help="Use existing raw files without downloading.")
    parser.add_argument("--start-year", type=int, default=1950, help="First year to include. Default: 1950.")
    parser.add_argument("--end-year", type=int, default=1999, help="Last year to include. Default: 1999.")
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--parquet-dir", type=Path, default=PARQUET_DIR)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET_PATH)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument("--max-429-retries", type=int, default=10)
    parser.add_argument("--initial-backoff-seconds", type=float, default=20.0)
    parser.add_argument(
        "--sample-one-year-per-decade",
        action="store_true",
        help="Use one representative year per decade and months 1, 4, 7, 10.",
    )
    parser.add_argument("--max-phrases-per-article", type=int, default=300)
    parser.add_argument("--context-radius", type=int, default=40)
    parser.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT_PATH)
    parser.add_argument("--reset-checkpoints", action="store_true", help="Ignore and clear prior completed-step checkpoints.")
    parser.add_argument("--min-count", type=int, default=2)
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    configure_logging(args.log_level)
    run_full_build(
        BuildConfig(
            start_year=args.start_year,
            end_year=args.end_year,
            raw_dir=args.raw_dir,
            parquet_dir=args.parquet_dir,
            dataset_path=args.dataset,
            model_path=args.model,
            min_count=args.min_count,
            api_key=args.api_key,
            skip_download=args.skip_download,
            max_429_retries=args.max_429_retries,
            initial_backoff_seconds=args.initial_backoff_seconds,
            sample_one_year_per_decade=args.sample_one_year_per_decade,
            max_phrases_per_article=args.max_phrases_per_article,
            context_radius=args.context_radius,
            checkpoint_path=args.checkpoint,
            reset_checkpoints=args.reset_checkpoints,
        )
    )


if __name__ == "__main__":
    main()
