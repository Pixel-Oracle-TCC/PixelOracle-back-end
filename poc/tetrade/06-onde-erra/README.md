# Prova 6 — Onde a previsão se confunde

Uma média esconde o erro. A matriz de confusão mostra, para cada eixo, qual rótulo humano virou qual previsão. A linha é a pessoa. A coluna é o modelo. Classe com menos de 30 exemplos não sustenta conclusão: o número existe, mas a prova diz que não dá para fechar.

```bash
cd PixelOracle-API
ml-service/.venv/bin/python poc/tetrade/06-onde-erra/run.py
```

Nesta execução a prova 4 não treinou, então não há matriz. Isso não é um F1 zero.

Quando houver rótulos, a saída será `output/resultado.json`, `output/f1_por_classe.csv` e um PNG por eixo.
