# Arquitetura

## Tipo de arquitetura observada

A arquitetura observada e um pipeline modular em Python, com etapas sequenciais e artefatos intermediarios persistidos em disco. O orquestrador principal e `iesbhistorico/cli/build_all.py`, que executa download, ingestao, agregacao, construcao de features, manifest de embeddings, validacao DuckDB, dataset JSONL e treinamento do modelo (evidencias: `iesbhistorico/cli/build_all.py:55`, `iesbhistorico/cli/build_all.py:79`, `iesbhistorico/cli/build_all.py:98`, `iesbhistorico/cli/build_all.py:100`).

## Diagrama textual

```text
NYT Archive API
  -> data/raw/{ano}/{mes}.json
  -> ingestao e limpeza
  -> data/parquet/articles/year=YYYY/month=MM/part.parquet
  -> data/parquet/phrases/year=YYYY/month=MM/part.parquet
  -> agregacao DuckDB
  -> data/parquet/phrase_timelines/part.parquet
  -> data/parquet/phrase_statistics/part.parquet
  -> features por frase e decada
  -> data/parquet/features/part.parquet
  -> data/parquet/embeddings/part.parquet
  -> data/datasets/training_dataset.jsonl
  -> data/models/decade_model.json
  -> evaluation_inputs/decade_labeled_phrases.jsonl
  -> evaluation_results/RUN_ID/
  -> predict.py "frase"
```

## Componentes

- `iesbhistorico/downloader/nyt_downloader.py`: baixa arquivos JSON mensais da NYT Archive API, evita repetir arquivos existentes e aplica retentativas com backoff para HTTP 429 (evidencias: `iesbhistorico/downloader/nyt_downloader.py:18`, `iesbhistorico/downloader/nyt_downloader.py:25`, `iesbhistorico/downloader/nyt_downloader.py:34`, `iesbhistorico/downloader/nyt_downloader.py:49`).
- `iesbhistorico/cli/ingest_raw.py`: le JSON bruto, extrai campos jornalisticos, normaliza texto, gera IDs deterministico e grava particoes Parquet de artigos e frases (evidencias: `iesbhistorico/cli/ingest_raw.py:21`, `iesbhistorico/cli/ingest_raw.py:33`, `iesbhistorico/cli/ingest_raw.py:58`, `iesbhistorico/cli/ingest_raw.py:80`).
- `iesbhistorico/normalization/article_cleaner.py`: normaliza Unicode, espacos, pontuacao e limpa frases com filtros de tamanho, proporcao alfabetica, repeticao e stopwords (evidencias: `iesbhistorico/normalization/article_cleaner.py:36`, `iesbhistorico/normalization/article_cleaner.py:46`).
- `iesbhistorico/extraction/phrase_extractor.py`: extrai n-gramas de 1 a 4 tokens, ignora n-gramas iniciados ou finalizados por stopwords e armazena contexto textual (evidencias: `iesbhistorico/extraction/phrase_extractor.py:16`, `iesbhistorico/extraction/phrase_extractor.py:26`, `iesbhistorico/extraction/phrase_extractor.py:45`).
- `iesbhistorico/storage/partitioned_parquet.py`: centraliza hashing deterministico, particionamento, escrita temporaria seguida de substituicao e leitura de datasets Parquet (evidencias: `iesbhistorico/storage/partitioned_parquet.py:15`, `iesbhistorico/storage/partitioned_parquet.py:31`, `iesbhistorico/storage/partitioned_parquet.py:47`, `iesbhistorico/storage/partitioned_parquet.py:64`).
- `iesbhistorico/analytics/phrase_timelines.py`: usa DuckDB em memoria para recomputar frequencias normalizadas por ano, estatisticas por frase, ano de pico, decada de pico e entropia temporal (evidencias: `iesbhistorico/analytics/phrase_timelines.py:16`, `iesbhistorico/analytics/phrase_timelines.py:19`, `iesbhistorico/analytics/phrase_timelines.py:27`, `iesbhistorico/analytics/phrase_timelines.py:49`).
- `iesbhistorico/features/build_features.py`: transforma timelines e estatisticas em linhas de features com probabilidade-alvo por decada (evidencias: `iesbhistorico/features/build_features.py:16`, `iesbhistorico/features/build_features.py:20`, `iesbhistorico/features/build_features.py:54`).
- `iesbhistorico/features/build_dataset.py`: agrupa linhas por frase e gera JSONL de treinamento (evidencias: `iesbhistorico/features/build_dataset.py:17`, `iesbhistorico/features/build_dataset.py:32`, `iesbhistorico/features/build_dataset.py:42`).
- `iesbhistorico/modeling/decade_model.py`: implementa modelo probabilistico baseado em perfis de palavras, bigramas e n-gramas de caracteres (evidencias: `iesbhistorico/modeling/decade_model.py:17`, `iesbhistorico/modeling/decade_model.py:30`, `iesbhistorico/modeling/decade_model.py:59`, `iesbhistorico/modeling/decade_model.py:112`).
- `iesbhistorico/inference/predict.py`: carrega o modelo salvo ou fallback, retorna distribuicao por decada, decada principal e confianca (evidencias: `iesbhistorico/inference/predict.py:12`, `iesbhistorico/inference/predict.py:17`, `iesbhistorico/inference/predict.py:24`).
- `iesbhistorico/inference/evaluate.py`: executa avaliacao formal versionada e gera metricas, predicoes, matriz de confusao e relatorios de classificacao por decada.
- `iesbhistorico/inference/metrics.py`: calcula acuracia top-1, top-3, erro medio entre decadas, metricas segmentadas, precision, recall e F1-score.
- `iesbhistorico/modeling/tfidf_model.py`: implementa modelo TF-IDF experimental com `scikit-learn`.

## Fluxo de execucao

O fluxo recomendado e `python build_all.py`, que chama `run_full_build`. Cada etapa e identificada por um `step_id`, executada em ordem e registrada por checkpoint quando concluida (evidencias: `iesbhistorico/cli/build_all.py:55`, `iesbhistorico/cli/build_all.py:74`, `iesbhistorico/cli/build_all.py:79`, `iesbhistorico/cli/build_all.py:118`).

Os scripts da raiz sao wrappers finos que chamam o `main` dos modulos internos. Isso simplifica a execucao por linha de comando sem duplicar logica (evidencia: arquivos `build_all.py`, `ingest.py`, `aggregate.py`, `predict.py` na raiz).

## Justificativas arquiteturais

A separacao entre coleta, ingestao, agregacao, features, treinamento e inferencia e adequada para um prototipo de TCC porque torna cada etapa verificavel isoladamente e permite substituir a fonte de dados futuramente. Essa decisao tambem reduz o risco da migracao para Hemeroteca, pois a camada de coleta/OCR podera ser adaptada antes da etapa de normalizacao e extracao de frases.

O uso de Parquet particionado e apropriado para dados jornalisticos historicos, pois organiza o corpus por tempo e favorece recomputacao de artefatos derivados. A limitacao e que a substituicao completa de datasets recomputados pode ser custosa para volumes maiores.

A avaliacao formal foi separada do conjunto demonstrativo. Essa decisao preserva comparabilidade entre rodadas e permite apresentar resultados antes/depois sem sobrescrever o baseline original.

O uso de DuckDB como mecanismo analitico sobre Parquet evita manter um banco processado separado. A consequencia positiva e a reducao de estado persistente duplicado; a limitacao e que consultas muito grandes ainda dependem dos recursos locais.
