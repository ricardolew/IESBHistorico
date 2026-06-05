# Especificacoes tecnicas

## Linguagem e organizacao

O projeto e implementado em Python. O pacote principal e `iesbhistorico/`, e os scripts de execucao ficam na raiz como wrappers ou comandos operacionais.

## Dependencias

Dependencias declaradas em `requirements.txt`:

- `numpy`;
- `pandas`;
- `pyarrow`;
- `duckdb`;
- `scikit-learn`;
- `joblib`;
- `sentence-transformers`;
- `spacy`.

Uso atual:

- `pandas`, `pyarrow` e `duckdb`: pipeline Parquet e consultas analiticas;
- `scikit-learn`: modelo TF-IDF experimental;
- `joblib`: serializacao do modelo TF-IDF experimental;
- `sentence-transformers`: comando opcional `build_real_embeddings.py`;
- `spacy`: dependencia declarada, ainda nao usada no extrator atual.

## Entradas principais

- JSON da NYT em `data/raw/{ano}/{mes}.json`;
- frase em `python predict.py "frase"`;
- amostra demonstrativa em `sample_inputs/phrases.jsonl`;
- avaliacao formal em `evaluation_inputs/decade_labeled_phrases.jsonl`.

## Saidas principais

- Parquet processado em `data/parquet/`;
- dataset de treinamento em `data/datasets/training_dataset.jsonl`;
- modelos em `data/models/`;
- resultados demonstrativos em `sample_inputs/results/`;
- avaliacoes versionadas em `evaluation_results/`;
- diagnosticos em `docs/generated/` e `data/reports/`.

## Comandos essenciais

Testes:

```bash
python -m unittest discover tests
```

Build completo:

```bash
python build_all.py --api-key SUA_CHAVE_NYT --start-year 1950 --end-year 1999
```

Predicao:

```bash
python predict.py "streaming platform"
```

Treino profile balanceado:

```bash
python train.py --balance-decades --model data/models/decade_model_balanced.json
```

TF-IDF experimental:

```bash
python train_tfidf.py --max-rows 5000
python evaluate_predictions.py --model-type tfidf --run-id tfidf-5000-current
```

Amostra demonstrativa:

```bash
python run_input_sample.py
python run_input_sample.py --model data/models/decade_model_balanced.json --markdown-output sample_inputs/results/predictions_balanced.md --jsonl-output sample_inputs/results/predictions_balanced.jsonl
```

Avaliacao formal:

```bash
python validate_input_sets.py
python evaluate_predictions.py --run-id profile-baseline-with-f1
python evaluate_predictions.py --model data/models/decade_model_balanced.json --run-id profile-balanced-with-f1
python evaluate_predictions.py --model-type tfidf --run-id tfidf-5000-with-f1
python compare_evaluation_runs.py profile-baseline-with-f1 tfidf-5000-with-f1 profile-balanced-with-f1
```

As rodadas de avaliacao exportam `metrics.md`, `metrics.json`, `predictions.jsonl`, `confusion_matrix.csv`, `classification_report.md`, `classification_report.json` e `classification_report.csv`. Os arquivos de classificacao registram suporte, precision, recall, F1-score, acertos, erros e principais confusoes por decada.

Diagnosticos:

```bash
python validate_duckdb.py
python analyze_corpus_distribution.py
python inspect_phrase_target.py "moon landing" --output docs/generated/target_moon_landing.md
```

Embeddings opcionais:

```bash
python build_real_embeddings.py --max-rows 1000
```

## Artefatos locais validados

Estado validado nesta revisao:

| Artefato | Estado |
| --- | --- |
| `data/parquet/articles` | 458.357 linhas |
| `data/parquet/phrases` | 44.772.151 linhas |
| `data/parquet/phrase_timelines` | 26.433.784 linhas |
| `data/parquet/phrase_statistics` | 23.655.363 linhas |
| `data/parquet/features` | 15.102.155 linhas |
| `data/parquet/embeddings` | 23.655.363 linhas |
| `data/datasets/training_dataset.jsonl` | 12.323.734 linhas |
| `sample_inputs/phrases.jsonl` | 168 entradas |
| `evaluation_inputs/decade_labeled_phrases.jsonl` | 24 entradas |

## Variaveis de ambiente

O pipeline atual nao depende de variaveis de ambiente obrigatorias. A chave da NYT e passada por `--api-key`.
