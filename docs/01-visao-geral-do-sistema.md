# Visao geral do sistema

## Objetivo

O IESBHistorico e um prototipo de classificacao temporal de frases jornalisticas. A entrada e uma frase; a saida esperada e uma distribuicao de probabilidade por decada, acompanhada da decada mais provavel e de uma confianca associada. O sistema nao tem como objetivo predizer apenas um ano ou retornar apenas uma classe seca.

## Escopo atual

O prototipo atual usa a New York Times Archive API como base provisoria em ingles. Essa decisao permite validar arquitetura, pipeline de dados, persistencia, treinamento, inferencia, avaliacao e comparacao de modelos antes da etapa futura com a Hemeroteca Digital Brasileira.

O repositorio contem:

- pipeline de coleta, ingestao, agregacao, features, dataset, treinamento e inferencia;
- armazenamento processado em Parquet particionado;
- modelo profile baseline em `data/models/decade_model.json`;
- modelo profile balanceado em `data/models/decade_model_balanced.json`;
- modelo TF-IDF experimental em `data/models/decade_model_tfidf.joblib`;
- amostra demonstrativa em `sample_inputs/`;
- conjunto formal de avaliacao em `evaluation_inputs/`;
- rodadas versionadas em `evaluation_results/`;
- relatorios classicos de classificacao por decada em `classification_report.md`, `classification_report.json` e `classification_report.csv`;
- diagnosticos gerados em `docs/generated/` e `data/reports/`.

## Escopo futuro com Hemeroteca

A proposta academica do TCC preve jornais historicos brasileiros da Hemeroteca Digital Brasileira. Essa etapa ainda nao esta implementada no codigo atual. A migracao futura exigira coleta de PDFs ou imagens, OCR, segmentacao de artigos, normalizacao de portugues historico, tratamento de ruido de digitalizacao e avaliacao do impacto dos erros de OCR.

## Estado atual dos resultados

A avaliacao formal atual usa `evaluation_inputs/decade_labeled_phrases.jsonl`, com 24 frases direcionadas, duas por decada de `1900s` a `2010s`.

Comparacao versionada atual:

| Rodada | Top-1 | Top-3 | Erro medio entre decadas |
| --- | ---: | ---: | ---: |
| `profile-baseline-current` | 0.2500 | 0.4167 | 3.2500 |
| `tfidf-5000-current` | 0.2500 | 0.3333 | 4.2500 |
| `profile-balanced-current` | 0.2500 | 0.5000 | 1.9583 |

O balanceamento por decada ainda nao aumentou a acuracia top-1, mas melhorou a recuperacao top-3 e reduziu o erro temporal medio. Portanto, ele deve ser apresentado como melhoria parcial e nao como solucao definitiva.

Rodadas complementares com precision, recall e F1-score foram geradas sem substituir as anteriores:

| Rodada | Top-1 | Top-3 | Erro medio | Macro F1 | Weighted F1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `profile-baseline-with-f1` | 0.2500 | 0.4167 | 3.2500 | 0.2009 | 0.2009 |
| `tfidf-5000-with-f1` | 0.2500 | 0.3333 | 4.2500 | 0.2139 | 0.2139 |
| `profile-balanced-with-f1` | 0.2500 | 0.5000 | 1.9583 | 0.2130 | 0.2130 |

Esses valores estao registrados em `evaluation_results/model_comparison.md` e nos arquivos `metrics.json` de cada rodada `with-f1`. Como o conjunto formal tem duas frases por decada, macro F1 e weighted F1 ficam proximos ou iguais nas rodadas atuais.

## Limites conhecidos

- Nao ha integracao com a Hemeroteca Digital Brasileira.
- Nao ha OCR implementado no pipeline atual.
- O conjunto de avaliacao formal ainda e pequeno, com 24 frases direcionadas.
- Metricas por classe, incluindo precision, recall e F1-score, sao instaveis com suporte baixo.
- Precision, recall e F1-score complementam, mas nao substituem, a analise qualitativa dos erros e da matriz de confusao.
- O TF-IDF experimental foi treinado em um recorte de 5.000 linhas, portanto nao substitui o baseline.
- O manifesto de embeddings existe; a geracao real de embeddings e opcional, via `build_real_embeddings.py`, e nao foi usada como modelo principal.
- O corpus atual esta em ingles e nao deve ser extrapolado automaticamente para jornais brasileiros historicos.
