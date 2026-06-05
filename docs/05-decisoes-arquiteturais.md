# Decisoes arquiteturais

## ADR 1 - NYT Archive API como fonte provisoria

**Contexto:** validar o pipeline antes da etapa com corpus brasileiro historico.

**Decisao:** usar a New York Times Archive API no prototipo atual.

**Justificativa:** a fonte fornece JSON estruturado por ano e mes, reduzindo complexidade inicial.

**Consequencias positivas:** permite validar coleta, persistencia, agregacao, treinamento, inferencia e avaliacao.

**Limitacoes:** corpus em ingles, nao equivalente a jornais brasileiros historicos.

**Impacto futuro:** a Hemeroteca exigira OCR, segmentacao, normalizacao de portugues historico e novos metadados.

## ADR 2 - Pipeline modular com orquestrador

**Contexto:** ha varias etapas dependentes no processamento.

**Decisao:** manter cada etapa em modulo proprio e usar `build_all.py` como orquestrador.

**Justificativa:** facilita retomada, testes e execucao manual por etapa.

**Consequencias positivas:** o sistema e mais explicavel para o TCC e mais simples de diagnosticar.

**Limitacoes:** consistencia entre artefatos depende de checkpoints e cuidado ao retreinar.

## ADR 3 - Parquet particionado como fonte processada

**Contexto:** o corpus gera dezenas de milhoes de linhas.

**Decisao:** usar Parquet particionado para artigos e frases, e Parquet recomputavel para artefatos derivados.

**Justificativa:** formato colunar eficiente, consultavel com DuckDB.

**Consequencias positivas:** permite validacao e recomputacao sem manter banco processado separado.

**Limitacoes:** os arquivos locais podem ser grandes; modelos JSON profile tambem ficam grandes.

## ADR 4 - DuckDB como motor analitico

**Contexto:** agregacoes temporais exigem SQL sobre Parquet.

**Decisao:** usar DuckDB em memoria.

**Justificativa:** evita banco persistente adicional e consulta Parquet diretamente.

**Consequencias positivas:** simplicidade operacional e boa auditabilidade.

**Limitacoes:** recursos locais ainda limitam consultas muito grandes.

## ADR 5 - Normalizacao por frequencia anual

**Contexto:** o volume de artigos varia ao longo do tempo.

**Decisao:** calcular frequencia normalizada por ano antes de derivar targets por decada.

**Justificativa:** reduz vies do volume anual do corpus.

**Consequencias positivas:** torna decadas mais comparaveis.

**Limitacoes:** nao remove vies editorial, tematico ou de cobertura historica.

## ADR 6 - Modelo profile como baseline principal

**Contexto:** o sistema precisa retornar distribuicoes por decada.

**Decisao:** manter `DecadeProfileModel` como baseline principal.

**Justificativa:** modelo simples, interpretavel e compatível com o pipeline atual.

**Consequencias positivas:** predicoes rapidas apos carregar o modelo e probabilidades diretas por decada.

**Limitacoes:** acuracia top-1 ainda baixa na avaliacao formal atual.

## ADR 7 - Balanceamento por decada como variante controlada

**Contexto:** as previsoes baseline se concentravam em poucas decadas.

**Decisao:** implementar `train.py --balance-decades` e salvar o modelo balanceado separadamente.

**Justificativa:** preservar baseline e permitir comparacao antes/depois.

**Consequencias positivas:** melhorou top-3 de 0.4167 para 0.5000 e reduziu erro medio de 3.2500 para 1.9583.

**Limitacoes:** nao melhorou acuracia top-1, que permaneceu em 0.2500.

## ADR 8 - Avaliacao formal versionada

**Contexto:** a amostra demonstrativa nao bastava para comparar melhorias.

**Decisao:** criar `evaluation_inputs/` e `evaluation_results/RUN_ID/`.

**Justificativa:** separar demonstracao de avaliacao e registrar metricas reprodutiveis.

**Consequencias positivas:** permite comparar `profile-baseline-current`, `tfidf-5000-current` e `profile-balanced-current`.

**Limitacoes:** o conjunto formal ainda e pequeno.

## ADR 9 - TF-IDF como baseline experimental

**Contexto:** era necessario comparar o profile com uma abordagem supervisionada.

**Decisao:** implementar `train_tfidf.py` com `scikit-learn`.

**Justificativa:** TF-IDF e uma baseline simples, conhecida e barata de testar.

**Consequencias positivas:** gera probabilidades por decada e participa do mesmo fluxo de avaliacao.

**Limitacoes:** no experimento atual, nao superou o modelo profile.

