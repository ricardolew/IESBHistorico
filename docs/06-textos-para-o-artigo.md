# Textos para o artigo

## Metodologia

O prototipo desenvolvido organiza a classificacao temporal de frases jornalisticas como um pipeline reprodutivel de processamento de dados. Na versao atual, utiliza-se a New York Times Archive API como base provisoria para validar a arquitetura do sistema, a persistencia dos artefatos intermediarios, a construcao de alvos probabilisticos por decada, o treinamento e a inferencia. Essa escolha nao substitui a etapa prevista com a Hemeroteca Digital Brasileira, mas permite reduzir a incerteza tecnica inicial antes da incorporacao de OCR e tratamento de documentos historicos em portugues.

O processo inicia-se pela obtencao de arquivos JSON mensais, seguida de ingestao dos campos textuais dos artigos. Os textos sao normalizados, tokenizados e convertidos em frases candidatas por meio de n-gramas. Em seguida, as ocorrencias sao persistidas em arquivos Parquet particionados por ano e mes, permitindo a recomputacao das etapas analiticas sem depender de um banco de dados processado permanente.

## Arquitetura do sistema

A arquitetura observada e modular e orientada a etapas. Os componentes de coleta, ingestao, extracao de frases, agregacao temporal, construcao de caracteristicas, treinamento, inferencia, diagnostico e avaliacao sao implementados em modulos separados. Essa organizacao e adequada ao contexto de um TCC porque torna o sistema mais explicavel, facilita a verificacao de cada etapa e permite comparar modelos sem substituir o baseline original.

O armazenamento intermediario e baseado em arquivos Parquet. Artigos e frases sao particionados por ano e mes, enquanto artefatos derivados, como timelines, estatisticas de frases, features e manifestos de embeddings, sao recomputados a partir desses dados processados. Consultas analiticas sao executadas com DuckDB diretamente sobre os arquivos Parquet, reduzindo a necessidade de manter uma base relacional adicional.

## Pipeline de dados

A ingestao transforma documentos jornalisticos em registros estruturados de artigos e frases. Para cada artigo, sao utilizados metadados como data de publicacao, secao, subsecao e contagem de palavras, alem de campos textuais como titulo, resumo, trecho, paragrafo inicial e palavras-chave. A partir desses textos, o sistema extrai frases candidatas, calcula frequencias e registra janelas de contexto.

Na etapa analitica, as frequencias brutas sao agregadas por frase, ano e decada. O sistema calcula tambem uma frequencia normalizada por ano, obtida pela divisao da frequencia da frase pelo total de frequencias daquele ano. Essa decisao busca reduzir a influencia de variacoes no volume de publicacao e produzir alvos mais proximos da distribuicao temporal relativa da linguagem.

## Modelagem e avaliacao

O modelo principal do prototipo e um classificador probabilistico leve baseado em perfis temporais de features textuais. Ele utiliza palavras, bigramas e n-gramas de caracteres extraidos da frase de entrada para combinar perfis de decadas aprendidos a partir do dataset. A saida e uma distribuicao de probabilidade por decada, acompanhada da decada de maior probabilidade e de um valor de confianca correspondente.

Para avaliar melhorias, foi criado um conjunto separado de frases rotuladas manualmente, com duas entradas por decada entre `1900s` e `2010s`. As avaliacoes sao versionadas em diretorios proprios e registram acuracia top-1, acuracia top-3, erro medio absoluto entre decadas, matriz de confusao, distribuicao das predicoes e metricas classicas de classificacao multiclasse. Esses artefatos sao gerados por `evaluate_predictions.py` e pelo modulo `iesbhistorico/inference/metrics.py`.

Na comparacao atual, o modelo profile baseline obteve acuracia top-1 de 0,2500, acuracia top-3 de 0,4167 e erro medio de 3,2500 decadas. O modelo profile balanceado manteve acuracia top-1 de 0,2500, mas elevou top-3 para 0,5000 e reduziu o erro medio para 1,9583. Assim, o balanceamento deve ser descrito como melhoria parcial, pois aproximou temporalmente as respostas sem aumentar os acertos diretos.

Nas rodadas complementares `with-f1`, registradas em `evaluation_results/model_comparison.md`, o modelo profile baseline obteve macro F1 de 0,2009 e weighted F1 de 0,2009. O TF-IDF experimental obteve macro F1 de 0,2139 e weighted F1 de 0,2139. O profile balanceado obteve macro F1 de 0,2130 e weighted F1 de 0,2130. Esses valores devem ser interpretados como metricas complementares, nao como conclusao isolada de superioridade, pois a amostra formal ainda contem apenas 24 entradas.

A acuracia top-1 corresponde ao acerto direto da decada principal prevista. A acuracia top-3 mede se a decada correta aparece entre as tres decadas mais provaveis retornadas pelo modelo. A precision por decada mede a proporcao de predicoes corretas entre as vezes que uma decada foi prevista. O recall por decada mede a proporcao de exemplos reais de uma decada recuperados corretamente. O F1-score combina precision e recall por meio da media harmonica. O macro F1 atribui o mesmo peso a todas as decadas, enquanto o weighted F1 pondera cada decada pelo suporte observado no conjunto de avaliacao.

## Justificativa das escolhas tecnicas

O uso de uma fonte estruturada como a NYT Archive API e justificavel como estrategia incremental de desenvolvimento. Ao utilizar uma API que ja fornece metadados e textos em formato JSON, o prototipo permite validar a estrutura geral do pipeline antes de enfrentar os desafios de OCR, segmentacao e normalizacao historica exigidos pela Hemeroteca Digital Brasileira.

A escolha por Parquet particionado e DuckDB favorece a analise temporal de grandes volumes de registros textuais. Parquet oferece armazenamento colunar eficiente e DuckDB permite consultas SQL diretamente sobre os arquivos, o que simplifica a arquitetura e reduz duplicacao de estado. Essa combinacao e apropriada para um prototipo academico que precisa ser reexecutavel e auditavel.

A manutencao de modelos em arquivos separados permite comparar o baseline, o TF-IDF experimental e o modelo balanceado sem perder a referencia original. Essa decisao e importante para evitar conclusoes baseadas apenas em percepcao qualitativa.

## Justificativa das tecnologias e bibliotecas

A linguagem Python foi adotada por sua adequacao a pipelines de processamento de dados, experimentacao em aprendizado de maquina e automacao de tarefas por linha de comando. No projeto, Python permite concentrar coleta, ingestao, transformacao, treinamento, inferencia, avaliacao e geracao de relatorios em uma unica base de codigo, reduzindo a complexidade operacional do prototipo.

A biblioteca padrao de Python e utilizada para funcoes estruturais do sistema. `argparse` sustenta os comandos executaveis do projeto, permitindo reprodutibilidade por CLI. `json` e utilizado para leitura de dados brutos, datasets JSONL, modelos profile serializados e metricas de avaliacao. `pathlib` padroniza manipulacao de caminhos sem amarrar o codigo a caminhos absolutos. `logging` registra a execucao das etapas do pipeline. `hashlib` permite gerar identificadores deterministicos para artigos, frases e embeddings. `urllib` e empregado no downloader da NYT Archive API, incluindo tratamento de limite de taxa HTTP 429. `dataclasses` e tipos de Python ajudam a tornar configuracoes e estruturas internas mais explicitas.

`pandas` e utilizado como ferramenta de manipulacao tabular durante ingestao, escrita e leitura de datasets processados. A escolha e adequada ao prototipo porque simplifica a conversao entre listas de registros, DataFrames e arquivos Parquet, mantendo o codigo compreensivel para fins academicos. `pyarrow` viabiliza a gravacao e leitura de Parquet, formato escolhido por sua eficiencia colunar, compressao e compatibilidade com consultas analiticas.

`DuckDB` e utilizado como motor SQL analitico sobre arquivos Parquet. Essa escolha evita a manutencao de um banco relacional separado e permite recomputar timelines, estatisticas e validacoes diretamente a partir dos arquivos processados. Para o contexto do TCC, DuckDB contribui para auditabilidade, pois as transformacoes temporais podem ser descritas como consultas SQL sobre artefatos persistidos.

`numpy` integra a pilha numerica declarada do projeto. Embora o pipeline principal utilize majoritariamente pandas, DuckDB e scikit-learn, `numpy` e uma dependencia natural para operacoes numericas e para bibliotecas de aprendizado de maquina usadas no ambiente. Sua presenca e coerente com a infraestrutura de modelagem e avaliacao, ainda que o codigo atual nao dependa de chamadas numericas complexas escritas manualmente.

`scikit-learn` foi incorporado para construir um baseline supervisionado experimental com TF-IDF e regressao logistica. A justificativa dessa escolha e metodologica: o modelo profile original precisava ser comparado com uma abordagem conhecida, simples e reprodutivel. O TF-IDF experimental nao substituiu o baseline, mas permite registrar comparacoes quantitativas em um mesmo conjunto de avaliacao.

`joblib` e utilizado para serializar e carregar o modelo TF-IDF experimental. Essa biblioteca e adequada para objetos de scikit-learn, pois preserva pipelines treinados de forma simples e permite reutilizacao posterior na inferencia e na avaliacao versionada.

`sentence-transformers` foi mantido como tecnologia opcional para experimentos controlados de embeddings reais. O comando `build_real_embeddings.py` permite gerar vetores para subconjuntos limitados, sem tornar embeddings uma dependencia obrigatoria do fluxo principal. Essa decisao reduz custo computacional durante a validacao do prototipo e preserva uma trilha de evolucao para representacoes semanticas mais ricas.

`spaCy` permanece como dependencia declarada para evolucao futura da extracao linguistica, especialmente caso o projeto passe a utilizar entidades nomeadas, sintagmas nominais ou recursos linguisticos mais sofisticados. No estado atual, a extracao principal ainda e baseada em n-gramas de 1 a 4 tokens. Portanto, spaCy deve ser descrito como tecnologia prevista para extensao da extracao, nao como componente efetivamente usado nas predicoes atuais.

O formato JSONL foi escolhido para datasets de treinamento, amostras demonstrativas e conjuntos de avaliacao porque permite escrita incremental, leitura linha a linha e versionamento simples. O formato Markdown foi usado para relatorios por ser legivel por humanos e diretamente aproveitavel na documentacao do TCC. CSV foi usado para matriz de confusao por facilitar inspecao tabular e eventual abertura em planilhas.

Por fim, a organizacao dos artefatos em diretorios separados reflete uma decisao de reprodutibilidade. `sample_inputs/` guarda demonstracoes, `evaluation_inputs/` guarda entradas rotuladas para avaliacao formal, `evaluation_results/` registra rodadas versionadas, `docs/generated/` armazena diagnosticos textuais e `data/reports/` guarda relatorios estruturados. Essa separacao permite apresentar as diferencas entre baseline, TF-IDF experimental e modelo balanceado sem sobrescrever resultados anteriores.

## Limitacoes do prototipo

O prototipo atual nao deve ser interpretado como uma solucao final para jornais brasileiros historicos. A base usada encontra-se em ingles e provem do New York Times, enquanto o plano de trabalho preve o uso da Hemeroteca Digital Brasileira. Assim, a validade historica, linguistica e cultural dos resultados ainda depende da futura substituicao ou complementacao do corpus.

O conjunto formal de avaliacao ainda e pequeno e deve ser ampliado antes de sustentar conclusoes fortes sobre desempenho. Como ha apenas duas entradas por decada, metricas por classe podem oscilar fortemente com um unico acerto ou erro. Precision, recall e F1-score nao substituem a analise qualitativa das confusoes, dos exemplos errados e da adequacao historica das frases. O TF-IDF experimental foi treinado em um recorte limitado do dataset e ainda nao superou o baseline. A geracao real de embeddings esta disponivel como comando opcional, mas ainda nao foi incorporada como modelo principal.

## Trabalhos futuros

Como trabalhos futuros, recomenda-se ampliar o conjunto rotulado por decada, testar balanceamentos adicionais, avaliar modelos supervisionados com maior cobertura do dataset, auditar frases problematicas por meio das timelines e estudar calibracao probabilistica das saidas.

Outra frente importante e ampliar a robustez da normalizacao textual, especialmente para lidar com variantes ortograficas, nomes proprios, ruidos de digitalizacao e expressoes historicamente marcadas. Essa evolucao sera particularmente relevante quando o corpus migrar para documentos brasileiros digitalizados.

## Adaptacao futura para Hemeroteca Digital Brasileira

A adaptacao para a Hemeroteca Digital Brasileira exigira uma camada adicional antes da ingestao textual atualmente implementada. Essa camada devera coletar PDFs ou imagens, executar OCR, corrigir e normalizar os textos extraidos, segmentar artigos em meio a paginas digitalizadas e associar corretamente cada texto a seus metadados temporais.

Essa migracao tambem demandara criterios explicitos de avaliacao da qualidade do OCR, pois erros de reconhecimento podem alterar palavras, datas, nomes proprios e expressoes caracteristicas de um periodo. Portanto, a etapa futura devera avaliar nao apenas o desempenho do classificador, mas tambem o impacto dos erros de OCR sobre a distribuicao temporal produzida pelo modelo.

Os resultados obtidos com a base em ingles da NYT nao devem ser extrapolados para a Hemeroteca Digital Brasileira. A etapa futura exigira nova avaliacao apos OCR, normalizacao de portugues historico e segmentacao dos artigos digitalizados.
