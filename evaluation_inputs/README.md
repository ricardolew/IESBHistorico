# Evaluation inputs

Este diretorio contem entradas rotuladas para avaliacao formal do classificador.

Arquivo principal:

```text
evaluation_inputs/decade_labeled_phrases.jsonl
```

Este conjunto deve ser mantido separado do treinamento. Ele serve para comparar modelos e versoes de teste ao longo do tempo.

Campos:

- `id`: identificador estavel;
- `phrase`: frase enviada ao classificador;
- `expected_decade`: decada esperada;
- `source_note`: justificativa humana curta para o rotulo;
- `review_status`: `reviewed` ou `needs_review`.

Fluxo:

```bash
python validate_input_sets.py
python evaluate_predictions.py --run-id baseline-current
```

