# Prova 3 — O teste não vê o jogo do treino

Se a mesma review, ou outra review do mesmo jogo, entra no treino e no teste, o modelo parece melhor do que é: ele já viu aquele jogo. Esta prova separa os 205 jogos em três grupos que não se misturam. O teste fica com 100 a 150 reviews e ninguém mede modelo nele até duas pessoas anotarem essas reviews.

```bash
cd PixelOracle-API
ml-service/.venv/bin/python poc/tetrade/03-divisao-por-jogo/run.py
```

Nesta execução, com semente 42: treino 4.032 reviews (158 jogos), validação 878 (39 jogos), teste 117 (8 jogos). Nenhum jogo e nenhum texto aparecem em dois grupos. A segunda execução reusa o arquivo salvo.

O que o número não é: o teste ainda não tem rótulo humano. Estar reservado não é Kappa.

Saída: `output/resultado.json` e `../dados/divisao.json`.
