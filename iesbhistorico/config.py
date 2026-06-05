from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PARQUET_DIR = DATA_DIR / "parquet"
DUCKDB_DIR = DATA_DIR / "duckdb"
DATASETS_DIR = DATA_DIR / "datasets"
MODELS_DIR = DATA_DIR / "models"
REPORTS_DIR = DATA_DIR / "reports"
DEFAULT_DATASET_PATH = DATASETS_DIR / "training_dataset.jsonl"
DEFAULT_MODEL_PATH = MODELS_DIR / "decade_model.json"
DEFAULT_TFIDF_MODEL_PATH = MODELS_DIR / "decade_model_tfidf.joblib"
DEFAULT_CHECKPOINT_PATH = DATA_DIR / "build_checkpoint.json"


@dataclass(frozen=True)
class Settings:
    dataset_path: Path = DEFAULT_DATASET_PATH
    model_path: Path = DEFAULT_MODEL_PATH
    raw_dir: Path = RAW_DIR


def ensure_data_dirs() -> None:
    for path in [
        DATA_DIR,
        RAW_DIR,
        DATA_DIR / "normalized",
        PARQUET_DIR,
        DUCKDB_DIR,
        DATA_DIR / "embeddings",
        DATASETS_DIR,
        MODELS_DIR,
        REPORTS_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)
