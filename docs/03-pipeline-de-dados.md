# Pipeline de dados

## Fonte de dados atual

A fonte implementada atualmente e a New York Times Archive API. O downloader monta URLs no formato `https://api.nytimes.com/svc/archive/v1/{year}/{month}.json?api-key=...` e grava arquivos JSON mensais em `data/raw/{ano}/{mes}.json`.

## Ingestao e pre-processamento

A ingestao le `response.docs`, extrai metadados e campos textuais como titulo, resumo, snippet, paragrafo inicial e palavras-chave. Os textos passam por normalizacao Unicode, limpeza de espacos, tratamento de pontuacao repetida e filtros de frase. Cada artigo e frase recebe identificadores deterministicos por hash.

## Extracao de frases

O extrator atual usa n-gramas de 1 a 4 tokens. Ele nao usa, neste estado, entidades nomeadas, noun chunks ou parser linguistico. Essa escolha e coerente com o modelo profile, que aprende perfis temporais por palavras, bigramas e n-gramas de caracteres.

## Persistencia

Os artefatos processados sao gravados em Parquet:

- `data/parquet/articles/`;
- `data/parquet/phrases/`;
- `data/parquet/phrase_timelines/`;
- `data/parquet/phrase_statistics/`;
- `data/parquet/features/`;
- `data/parquet/embeddings/`.

Artigos e frases sao particionados por ano e mes. Datasets derivados sao recomputaveis e gravados por substituicao completa com diretorio temporario.

## Agregacao temporal

A agregacao usa DuckDB sobre Parquet para calcular frequencia bruta por frase e ano, frequencia normalizada por volume anual, primeira e ultima ocorrencia, ano de pico, decada de pico, contagem total e entropia temporal.

## Features e target

`build_features.py` transforma timelines em linhas com `target_probability` por decada. `build_dataset.py` agrupa essas linhas por frase e gera `data/datasets/training_dataset.jsonl`.

O dataset local validado possui 12.323.734 linhas de treinamento.

## Treinamento

Ha tres caminhos de modelo:

- profile baseline: `python train.py`;
- profile balanceado: `python train.py --balance-decades --model data/models/decade_model_balanced.json`;
- TF-IDF experimental: `python train_tfidf.py --max-rows 5000`.

O modelo profile baseline permanece em `data/models/decade_model.json`. O modelo balanceado e mantido separado para preservar comparacao antes/depois.

## Inferencia

O CLI principal continua sendo:

```bash
python predict.py "streaming platform"
```

Tambem e possivel selecionar o modelo TF-IDF experimental:

```bash
python predict.py "moon landing" --model-type tfidf
```

## Avaliacao e versionamento

A avaliacao formal fica separada do treinamento:

```bash
python validate_input_sets.py
python evaluate_predictions.py --run-id profile-baseline-with-f1
python evaluate_predictions.py --model data/models/decade_model_balanced.json --run-id profile-balanced-with-f1
python evaluate_predictions.py --model-type tfidf --run-id tfidf-5000-with-f1
python compare_evaluation_runs.py profile-baseline-with-f1 tfidf-5000-with-f1 profile-balanced-with-f1
```

Cada rodada de avaliacao grava:

- `metrics.md`;
- `metrics.json`;
- `predictions.jsonl`;
- `confusion_matrix.csv`;
- `classification_report.md`;
- `classification_report.json`;
- `classification_report.csv`.

As rodadas atuais sao:

- `evaluation_results/profile-baseline-current`;
- `evaluation_results/tfidf-5000-current`;
- `evaluation_results/profile-balanced-current`.

As rodadas complementares com precision, recall e F1-score sao:

- `evaluation_results/profile-baseline-with-f1`;
- `evaluation_results/tfidf-5000-with-f1`;
- `evaluation_results/profile-balanced-with-f1`.

O calculo em `iesbhistorico/inference/metrics.py` mantem acuracia top-1, acuracia top-3 e erro medio entre decadas, e adiciona metricas multiclasse por decada, macro, weighted e micro. Classes sem predicao ou sem exemplos reais recebem divisao por zero tratada como 0.

## Diagnosticos

Os comandos de diagnostico sao:

```bash
python analyze_corpus_distribution.py
python inspect_phrase_target.py "moon landing" --output docs/generated/target_moon_landing.md
```

Eles geram resumo temporal do corpus e auditoria de targets por frase.

## Mudancas necessarias para Hemeroteca

Para a Hemeroteca Digital Brasileira, o pipeline precisara incluir coleta de PDFs ou imagens, OCR, correcao textual, segmentacao de artigos, metadados temporais confiaveis e avaliacao do impacto de erros de digitalizacao.
