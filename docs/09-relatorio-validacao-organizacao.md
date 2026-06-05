# Relatorio de validacao e organizacao

## Objetivo

Este relatorio consolida a revisao final da documentacao, a validacao da integridade do sistema e a organizacao dos artefatos usados para apresentar as diferencas entre os testes antes e depois das melhorias.

## Estado dos dados processados

A validacao DuckDB confirmou leitura dos datasets Parquet:

| Dataset | Linhas |
| --- | ---: |
| `articles` | 458.357 |
| `phrases` | 44.772.151 |
| `phrase_timelines` | 26.433.784 |
| `phrase_statistics` | 23.655.363 |
| `features` | 15.102.155 |
| `embeddings` | 23.655.363 |

O dataset de treinamento `data/datasets/training_dataset.jsonl` existe e possui 12.323.734 linhas.

## Modelos disponiveis

| Modelo | Arquivo | Uso |
| --- | --- | --- |
| Profile baseline | `data/models/decade_model.json` | Referencia original |
| Profile balanceado | `data/models/decade_model_balanced.json` | Retreino com pesos por decada |
| TF-IDF experimental | `data/models/decade_model_tfidf.joblib` | Baseline supervisionado experimental |

O modelo baseline foi preservado. O modelo balanceado foi salvo separadamente para comparacao antes/depois.

## Inputs e avaliacoes

| Artefato | Estado |
| --- | --- |
| `sample_inputs/phrases.jsonl` | 168 entradas, valido, sem IDs duplicados |
| `sample_inputs/results/predictions.jsonl` | 168 previsoes baseline |
| `sample_inputs/results/predictions_balanced.jsonl` | 168 previsoes balanceadas |
| `evaluation_inputs/decade_labeled_phrases.jsonl` | 24 entradas, duas por decada |
| `evaluation_results/profile-baseline-current` | Rodada baseline |
| `evaluation_results/tfidf-5000-current` | Rodada TF-IDF experimental |
| `evaluation_results/profile-balanced-current` | Rodada profile balanceada |
| `evaluation_results/profile-baseline-with-f1` | Rodada baseline com precision, recall e F1-score |
| `evaluation_results/tfidf-5000-with-f1` | Rodada TF-IDF com precision, recall e F1-score |
| `evaluation_results/profile-balanced-with-f1` | Rodada profile balanceada com precision, recall e F1-score |

## Comparacao antes/depois

| Rodada | Top-1 | Top-3 | Erro medio entre decadas |
| --- | ---: | ---: | ---: |
| `profile-baseline-current` | 0.2500 | 0.4167 | 3.2500 |
| `tfidf-5000-current` | 0.2500 | 0.3333 | 4.2500 |
| `profile-balanced-current` | 0.2500 | 0.5000 | 1.9583 |

Conclusao: o modelo balanceado nao aumentou a acuracia top-1, mas melhorou a recuperacao top-3 e reduziu a distancia temporal media dos erros. Essa e a diferenca principal a ser apresentada.

## Comparacao com F1-score

| Rodada | Top-1 | Top-3 | Erro medio | Macro F1 | Weighted F1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `profile-baseline-with-f1` | 0.2500 | 0.4167 | 3.2500 | 0.2009 | 0.2009 |
| `tfidf-5000-with-f1` | 0.2500 | 0.3333 | 4.2500 | 0.2139 | 0.2139 |
| `profile-balanced-with-f1` | 0.2500 | 0.5000 | 1.9583 | 0.2130 | 0.2130 |

Evidencias: `evaluation_results/model_comparison.md`, `evaluation_results/profile-baseline-with-f1/metrics.json`, `evaluation_results/tfidf-5000-with-f1/metrics.json` e `evaluation_results/profile-balanced-with-f1/metrics.json`.

## Organizacao atual

Arquivos de entrada:

- `sample_inputs/`: demonstracao com entradas variadas;
- `evaluation_inputs/`: avaliacao formal rotulada.

Arquivos de saida:

- `sample_inputs/results/`: previsoes demonstrativas baseline e balanceadas;
- `evaluation_results/`: metricas versionadas, matriz de confusao e relatorios de classificacao por decada;
- `docs/generated/`: diagnosticos gerados;
- `data/reports/`: dados tabulares de diagnostico.

Documentacao revisada:

- `README.md`;
- `docs/00-indice.md`;
- `docs/01-visao-geral-do-sistema.md`;
- `docs/03-pipeline-de-dados.md`;
- `docs/04-especificacoes-tecnicas.md`;
- `docs/05-decisoes-arquiteturais.md`;
- `docs/06-textos-para-o-artigo.md`;
- `docs/07-analise-da-amostra-de-predictions.md`;
- `docs/08-plano-de-implementacao-melhoria-precisao.md`.

## Comandos de validacao executados

```bash
python validate_duckdb.py
python validate_input_sets.py
python evaluate_predictions.py --run-id profile-baseline-with-f1
python evaluate_predictions.py --model data/models/decade_model_balanced.json --run-id profile-balanced-with-f1
python evaluate_predictions.py --model-type tfidf --run-id tfidf-5000-with-f1
python compare_evaluation_runs.py profile-baseline-with-f1 tfidf-5000-with-f1 profile-balanced-with-f1
python -m unittest discover tests
```

Resultados:

- Parquet validado via DuckDB;
- inputs validados sem erros e sem IDs duplicados;
- novas rodadas de avaliacao geradas sem substituir as rodadas `current`;
- `evaluation_results/model_comparison.md` atualizado para comparar as rodadas `with-f1`;
- testes automatizados passaram com 15 testes;
- nao foram encontrados arquivos temporarios `.tmp` remanescentes nos diretorios principais revisados.

Aspectos cobertos pelos testes automatizados:

- classificacao perfeita;
- classificacao parcialmente incorreta;
- classe sem predicao;
- classe prevista sem exemplo real;
- conjunto vazio;
- calculo de macro F1;
- calculo de weighted F1;
- compatibilidade com acuracia top-1, acuracia top-3 e erro medio entre decadas;
- validacao estrutural basica de inputs;
- smoke tests do pipeline e do modelo TF-IDF.

Lacunas de teste remanescentes:

- nao ha teste especifico para empate no ranking top-k;
- nao ha teste dedicado para distribuicao de probabilidades incompleta alem dos cenarios minimos de predicao;
- nao ha avaliacao automatizada com corpus da Hemeroteca Digital Brasileira, pois essa etapa ainda nao esta implementada;
- nao ha teste de impacto de OCR, pois OCR ainda e etapa futura.

## Limitacoes das metricas

- O conjunto formal ainda e pequeno, com 24 entradas.
- Cada decada tem apenas duas frases, portanto precision, recall e F1-score por classe podem ser instaveis.
- Precision, recall e F1-score nao substituem a analise qualitativa da matriz de confusao e dos erros.
- Os resultados em ingles com NYT nao devem ser extrapolados para a Hemeroteca Digital Brasileira.
- A etapa com Hemeroteca precisara de nova avaliacao apos OCR, segmentacao e normalizacao de portugues historico.

## Recomendacao de apresentacao

Para apresentar as melhorias, usar:

1. `evaluation_results/model_comparison.md` para a tabela de comparacao.
2. `sample_inputs/results/predictions.md` como resultado demonstrativo baseline.
3. `sample_inputs/results/predictions_balanced.md` como resultado demonstrativo apos balanceamento.
4. `docs/07-analise-da-amostra-de-predictions.md` para interpretacao tecnica.
