# IESBHistorico

Historical phrase decade classifier built from the New York Times Archive API.

The project has one required final behavior:

```text
input:  "telegram office"
output: likelihood that the phrase belongs to each decade
```

Example output:

```json
{
  "phrase": "telegram office",
  "decades": {
    "1890s": 0.08,
    "1900s": 0.24,
    "1910s": 0.43,
    "1920s": 0.19,
    "1930s": 0.06
  },
  "top_decade": "1910s",
  "confidence": 0.43
}
```

Do not train a model that predicts only one year. The model must predict a probability distribution over decades.

## Quick Start

Run the automated smoke tests first:

```bash
python -m unittest discover tests
```

Then build a compact real dataset and train the model:

```bash
python build_all.py --api-key YOUR_NYT_KEY --start-year 1950 --end-year 1999 --sample-one-year-per-decade
```

This compact mode downloads and processes:

```text
years: 1950, 1960, 1970, 1980, 1990
months: 1, 4, 7, 10
```

After the build finishes, make a prediction:

```bash
python predict.py "streaming platform"
```

Example output:

```json
{
  "phrase": "streaming platform",
  "decades": {
    "1990s": 0.03,
    "2000s": 0.12,
    "2010s": 0.35,
    "2020s": 0.50
  },
  "top_decade": "2020s",
  "confidence": 0.50
}
```

To run the curated sample input repository and register predictions:

```bash
python run_input_sample.py
```

This reads `sample_inputs/phrases.jsonl` and writes:

```text
sample_inputs/results/predictions.md
sample_inputs/results/predictions.jsonl
```

To validate sample/evaluation input files:

```bash
python validate_input_sets.py
```

To run a versioned formal evaluation:

```bash
python evaluate_predictions.py --run-id profile-baseline-current
```

Evaluation outputs are written under:

```text
evaluation_results/RUN_ID/
  metrics.md
  metrics.json
  predictions.jsonl
  confusion_matrix.csv
```

To compare evaluation runs:

```bash
python compare_evaluation_runs.py profile-baseline-current tfidf-5000-current profile-balanced-current
```

To train and evaluate the experimental TF-IDF model:

```bash
python train_tfidf.py --max-rows 5000
python evaluate_predictions.py --model-type tfidf --run-id tfidf-5000-current
```

To train and evaluate the balanced profile model without overwriting the baseline:

```bash
python train.py --balance-decades --model data/models/decade_model_balanced.json
python evaluate_predictions.py --model data/models/decade_model_balanced.json --run-id profile-balanced-current
python run_input_sample.py --model data/models/decade_model_balanced.json --markdown-output sample_inputs/results/predictions_balanced.md --jsonl-output sample_inputs/results/predictions_balanced.jsonl
```

To generate corpus and target diagnostics:

```bash
python analyze_corpus_distribution.py
python inspect_phrase_target.py "moon landing" --output docs/generated/target_moon_landing.md
```

To generate optional real embeddings for a small controlled subset:

```bash
python build_real_embeddings.py --max-rows 1000
```

If the build stops, run the same `build_all.py` command again. Completed stages are checkpointed in `data/build_checkpoint.json`.

To force a clean rebuild:

```bash
python build_all.py --api-key YOUR_NYT_KEY --start-year 1950 --end-year 1999 --sample-one-year-per-decade --reset-checkpoints
```

## Step-By-Step Pipeline

The single-command build is recommended:

```bash
python build_all.py --api-key YOUR_NYT_KEY --start-year 1950 --end-year 1999 --sample-one-year-per-decade
```

It runs these stages:

1. Download raw NYT archive JSON into `data/raw/`.
2. Parse, clean, and extract article phrases.
3. Write immutable year/month Parquet partitions under `data/parquet/articles/` and `data/parquet/phrases/`.
4. Rebuild normalized phrase timelines in `data/parquet/phrase_timelines/`.
5. Rebuild phrase statistics in `data/parquet/phrase_statistics/`.
6. Rebuild feature rows in `data/parquet/features/`.
7. Rebuild the embedding manifest in `data/parquet/embeddings/`.
8. Validate DuckDB queries over the Parquet datasets.
9. Build `data/datasets/training_dataset.jsonl`.
10. Train and save `data/models/decade_model.json`.

Manual equivalent:

```bash
python ingest.py --raw-dir data/raw --parquet-dir data/parquet
python aggregate.py --parquet-dir data/parquet
python build_features.py --parquet-dir data/parquet
python build_embeddings.py --parquet-dir data/parquet
python validate_duckdb.py --parquet-dir data/parquet
python build_dataset.py --parquet-dir data/parquet
python train.py
python predict.py "streaming platform"
```

Useful smaller-file options:

```bash
python build_all.py --api-key YOUR_NYT_KEY --sample-one-year-per-decade --max-phrases-per-article 200 --context-radius 20
```

## Pipeline

```text
NYT Archive API
  -> raw JSON
  -> cleaned articles
  -> extracted phrases with context
  -> yearly and decade frequency tables
  -> normalized phrase timelines
  -> training dataset
  -> decade probability model
  -> phrase prediction API
```

## Data Source

Use the NYT Archive API:

```text
https://api.nytimes.com/svc/archive/v1/{year}/{month}.json?api-key=YOUR_KEY
```

Useful article fields:

- `_id`
- `pub_date`
- `headline.main`
- `abstract`
- `snippet`
- `lead_paragraph`
- `keywords`
- `section_name`
- `subsection_name`
- `word_count`

Store raw API responses so ingestion can be resumed without downloading again.

## Phrase Extraction

Extract phrases from:

- Headlines
- Abstracts
- Snippets
- Lead paragraphs
- Keywords

Supported phrase types:

- N-grams
- Noun chunks
- Named entities
- Keyphrases
- Collocations

Store context windows with each phrase. A phrase alone is often ambiguous, so context should be available for features and embeddings.

## Cleaning

Remove noisy phrases before aggregation:

- OCR junk
- Broken Unicode
- Repeated punctuation
- Mostly numeric text
- Very short fragments
- Low alphabetic-ratio strings
- All-caps garbage
- Malformed tokens
- One-off junk phrases

Apply:

- Unicode normalization
- Whitespace normalization
- Punctuation cleanup
- Stopword filtering
- Language filtering
- Minimum length checks

## Normalization

Raw counts are not enough because article volume changes over time.

For each phrase and year, store:

```text
raw_count
normalized_frequency = phrase_count_in_year / total_phrase_count_in_year
```

Also support:

- Log frequency
- Z-score by year
- TF-IDF-like weighting
- Rolling temporal smoothing

The model should learn language timing, not NYT publication volume.

## Storage

Use immutable, partitioned Parquet as the single source of processed truth:

```text
raw NYT JSON
  -> partitioned Parquet articles
  -> partitioned Parquet phrases
  -> recomputable Parquet timelines
  -> recomputable Parquet features
  -> recomputable Parquet embedding manifest
  -> training JSONL
  -> model
```

DuckDB is used only as an analytical query engine over Parquet files. The project does not maintain a separate processed database.

Processed datasets live under:

```text
data/parquet/
  articles/year=YYYY/month=MM/part.parquet
  phrases/year=YYYY/month=MM/part.parquet
  phrase_timelines/part.parquet
  phrase_statistics/part.parquet
  features/part.parquet
  embeddings/part.parquet
```

IDs are deterministic content hashes, so partitions can be safely rebuilt. Stages use temp-write plus replacement semantics instead of append-based mutation.

## Features

Build one training row per phrase.

Features should combine:

- Phrase text embeddings
- Context embeddings when available
- Total frequency
- Normalized frequency by decade
- First year
- Last year
- Peak year
- Peak decade
- Trend slope
- Growth velocity
- Decay velocity
- Temporal entropy
- Decade concentration
- Resurgence score

Embeddings should be cached so reruns do not regenerate them.

Recommended embedding models:

- `all-MiniLM-L6-v2`
- `bge-small-en`
- `e5-small-v2`

## Training Target

The main target is a decade probability distribution.

Example training row:

```json
{
  "phrase": "artificial intelligence",
  "features": {
    "embedding": [],
    "first_year": 1956,
    "last_year": 2025,
    "peak_year": 2023,
    "total_count": 92831,
    "temporal_entropy": 0.71
  },
  "target": {
    "1950s": 0.01,
    "1960s": 0.03,
    "1970s": 0.05,
    "1980s": 0.08,
    "1990s": 0.10,
    "2000s": 0.13,
    "2010s": 0.24,
    "2020s": 0.36
  }
}
```

The target distribution should come from normalized decade frequencies.

Optional secondary outputs can be derived from the distribution:

- Top decade
- Confidence
- Temporal uncertainty
- Peak decade
- Modernity score
- Obsolescence score
- Resurgence score

These are useful, but they are not the core model output.

## Model

Start simple:

- Baseline: multinomial logistic regression or random forest
- Better: LightGBM, XGBoost, or scikit-learn gradient boosting
- Optional: neural model using embeddings plus numeric features

The trained model must expose:

```text
phrase -> {decade: probability}
```

Probabilities must sum to `1.0`.

## Prediction API

Required CLI:

```bash
python predict.py "streaming platform"
```

Required JSON output:

```json
{
  "phrase": "streaming platform",
  "decades": {
    "1990s": 0.03,
    "2000s": 0.12,
    "2010s": 0.35,
    "2020s": 0.50
  },
  "top_decade": "2020s",
  "confidence": 0.50
}
```

## Current Implementation

This repository includes a working first version of the pipeline:

```bash
python build_all.py --api-key YOUR_NYT_KEY
```

By default, `build_all.py` builds only the 1950-1999 dataset. Change the range with:

```bash
python build_all.py --api-key YOUR_NYT_KEY --start-year 1950 --end-year 1999
```

If raw files are already present under `data/raw`, skip downloading:

```bash
python build_all.py --skip-download --start-year 1950 --end-year 1999
```

For a compact sampled corpus, use one year per decade and four evenly spaced months per selected year:

```bash
python build_all.py --api-key YOUR_NYT_KEY --start-year 1950 --end-year 1999 --sample-one-year-per-decade
```

This selects years like `1950, 1960, 1970, 1980, 1990` and months `1, 4, 7, 10`.

The full build is checkpointed. Completed stages are recorded in:

```text
data/build_checkpoint.json
```

If the command stops, run the same command again and it resumes from the next unfinished stage. To intentionally rebuild every stage, use:

```bash
python build_all.py --api-key YOUR_NYT_KEY --reset-checkpoints
```

NYT rate limits are retried automatically. On HTTP `429`, the downloader waits with exponential backoff starting at 20 seconds for up to 10 retries, then fails. Tune it with:

```bash
python build_all.py --api-key YOUR_NYT_KEY --max-429-retries 10 --initial-backoff-seconds 20
```

Parquet size controls:

```bash
python build_all.py --api-key YOUR_NYT_KEY --max-phrases-per-article 300 --context-radius 40
```

The pipeline writes Parquet with `zstd` compression by default. Lower `--max-phrases-per-article` or `--context-radius` to reduce phrase partition size.

Manual stage-by-stage workflow:

```bash
python ingest.py --raw-dir data/raw
python aggregate.py
python build_features.py
python build_embeddings.py
python validate_duckdb.py
python build_dataset.py
python train.py
python predict.py "streaming platform"
```

What each command does:

- `ingest.py`: reads NYT Archive JSON files and replaces year/month Parquet partitions for articles and phrases.
- `aggregate.py`: uses DuckDB over phrase Parquet to rebuild timelines and phrase statistics.
- `build_features.py`: rebuilds feature Parquet from timelines.
- `build_embeddings.py`: rebuilds the deterministic embedding manifest Parquet.
- `validate_duckdb.py`: validates DuckDB analytical queries over Parquet files.
- `build_dataset.py`: exports phrase rows with decade probability targets.
- `train.py`: trains a lightweight phrase-to-decade probability model.
- `predict.py`: outputs JSON decade probabilities for a phrase.
- `validate_input_sets.py`: validates sample and evaluation JSONL files.
- `evaluate_predictions.py`: generates versioned evaluation metrics and confusion matrices.
- `compare_evaluation_runs.py`: compares versioned evaluation runs.
- `analyze_corpus_distribution.py`: summarizes temporal corpus distribution from Parquet.
- `inspect_phrase_target.py`: inspects the timeline and target distribution for one phrase.
- `train_tfidf.py`: trains an experimental TF-IDF baseline model.
- `build_real_embeddings.py`: optionally generates sentence embeddings for a limited subset.

If no trained model exists yet, `predict.py` still returns a valid fallback distribution. After training, predictions use the learned model saved at `data/models/decade_model.json`.

Current comparison artifacts:

```text
evaluation_results/profile-baseline-current/
evaluation_results/tfidf-5000-current/
evaluation_results/profile-balanced-current/
evaluation_results/model_comparison.md
sample_inputs/results/predictions.md
sample_inputs/results/predictions_balanced.md
```

## Project Structure

```text
data/
  raw/
  normalized/
  parquet/
  embeddings/
  datasets/
  models/

iesbhistorico/
  downloader/
  normalization/
  extraction/
  storage/
  embeddings/
  analytics/
  features/
  training/
  inference/
  cli/

requirements.txt
README.md
```

## Requirements

- Python 3.12+
- DuckDB
- Parquet
- pandas
- numpy
- pyarrow
- scikit-learn
- joblib
- sentence-transformers
- spaCy

## Engineering Rules

- Every step must be resumable.
- Skip already downloaded archive files.
- Deduplicate articles, phrases, and embeddings.
- Use immutable partitioned Parquet as processed truth.
- Use full partition replacement, not append-based inserts.
- Process data in batches.
- Do not load the full corpus into memory.
- Keep ingestion, aggregation, training, and inference separate.
- Use type hints, argparse CLIs, and structured logging.
- Avoid hardcoded local paths.

## Anti-Goals

Do not:

- Predict only a single year.
- Train only on embeddings.
- Ignore frequency normalization.
- Ignore OCR and text noise.
- Build a notebook-only workflow.
- Require full reprocessing for small changes.

## Definition of Done

The project is done when a user can run:

```bash
python predict.py "some phrase"
```

and receive a JSON object containing the probability that the phrase belongs to each decade.
