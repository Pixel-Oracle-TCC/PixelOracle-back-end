# Prova 2 — A conta do rótulo

Cada review recebe um rótulo em cada eixo. O rótulo não é um palpite: a pessoa marca os pedaços citados (combate, história, trilha, crash) como elogio, crítica ou neutro, e uma tabela transforma essa contagem em Positivo, Negativo, Neutro, Misto ou Não mencionado. Três mistos viram um Misto só quando os dados são poucos. Esta prova confere se essa tabela reproduz os 13 exemplos do manual. Ela não lê o texto e não descobre ironia sozinha.

```bash
cd PixelOracle-API
ml-service/.venv/bin/python poc/tetrade/02-regra-do-rotulo/run.py
```

Nesta execução os 13 exemplos passaram, sem falha.

O que o número não é: não é concordância entre duas pessoas e não é acerto de um modelo.

Saída: `output/resultado.json`. Os exemplos estão em `ml-service/tetrade/fixtures/exemplos_manual.json`.
