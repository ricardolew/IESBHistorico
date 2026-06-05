from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from iesbhistorico.analytics.phrase_timelines import rebuild_timelines
from iesbhistorico.cli.build_all import BuildConfig, run_full_build
from iesbhistorico.cli.ingest_raw import ingest_directory
from iesbhistorico.embeddings.embedding_cache import build_embedding_manifest
from iesbhistorico.features.build_dataset import build_dataset
from iesbhistorico.features.build_features import build_features
from iesbhistorico.inference.predict import predict_phrase
from iesbhistorico.storage.duckdb_store import validate_duckdb_parquet_views
from iesbhistorico.training.train_decade_model import train_model


class SmokePipelineTest(unittest.TestCase):
    def test_phrase_to_decade_distribution(self) -> None:
        fixture_dir = Path(__file__).parent / "fixtures" / "raw"
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            parquet_dir = tmp_path / "parquet"
            dataset_path = tmp_path / "training.jsonl"
            model_path = tmp_path / "model.json"

            totals = ingest_directory(fixture_dir, parquet_dir)
            self.assertEqual(totals["articles"], 2)
            self.assertGreater(totals["phrases"], 0)
            self.assertGreater(rebuild_timelines(parquet_dir)["phrase_timelines"], 0)
            self.assertGreater(build_features(parquet_dir, min_count=1), 0)
            self.assertGreater(build_embedding_manifest(parquet_dir), 0)
            self.assertGreater(build_dataset(parquet_dir, dataset_path), 0)
            train_model(dataset_path, model_path)

            old_phrase = predict_phrase("telegram office", model_path)
            modern_phrase = predict_phrase("streaming platform", model_path)

            self.assertAlmostEqual(sum(old_phrase["decades"].values()), 1.0, places=5)
            self.assertAlmostEqual(sum(modern_phrase["decades"].values()), 1.0, places=5)
            self.assertEqual(old_phrase["top_decade"], "1900s")
            self.assertEqual(modern_phrase["top_decade"], "2020s")

    def test_full_build_command_pipeline(self) -> None:
        fixture_dir = Path(__file__).parent / "fixtures" / "raw"
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            parquet_dir = tmp_path / "parquet"
            dataset_path = tmp_path / "training.jsonl"
            model_path = tmp_path / "model.json"
            checkpoint_path = tmp_path / "build_checkpoint.json"

            config = BuildConfig(
                start_year=1900,
                end_year=2020,
                raw_dir=fixture_dir,
                parquet_dir=parquet_dir,
                dataset_path=dataset_path,
                model_path=model_path,
                min_count=1,
                api_key=None,
                    skip_download=True,
                    max_429_retries=10,
                    initial_backoff_seconds=20.0,
                    sample_one_year_per_decade=False,
                    max_phrases_per_article=300,
                    context_radius=40,
                    checkpoint_path=checkpoint_path,
                reset_checkpoints=False,
            )
            run_full_build(config)

            self.assertTrue((parquet_dir / "articles" / "year=1900" / "month=01" / "part.parquet").exists())
            self.assertTrue((parquet_dir / "phrases" / "year=2020" / "month=01" / "part.parquet").exists())
            self.assertTrue((parquet_dir / "phrase_timelines" / "part.parquet").exists())
            self.assertTrue((parquet_dir / "phrase_statistics" / "part.parquet").exists())
            self.assertTrue((parquet_dir / "features" / "part.parquet").exists())
            self.assertTrue((parquet_dir / "embeddings" / "part.parquet").exists())
            self.assertTrue(dataset_path.exists())
            self.assertTrue(model_path.exists())
            self.assertGreater(validate_duckdb_parquet_views(parquet_dir)["features"], 0)

            prediction = predict_phrase("streaming platform", model_path)
            self.assertEqual(prediction["top_decade"], "2020s")

            run_full_build(config)
            self.assertTrue(checkpoint_path.exists())


if __name__ == "__main__":
    unittest.main()
