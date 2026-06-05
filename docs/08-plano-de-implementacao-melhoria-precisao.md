# Plano de implementacao para melhoria de desempenho

## Status da implementacao

As primeiras etapas deste plano foram implementadas no repositorio:

- validacao estrutural de inputs com `validate_input_sets.py`;
- conjunto de avaliacao separado em `evaluation_inputs/decade_labeled_phrases.jsonl`;
- avaliacao formal versionada com `evaluate_predictions.py`;
- metricas top-1, top-3, erro medio entre decadas, matriz de confusao, precision, recall, F1-score e metricas por tamanho de input;
- classificacao de tamanho das entradas em `iesbhistorico/inference/input_size.py`;
- relatorio de distribuicao temporal do corpus com `analyze_corpus_distribution.py`;
- inspecao de target por frase com `inspect_phrase_target.py`;
- opcao de treinamento balanceado por decada em `train.py --balance-decades`;
- modelo comparativo TF-IDF experimental com `train_tfidf.py`;
- geracao opcional de embeddings reais para subconjuntos controlados com `build_real_embeddings.py`;
- comparacao de rodadas com `compare_evaluation_runs.py`.

Rodadas geradas:

- `evaluation_results/profile-baseline-current`;
- `evaluation_results/tfidf-5000-current`;
- `evaluation_results/profile-balanced-current`;
- `evaluation_results/profile-baseline-with-f1`;
- `evaluation_results/tfidf-5000-with-f1`;
- `evaluation_results/profile-balanced-with-f1`;
- `evaluation_results/model_comparison.md`.

Na comparacao atual, o modelo `profile-balanced-current` manteve a mesma acuracia top-1 do baseline, `0,2500`, mas melhorou a acuracia top-3 de `0,4167` para `0,5000` e reduziu o erro medio entre decadas de `3,2500` para `1,9583`. O modelo `tfidf-5000-current` tambem manteve top-1 em `0,2500`, mas apresentou top-3 menor, `0,3333`, e erro medio maior, `4,2500`. Portanto, o balanceamento por decada e a melhoria mais promissora neste ciclo, enquanto o TF-IDF experimental ainda nao substitui o baseline atual.

Nas rodadas `with-f1`, o comparativo adicionou macro F1 e weighted F1: `profile-baseline-with-f1` registrou 0,2009 em ambas, `tfidf-5000-with-f1` registrou 0,2139 em ambas, e `profile-balanced-with-f1` registrou 0,2130 em ambas. Esses valores estao em `evaluation_results/model_comparison.md` e nos arquivos `metrics.json` das rodadas.

## Escopo

Este plano detalha a implementacao das tratativas de melhoria de desempenho descritas em `docs/07-analise-da-amostra-de-predictions.md`, com excecao da preparacao para adaptacao ao portugues historico. O objetivo e evoluir o prototipo atual para que ele tenha avaliacao mais confiavel, melhor balanceamento temporal e representacoes textuais mais robustas. Neste documento, "precision" deve ser lida apenas como a metrica classica de classificacao; acertos diretos usam o termo acuracia top-1.

## Objetivos tecnicos

- Reduzir concentracao excessiva de previsoes em poucas decadas.
- Medir desempenho com metricas formais, nao apenas por inspecao manual.
- Separar dados de avaliacao dos dados usados para treinamento.
- Aumentar a amostra direcionada por decada.
- Medir desempenho por tamanho de input.
- Auditar a construcao dos targets temporais.
- Comparar o modelo atual com alternativas supervisionadas.

## Fase 1 - Diagnostico e balanceamento do corpus

### 1.1 Criar relatorio de distribuicao temporal do corpus

**Tratativa relacionada:** balancear o corpus por decada.

**Implementacao proposta:**

- Criar um script `analyze_corpus_distribution.py`.
- Ler `data/parquet/articles`, `data/parquet/phrases`, `data/parquet/phrase_timelines`, `data/parquet/features` com DuckDB.
- Gerar contagens por ano e decada:
  - artigos por decada;
  - linhas de frases por decada;
  - soma de frequencias por decada;
  - quantidade de frases unicas por decada;
  - distribuicao de `target_probability` por decada.
- Salvar relatorio em `docs/generated/corpus_distribution.md`.
- Salvar dados tabulares em `data/reports/corpus_distribution.json`.

**Arquivos provaveis:**

- novo `analyze_corpus_distribution.py`;
- novo modulo opcional `iesbhistorico/analytics/corpus_distribution.py`;
- novo diretorio `data/reports/`;
- novo diretorio `docs/generated/`.

**Criterios de aceite:**

- O comando `python analyze_corpus_distribution.py` executa sem retreinar o modelo.
- O relatorio mostra quais decadas dominam o corpus.
- O relatorio identifica decadas sem dados ou sub-representadas.

### 1.2 Implementar pesos por decada no treinamento

**Tratativa relacionada:** balancear o corpus por decada.

**Implementacao proposta:**

- Adicionar uma rotina para calcular pesos inversamente proporcionais ao volume de cada decada no dataset de treinamento.
- Permitir ativar/desativar balanceamento por argumento:

```bash
python train.py --balance-decades
```

- Alterar `DecadeProfileModel.fit` para aceitar pesos por decada ou pesos por linha.
- Registrar no arquivo do modelo se o treinamento usou balanceamento.

**Arquivos provaveis:**

- `iesbhistorico/training/train_decade_model.py`;
- `iesbhistorico/modeling/decade_model.py`;
- `train.py`;
- testes em `tests/test_smoke_pipeline.py` ou novo `tests/test_training_balance.py`.

**Criterios de aceite:**

- O treinamento atual continua funcionando sem `--balance-decades`.
- Com `--balance-decades`, o modelo salvo registra metadado de balanceamento.
- A distribuicao de previsoes da amostra passa a ser comparavel entre modelo balanceado e nao balanceado.

## Fase 2 - Conjunto de avaliacao separado

### 2.1 Separar inputs de demonstracao e inputs de avaliacao

**Tratativa relacionada:** criar um conjunto de avaliacao separado.

**Implementacao proposta:**

- Manter `sample_inputs/phrases.jsonl` como conjunto demonstrativo.
- Criar `evaluation_inputs/decade_labeled_phrases.jsonl` para avaliacao formal.
- Definir campos minimos:
  - `id`;
  - `phrase`;
  - `expected_decade`;
  - `source_note`;
  - `input_size_group`;
  - `review_status`.
- Garantir que entradas de avaliacao nao sejam usadas para treino.

**Arquivos provaveis:**

- novo `evaluation_inputs/README.md`;
- novo `evaluation_inputs/decade_labeled_phrases.jsonl`.

**Criterios de aceite:**

- Existe um arquivo de avaliacao separado dos exemplos de demonstracao.
- Cada registro possui decada esperada obrigatoria.
- O README explica que o conjunto e manualmente rotulado e nao deve alimentar o treinamento.

### 2.2 Criar runner de avaliacao formal

**Tratativa relacionada:** criar avaliacao separada e implementar metricas formais.

**Implementacao proposta:**

- Criar `evaluate_predictions.py`.
- Reutilizar a logica de batch prediction.
- Gerar relatorio em:
  - `evaluation_results/metrics.md`;
  - `evaluation_results/predictions.jsonl`;
  - `evaluation_results/confusion_matrix.csv`.
- Separar avaliacao do fluxo `run_input_sample.py`, que continua sendo demonstrativo.

**Arquivos provaveis:**

- novo `evaluate_predictions.py`;
- novo modulo `iesbhistorico/inference/evaluate.py`;
- novos testes em `tests/test_evaluation_metrics.py`.

**Criterios de aceite:**

- O comando `python evaluate_predictions.py` gera metricas sem alterar o modelo.
- O relatorio informa total de exemplos, acertos, erros e metricas por decada.
- O resultado inclui predicao, decada esperada e distribuicao completa.

## Fase 3 - Expansao dos exemplos direcionados

### 3.1 Ampliar exemplos por decada

**Tratativa relacionada:** aumentar a quantidade de exemplos direcionados por decada.

**Implementacao proposta:**

- Aumentar gradualmente `evaluation_inputs/decade_labeled_phrases.jsonl` para:
  - etapa inicial: 10 frases por decada;
  - etapa intermediaria: 30 frases por decada;
  - etapa desejavel: 50 ou mais frases por decada.
- Separar exemplos por tema:
  - politica;
  - tecnologia;
  - economia;
  - guerra;
  - cultura;
  - saude;
  - infraestrutura.
- Marcar frases ambiguas com `review_status: needs_review`.

**Arquivos provaveis:**

- `evaluation_inputs/decade_labeled_phrases.jsonl`;
- `evaluation_inputs/README.md`.

**Criterios de aceite:**

- Cada decada possui pelo menos 10 exemplos revisados.
- O arquivo nao possui IDs duplicados.
- O runner de avaliacao alerta quando alguma decada tem menos exemplos que o minimo definido.

### 3.2 Adicionar validacao estrutural dos inputs

**Tratativa relacionada:** aumentar qualidade dos exemplos direcionados.

**Implementacao proposta:**

- Criar script `validate_input_sets.py`.
- Validar:
  - JSONL bem formado;
  - IDs unicos;
  - decadas validas;
  - campos obrigatorios;
  - quantidade minima por decada;
  - distribuicao por tamanho de frase.

**Arquivos provaveis:**

- novo `validate_input_sets.py`;
- novo `iesbhistorico/inference/input_validation.py`;
- novo `tests/test_input_validation.py`.

**Criterios de aceite:**

- `python validate_input_sets.py` falha com codigo diferente de zero quando houver erro estrutural.
- O script informa claramente decadas sub-representadas.

## Fase 4 - Metricas por tamanho de input

### 4.1 Classificar tamanho das entradas

**Tratativa relacionada:** diferenciar frase curta de sentenca longa.

**Implementacao proposta:**

- Criar funcao compartilhada para classificar entradas:
  - `1_token`;
  - `2_4_tokens`;
  - `5_8_tokens`;
  - `9_15_tokens`;
  - `16_plus_tokens`;
  - `over_90_chars`.
- Adicionar essa classificacao aos resultados gerados por `run_input_sample.py` e `evaluate_predictions.py`.

**Arquivos provaveis:**

- `iesbhistorico/inference/batch_predict.py`;
- novo modulo `iesbhistorico/inference/input_size.py`;
- `sample_inputs/results/predictions.jsonl`;
- `evaluation_results/predictions.jsonl`.

**Criterios de aceite:**

- Cada predicao registra `input_size_group`.
- O Markdown de resultados mostra resumo por faixa de tamanho.

### 4.2 Calcular desempenho por tamanho

**Tratativa relacionada:** diferenciar frase curta de sentenca longa.

**Implementacao proposta:**

- No runner de avaliacao formal, calcular:
  - acuracia por faixa de tamanho;
  - confianca media por faixa;
  - quantidade de exemplos por faixa;
  - decadas mais previstas por faixa.

**Arquivos provaveis:**

- `iesbhistorico/inference/evaluate.py`;
- `evaluation_results/metrics.md`.

**Criterios de aceite:**

- O relatorio permite afirmar qual tamanho de entrada funciona melhor.
- O relatorio separa inputs longos de expressoes curtas.

## Fase 5 - Revisao da construcao dos targets

### 5.1 Auditar targets por frase

**Tratativa relacionada:** revisar a construcao dos targets.

**Implementacao proposta:**

- Criar `inspect_phrase_target.py`.
- Receber uma frase e exibir:
  - timeline anual;
  - frequencia bruta por ano;
  - frequencia normalizada por ano;
  - distribuicao-alvo por decada;
  - top decadas;
  - total de ocorrencias.

Exemplo:

```bash
python inspect_phrase_target.py "moon landing"
```

**Arquivos provaveis:**

- novo `inspect_phrase_target.py`;
- novo modulo `iesbhistorico/analytics/target_inspection.py`.

**Criterios de aceite:**

- O comando explica por que uma frase tem determinado target temporal.
- O relatorio ajuda a diagnosticar casos em que o modelo erra exemplos conhecidos.

### 5.2 Criar lista de frases ambiguas ou contaminadas

**Tratativa relacionada:** revisar targets.

**Implementacao proposta:**

- A partir da avaliacao formal, identificar frases com:
  - confianca alta e erro;
  - target espalhado por muitas decadas;
  - frequencia muito baixa;
  - termos genericos que aparecem em muitos contextos.
- Gerar `docs/generated/target_audit.md`.

**Arquivos provaveis:**

- `iesbhistorico/analytics/target_inspection.py`;
- `docs/generated/target_audit.md`.

**Criterios de aceite:**

- O relatorio lista frases problemáticas e possiveis causas.
- O relatorio separa erro de modelo de ambiguidade do proprio termo.

## Fase 6 - Melhor representacao textual e modelos comparativos

### 6.1 Implementar baseline supervisionado com TF-IDF

**Tratativa relacionada:** melhorar representacao textual.

**Implementacao proposta:**

- Criar um modelo comparativo usando `scikit-learn`.
- Representar frases com TF-IDF de palavras e caracteres.
- Treinar classificador probabilistico, como regressao logistica multinomial.
- Salvar modelo em caminho separado:

```text
data/models/decade_model_tfidf.joblib
```

- Criar CLI para selecionar modelo:

```bash
python predict.py "moon landing" --model-type profile
python predict.py "moon landing" --model-type tfidf
```

**Arquivos provaveis:**

- novo `iesbhistorico/modeling/tfidf_model.py`;
- `iesbhistorico/training/train_decade_model.py`;
- `iesbhistorico/inference/predict.py`;
- `requirements.txt`, se `joblib` precisar ser declarado explicitamente;
- novos testes em `tests/test_tfidf_model.py`.

**Criterios de aceite:**

- O modelo atual continua disponivel como baseline.
- O modelo TF-IDF gera probabilidades por decada que somam 1.
- O runner de avaliacao compara `profile` e `tfidf` no mesmo conjunto.

### 6.2 Implementar embeddings reais como experimento controlado

**Tratativa relacionada:** melhorar representacao textual.

**Implementacao proposta:**

- Evoluir `iesbhistorico/embeddings/embedding_cache.py` de manifesto para geracao opcional de vetores.
- Comecar com modo experimental e amostra limitada para evitar custo excessivo.
- Salvar embeddings em Parquet ou arquivo binario controlado.
- Comparar desempenho com:
  - modelo atual;
  - TF-IDF;
  - embeddings + classificador simples.

**Arquivos provaveis:**

- `iesbhistorico/embeddings/embedding_cache.py`;
- novo `iesbhistorico/modeling/embedding_model.py`;
- novo `train_embedding_model.py`.

**Criterios de aceite:**

- Embeddings sao gerados de forma cacheavel.
- O experimento pode ser executado em subset pequeno.
- O relatorio de avaliacao mostra se embeddings melhoram ou nao a acuracia, precision, recall ou F1-score.

## Fase 7 - Metricas formais e relatorios comparativos

### 7.1 Implementar metricas top-k e matriz de confusao

**Tratativa relacionada:** implementar metricas formais.

**Implementacao proposta:**

- Calcular:
  - acuracia top-1;
  - acuracia top-3;
  - erro medio absoluto em decadas;
  - matriz de confusao;
  - confianca media de acertos e erros.
- No erro medio absoluto, converter decadas para indices temporais.

**Arquivos provaveis:**

- `iesbhistorico/inference/evaluate.py`;
- `tests/test_evaluation_metrics.py`.

**Criterios de aceite:**

- As metricas sao calculadas automaticamente.
- A matriz de confusao e exportada em CSV.
- O relatorio explica quais decadas sao mais confundidas.

### 7.2 Comparar versoes do modelo

**Tratativa relacionada:** implementar metricas formais e melhorar representacao textual.

**Implementacao proposta:**

- Permitir avaliar mais de um modelo no mesmo conjunto:

```bash
python evaluate_predictions.py --model-type profile
python evaluate_predictions.py --model-type tfidf
```

- Gerar relatorio comparativo:
  - `evaluation_results/model_comparison.md`;
  - tabela de metricas por modelo;
  - diferencas por decada;
  - diferencas por tamanho de input.

**Arquivos provaveis:**

- `evaluate_predictions.py`;
- `iesbhistorico/inference/evaluate.py`;
- `evaluation_results/model_comparison.md`.

**Criterios de aceite:**

- O relatorio mostra se a nova abordagem melhora o baseline.
- Nenhum modelo substitui o atual sem comparacao documentada.

## Ordem recomendada de implementacao

1. Criar relatorio de distribuicao temporal do corpus.
2. Criar conjunto de avaliacao separado.
3. Implementar runner de avaliacao formal.
4. Adicionar validacao estrutural dos inputs.
5. Ampliar exemplos direcionados por decada.
6. Medir desempenho por tamanho de input.
7. Auditar targets de frases problemáticas.
8. Implementar balanceamento por decada no treinamento.
9. Implementar baseline TF-IDF supervisionado.
10. Implementar comparacao formal entre modelos.
11. Avaliar embeddings reais em modo experimental.

## Marcos de entrega

### Marco 1 - Avaliacao confiavel

**Entregas:**

- `evaluation_inputs/decade_labeled_phrases.jsonl`;
- `validate_input_sets.py`;
- `evaluate_predictions.py`;
- `evaluation_results/metrics.md`.

**Resultado esperado:** o projeto passa a ter uma rotina de avaliacao separada do conjunto demonstrativo.

### Marco 2 - Diagnostico de vieses

**Entregas:**

- `analyze_corpus_distribution.py`;
- `docs/generated/corpus_distribution.md`;
- metricas por tamanho de input;
- auditoria inicial de targets.

**Resultado esperado:** o projeto passa a explicar por que algumas decadas dominam as previsoes.

### Marco 3 - Melhoria de modelo

**Entregas:**

- treinamento com balanceamento por decada;
- modelo TF-IDF comparativo;
- relatorio `evaluation_results/model_comparison.md`.

**Resultado esperado:** qualquer melhora de acuracia, precision, recall ou F1-score passa a ser medida contra o baseline atual.

### Marco 4 - Experimentos avancados

**Entregas:**

- embeddings reais em modo experimental;
- comparacao entre profile, TF-IDF e embeddings;
- recomendacao documentada sobre qual abordagem manter.

**Resultado esperado:** o projeto passa a ter base tecnica para decidir se vale evoluir para representacoes semanticas mais custosas.

## Riscos e cuidados

- Nao usar frases do conjunto de avaliacao como treinamento.
- Nao comparar modelos em amostras diferentes.
- Nao declarar melhora de acuracia, precision, recall ou F1-score sem metricas reproduziveis.
- Nao substituir o modelo atual antes de manter um baseline comparavel.
- Evitar aumentar complexidade antes de diagnosticar o balanceamento do corpus.
- Registrar parametros de treinamento junto ao modelo salvo.

## Resultado esperado do plano

Ao final deste plano, o projeto devera ter um ciclo claro:

```text
corpus processado
  -> diagnostico de distribuicao temporal
  -> treinamento baseline e variantes
  -> conjunto de avaliacao separado
  -> metricas formais
  -> comparacao documentada
  -> decisao sobre proxima melhoria
```

Esse fluxo deve permitir afirmar, com base em evidencias, se uma alteracao aumenta a acuracia top-1, precision, recall ou F1-score, reduz concentracao em poucas decadas ou melhora o comportamento para diferentes tamanhos de entrada.
