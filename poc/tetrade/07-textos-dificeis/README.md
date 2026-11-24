# Prova 7 — Ironia e texto curto

Reviews de jogo usam sarcasmo (“10/10, adoro perder o save”) e textos de uma linha. Os dois atrapalham. A pessoa marca a flag IRONIA na planilha. Sem essa coluna, não há como dizer se o modelo erra mais nesses casos.

```bash
cd PixelOracle-API
ml-service/.venv/bin/python poc/tetrade/07-textos-dificeis/run.py
```

Nesta execução a planilha não existe. Há 2.128 textos de 20 a 40 palavras na amostra de 5.027. Esse número não é taxa de erro.

O exemplo 4 do manual é ironia de propósito: a função de rótulo não detecta a piada. Quem anota é que deixa o “divertido” fora da Mecânica e marca a falha do save em Tecnologia.
