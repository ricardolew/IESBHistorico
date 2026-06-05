# Analise da amostra de predictions

## Objetivo da amostra

Esta analise descreve a amostra de entradas criada em `sample_inputs/phrases.jsonl` e os resultados registrados em `sample_inputs/results/predictions.md` e `sample_inputs/results/predictions.jsonl`. O objetivo e avaliar, de forma exploratoria, como o prototipo atual distribui frases por decadas e quais limitacoes aparecem quando o conjunto de teste inclui frases direcionadas e entradas aleatorias de tamanhos variados.

Esta secao nao deve ser interpretada como avaliacao experimental final do modelo. A amostra foi definida manualmente para observacao qualitativa e diagnostico tecnico, nao como conjunto estatisticamente balanceado de validacao.

## Base de dados do sistema

O modelo atual foi treinado a partir de dados do New York Times Archive API, processados pelo pipeline do projeto. O fluxo parte de arquivos JSON mensais em `data/raw/`, gera particoes Parquet para artigos e frases em `data/parquet/`, constroi estatisticas temporais por frase e exporta um dataset JSONL de treinamento em `data/datasets/training_dataset.jsonl`. O modelo salvo em `data/models/decade_model.json` e usado para gerar as previsoes da amostra.

Na implementacao atual, a extracao de frases durante o treinamento utiliza n-gramas de 1 a 4 tokens. Isso significa que entradas curtas, especialmente expressoes de ate quatro palavras, estao mais proximas do padrao de dados usado para treinar o sistema. Frases longas e sentencas completas sao aceitas pelo fluxo de inferencia, mas representam um uso menos alinhado ao formato de treinamento.

## Entradas selecionadas

A amostra atual contem 168 entradas:

- 24 entradas direcionadas, com `expected_decade` preenchido;
- 144 entradas aleatorias, sem decada esperada;
- 2 entradas direcionadas para cada decada estudada entre `1900s` e `2010s`;
- entradas curtas e longas, incluindo termos de 1 token, expressoes de 2 a 4 tokens, frases medias e frases acima de 90 caracteres.

Distribuicao por tamanho aproximado:

| Faixa de tamanho | Quantidade |
| --- | ---: |
| 1 token | 12 |
| 2 a 4 tokens | 120 |
| 5 a 8 tokens | 18 |
| 9 a 15 tokens | 17 |
| 16 ou mais tokens | 1 |
| Acima de 90 caracteres | 10 |

A maior parte da amostra ainda esta concentrada em expressoes de 2 a 4 tokens, o que e coerente com o funcionamento atual do extrator. Os novos casos longos foram incluidos para observar comportamento fora do padrao principal de treinamento.

## Acuracia top-1 observada nos direcionados

Nos 24 casos direcionados, o sistema acertou 6, resultando em uma acuracia exploratoria top-1 de 25,0% na amostra direcionada.

Depois da implementacao do fluxo de avaliacao versionada, esta mesma amostra direcionada foi separada em `evaluation_inputs/decade_labeled_phrases.jsonl` e avaliada em `evaluation_results/profile-baseline-current`. A rodada formal registrou acuracia top-1 de 0,2500, acuracia top-3 de 0,4167 e erro medio absoluto de 3,2500 decadas. Esses resultados devem ser usados como baseline para comparacoes futuras.

Apos o retreinamento com balanceamento por decada, foi gerada a rodada `evaluation_results/profile-balanced-current`. A acuracia top-1 permaneceu em 0,2500, mas a acuracia top-3 subiu de 0,4167 para 0,5000 e o erro medio absoluto entre decadas caiu de 3,2500 para 1,9583. Isso indica que o balanceamento ainda nao aumentou a quantidade de acertos diretos, mas aproximou parte das previsoes da decada correta e reduziu erros temporalmente muito distantes.

Rodadas complementares com precision, recall e F1-score foram geradas em `evaluation_results/profile-baseline-with-f1`, `evaluation_results/tfidf-5000-with-f1` e `evaluation_results/profile-balanced-with-f1`. Os arquivos `metrics.md`, `metrics.json` e `classification_report.md` dessas rodadas incluem suporte, precision, recall, F1-score, acertos, erros e principais confusoes por decada.

| Decada esperada | Acertos | Total |
| --- | ---: | ---: |
| 1900s | 0 | 2 |
| 1910s | 0 | 2 |
| 1920s | 0 | 2 |
| 1930s | 1 | 2 |
| 1940s | 1 | 2 |
| 1950s | 1 | 2 |
| 1960s | 0 | 2 |
| 1970s | 1 | 2 |
| 1980s | 0 | 2 |
| 1990s | 1 | 2 |
| 2000s | 1 | 2 |
| 2010s | 0 | 2 |

Casos direcionados acertados:

- `great depression` -> esperado `1930s`, previsto `1930s`;
- `german invasion` -> esperado `1940s`, previsto `1940s`;
- `korean war` -> esperado `1950s`, previsto `1950s`;
- `vietnam ceasefire` -> esperado `1970s`, previsto `1970s`;
- `gulf war` -> esperado `1990s`, previsto `1990s`;
- `world trade center` -> esperado `2000s`, previsto `2000s`.

Casos direcionados nao acertados indicam que o modelo ainda nao aprendeu de forma robusta varias associacoes historicas esperadas pelo pesquisador. Por exemplo, `moon landing` foi classificado como `1930s`, `cuban missile crisis` como `2000s`, `berlin wall` como `1930s` e `arab spring` como `1970s`.

## Distribuicao das previsoes

Considerando todas as 168 entradas, as decadas mais frequentemente previstas foram `2000s` e `1930s`.

| Decada prevista | Quantidade |
| --- | ---: |
| 1930s | 58 |
| 1940s | 5 |
| 1950s | 8 |
| 1960s | 1 |
| 1970s | 5 |
| 1990s | 14 |
| 2000s | 68 |
| 2010s | 9 |

Nao houve previsoes de `1900s`, `1910s`, `1920s` ou `1980s` como decada principal nesta amostra. Esse comportamento sugere concentracao do modelo em poucas decadas e possivel desequilibrio dos perfis aprendidos.

Nos 24 casos direcionados, as principais decadas previstas foram:

| Decada prevista nos direcionados | Quantidade |
| --- | ---: |
| 1930s | 7 |
| 1940s | 3 |
| 1950s | 1 |
| 1970s | 3 |
| 1990s | 2 |
| 2000s | 7 |
| 2010s | 1 |

Nos 144 casos aleatorios, as principais decadas previstas foram:

| Decada prevista nos aleatorios | Quantidade |
| --- | ---: |
| 1930s | 51 |
| 1940s | 2 |
| 1950s | 7 |
| 1960s | 1 |
| 1970s | 2 |
| 1990s | 12 |
| 2000s | 61 |
| 2010s | 8 |

## Confianca das previsoes

As confiancas observadas sao baixas a moderadas. Na amostra completa, a confianca minima foi 0,119469, a media foi aproximadamente 0,161158 e a maxima foi 0,458090.

| Grupo | Minima | Media | Maxima |
| --- | ---: | ---: | ---: |
| Todas as entradas | 0,119469 | 0,161158 | 0,458090 |
| Entradas direcionadas | 0,119469 | 0,169711 | 0,301548 |
| Entradas aleatorias | 0,122537 | 0,159733 | 0,458090 |

Esses valores indicam que, mesmo quando o sistema escolhe uma decada principal, a probabilidade esta distribuida entre varias decadas. Isso e coerente com a proposta de gerar distribuicoes probabilisticas, mas tambem evidencia baixa separacao entre classes no estado atual do modelo.

## Efeito do tamanho das entradas

O sistema aceita entradas longas na inferencia, mas o treinamento foi construido a partir de n-gramas curtos. Por isso, frases de 1 a 4 tokens tendem a ser mais representativas do padrao aprendido. Entradas longas geram features de palavras, bigramas e n-gramas de caracteres, mas podem diluir o sinal temporal em muitos termos genericos.

Na amostra atual, todos os acertos direcionados ocorreram na faixa de 2 a 4 tokens. As entradas longas foram adicionadas como teste de robustez, nao como formato ideal de uso. Para o sistema atual, recomenda-se priorizar frases curtas, expressoes historicas e sintagmas nominais, evitando sentencas completas quando o objetivo for obter uma classificacao temporal mais clara.

## Limitacoes observadas

As principais limitacoes observadas sao:

- concentracao excessiva de previsoes em `1930s` e `2000s`;
- ausencia de previsoes principais para algumas decadas estudadas;
- baixa acuracia top-1 nos casos direcionados;
- confiancas medias baixas;
- fragilidade em expressoes historicas conhecidas que deveriam estar associadas a decadas especificas;
- diferenca entre o tamanho ideal de treino, baseado em n-gramas de ate 4 tokens, e entradas longas usadas na amostra;
- dependencia de uma base provisoria em ingles do New York Times, ainda distante do corpus final previsto para a Hemeroteca Digital Brasileira.

## Tratativas para melhorar a acuracia e a qualidade das metricas

As melhorias recomendadas sao:

1. Balancear o corpus por decada.

   O modelo parece concentrar previsoes em poucas decadas. Uma tratativa importante e verificar a distribuicao de artigos, frases e targets por decada, reduzindo vieses de volume ou super-representacao temporal.

2. Criar um conjunto de avaliacao separado.

   A amostra atual e util para diagnostico, mas nao substitui um conjunto de teste controlado. Recomenda-se criar um dataset rotulado manualmente com frases historicas por decada, separado do treinamento.

3. Aumentar a quantidade de exemplos direcionados por decada.

   Dois exemplos por decada sao suficientes apenas para uma primeira observacao. Para avaliar desempenho por periodo, recomenda-se ampliar para dezenas ou centenas de frases por decada.

4. Diferenciar frase curta de sentenca longa.

   O sistema deveria registrar metricas separadas para entradas de 1 token, 2 a 4 tokens, 5 a 8 tokens e sentencas longas. Isso permitiria declarar qual formato de entrada e mais adequado ao modelo.

5. Melhorar a representacao textual.

   O modelo atual usa perfis de palavras, bigramas e n-gramas de caracteres. A acuracia e as metricas de precision, recall e F1-score podem melhorar com embeddings reais, modelos supervisionados comparativos ou combinacao entre features temporais e semanticas.

6. Revisar a construcao dos targets.

   As probabilidades por decada derivam de frequencias normalizadas. E recomendavel auditar frases de alta frequencia, termos ambiguos e expressoes que aparecem em varios contextos, pois elas podem deslocar o pico temporal.

7. Implementar metricas formais.

   Recomenda-se calcular acuracia top-1, acuracia top-3, erro medio de distancia entre decadas, matriz de confusao, precision, recall, F1-score e calibracao das probabilidades.

8. Preparar adaptacao para portugues historico.

   Para a etapa com Hemeroteca Digital Brasileira, sera necessario adaptar tokenizacao, normalizacao, tratamento de OCR, variantes ortograficas e filtros de ruido. A acuracia e as metricas de classificacao observadas no corpus em ingles nao devem ser extrapoladas para o corpus brasileiro.

## Implementacoes relacionadas

As tratativas tecnicas, exceto a preparacao para portugues historico, foram iniciadas com os seguintes comandos e artefatos:

- `validate_input_sets.py`: validacao estrutural das amostras;
- `evaluate_predictions.py`: metricas formais versionadas;
- `compare_evaluation_runs.py`: comparacao entre rodadas;
- `analyze_corpus_distribution.py`: diagnostico do corpus por decada;
- `inspect_phrase_target.py`: auditoria de targets por frase;
- `train.py --balance-decades`: treinamento profile com pesos por decada;
- `train_tfidf.py`: baseline supervisionado experimental.

Os resultados comparativos atuais estao em `evaluation_results/model_comparison.md`.

## Resultado apos retreinamento balanceado

O modelo balanceado foi salvo em `data/models/decade_model_balanced.json` e testado sem substituir o baseline original. A amostra variada foi reprocessada em:

- `sample_inputs/results/predictions_balanced.md`;
- `sample_inputs/results/predictions_balanced.jsonl`.

Na amostra variada de 168 entradas, 48 entradas mudaram de decada principal em relacao ao modelo baseline. A quantidade de acertos nos 24 direcionados permaneceu em 6/24, mas a distribuicao das previsoes ficou menos concentrada em `2000s`:

| Modelo | 1930s | 2000s | Decadas previstas como top-1 |
| --- | ---: | ---: | ---: |
| Profile baseline | 58 | 68 | 8 |
| Profile balanceado | 68 | 29 | 11 |

No conjunto formal direcionado, a comparacao versionada registrou:

| Rodada | Top-1 | Top-3 | Erro medio absoluto |
| --- | ---: | ---: | ---: |
| `profile-baseline-current` | 0,2500 | 0,4167 | 3,2500 |
| `profile-balanced-current` | 0,2500 | 0,5000 | 1,9583 |

Portanto, o retreinamento balanceado deve ser considerado uma melhoria parcial: ele melhora a proximidade temporal das respostas e a recuperacao top-3, mas ainda nao melhora a acuracia top-1.

Nas rodadas `with-f1`, a comparacao formal ficou:

| Rodada | Top-1 | Top-3 | Erro medio | Macro F1 | Weighted F1 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `profile-baseline-with-f1` | 0,2500 | 0,4167 | 3,2500 | 0,2009 | 0,2009 |
| `tfidf-5000-with-f1` | 0,2500 | 0,3333 | 4,2500 | 0,2139 | 0,2139 |
| `profile-balanced-with-f1` | 0,2500 | 0,5000 | 1,9583 | 0,2130 | 0,2130 |

Como a amostra formal tem suporte baixo, duas frases por decada, as metricas por classe devem ser tratadas como diagnostico preliminar. Precision, recall e F1-score complementam a matriz de confusao e a analise qualitativa dos erros, mas nao substituem a revisao manual das frases classificadas incorretamente.

## Conclusao

A amostra de predictions mostra que o pipeline esta funcional e consegue produzir distribuicoes de probabilidade para entradas variadas. Entretanto, a acuracia exploratoria top-1 de 25,0% nos casos direcionados e a concentracao de previsoes em poucas decadas indicam que o modelo atual deve ser tratado como prototipo inicial. O principal valor desta amostra e revelar pontos de melhoria: balanceamento temporal, avaliacao formal, ampliacao de exemplos rotulados, melhor representacao textual e preparacao para o dominio da Hemeroteca Digital Brasileira.
