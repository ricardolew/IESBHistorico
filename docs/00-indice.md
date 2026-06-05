# Indice da documentacao

## Documentos principais

- `01-visao-geral-do-sistema.md`: objetivo, escopo atual, escopo futuro e resultados atuais.
- `02-arquitetura.md`: arquitetura, componentes e fluxo de execucao.
- `03-pipeline-de-dados.md`: fonte de dados, ingestao, agregacao, treinamento, inferencia e avaliacao.
- `04-especificacoes-tecnicas.md`: comandos, dependencias, entradas, saidas e artefatos locais.
- `05-decisoes-arquiteturais.md`: ADRs simplificadas.
- `06-textos-para-o-artigo.md`: trechos em linguagem academica para reaproveitamento no TCC.
- `07-analise-da-amostra-de-predictions.md`: analise da amostra demonstrativa e das previsoes.
- `08-plano-de-implementacao-melhoria-precisao.md`: plano e status das melhorias de desempenho.
- `09-relatorio-validacao-organizacao.md`: validacao final de integridade e organizacao do sistema.
- `10-apresentacao-do-sistema.md`: roteiro em formato de slides para apresentacao do projeto.

## Artefatos gerados

- `docs/generated/corpus_distribution.md`: distribuicao temporal do corpus.
- `docs/generated/target_moon_landing.md`: exemplo de auditoria de target por frase.
- `evaluation_results/model_comparison.md`: comparacao das rodadas versionadas.
- `evaluation_results/*/classification_report.md`: precision, recall, F1-score, suporte, acertos, erros e principais confusoes por decada.

## Fluxo recomendado para apresentacao

1. Apresentar `01-visao-geral-do-sistema.md`.
2. Explicar arquitetura com `02-arquitetura.md`.
3. Demonstrar pipeline com `03-pipeline-de-dados.md`.
4. Mostrar resultados antes/depois em `07-analise-da-amostra-de-predictions.md`.
5. Usar `evaluation_results/model_comparison.md` para a tabela comparativa.
6. Fechar com `09-relatorio-validacao-organizacao.md`.

Atalho: usar `10-apresentacao-do-sistema.md` como roteiro consolidado para gerar os slides.
