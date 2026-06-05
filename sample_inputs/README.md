# Sample inputs

Este diretorio guarda uma amostra de frases para gerar resultados demonstrativos do projeto.

Arquivo principal:

```text
sample_inputs/phrases.jsonl
```

Cada linha e um objeto JSON com:

- `id`: identificador estavel do input;
- `phrase`: frase enviada ao classificador;
- `group`: `directed` para frases com decada esperada ou `random` para frases exploratorias;
- `expected_decade`: decada esperada apenas para os casos direcionados; `null` nos demais;
- `note`: observacao curta para interpretacao humana.

Para gerar um relatorio de previsoes:

```bash
python run_input_sample.py
```

Saidas padrao:

```text
sample_inputs/results/predictions.md
sample_inputs/results/predictions.jsonl
```

Saidas geradas para o modelo profile balanceado:

```text
sample_inputs/results/predictions_balanced.md
sample_inputs/results/predictions_balanced.jsonl
```
