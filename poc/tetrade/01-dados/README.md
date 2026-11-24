# Prova 1 — Os textos entram limpos

Uma review é o texto que alguém publica na página de um jogo na Steam. Esta prova não prevê venda e não chama a Steam de novo. Ela só confere se os textos em português que já estão no banco podem ser a matéria-prima da Tétrade: sem coluna que identifique o autor, sem o mesmo texto contado duas vezes, e com tamanho que uma pessoa consegue anotar (20 a 200 palavras).

```bash
cd PixelOracle-API
ml-service/.venv/bin/python poc/tetrade/01-dados/run.py
```

Nesta execução: 10.548 reviews em português, nenhuma coluna de autor. Saíram 4 textos quase sem letra, 2 duplicatas no mesmo jogo e 32 cópias de textos que apareciam em jogos diferentes (26 textos distintos). Fora do tamanho: 4.596 curtas e 887 longas. Sobram **5.027 reviews em 205 jogos**.

O que o número não é: não é o F1 de um modelo e não é uma coleta nova.

Saída: `output/resultado.json` e `../dados/amostra_ids.csv`.
