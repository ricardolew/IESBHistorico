from __future__ import annotations

from pathlib import Path
from typing import Protocol

from iesbhistorico.config import DEFAULT_MODEL_PATH, DEFAULT_TFIDF_MODEL_PATH
from iesbhistorico.modeling.decade_model import DecadeProfileModel
from iesbhistorico.modeling.tfidf_model import TfidfDecadeModel


class PredictiveModel(Protocol):
    def predict(self, phrase: str) -> dict[str, float]:
        ...


def default_model_path(model_type: str) -> Path:
    if model_type == "profile":
        return DEFAULT_MODEL_PATH
    if model_type == "tfidf":
        return DEFAULT_TFIDF_MODEL_PATH
    raise ValueError(f"Unsupported model type: {model_type}")


def load_model(model_type: str = "profile", model_path: Path | None = None) -> PredictiveModel:
    path = model_path or default_model_path(model_type)
    if model_type == "profile":
        return DecadeProfileModel.load(path) if path.exists() else DecadeProfileModel.fallback()
    if model_type == "tfidf":
        if not path.exists():
            raise FileNotFoundError(f"TF-IDF model not found: {path}")
        return TfidfDecadeModel.load(path)
    raise ValueError(f"Unsupported model type: {model_type}")

