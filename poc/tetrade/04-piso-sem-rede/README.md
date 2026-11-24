# Prova 4 — O que se acerta sem rede neural

Antes de treinar um modelo grande, é preciso um piso. O piso burro sempre responde a classe mais comum (em geral “Não mencionado”). O piso simples transforma o texto em contagem de palavras (TF-IDF) e treina uma regressão logística por eixo. Se um modelo grande não passar desses dois, ele não aprendeu a tarefa.

Esta prova só calcula o número quando existe `../dados/rotulos.csv`, com rótulo humano. O teste da prova 3 não entra na conta. O parâmetro C é escolhido dentro do treino, por jogo. Sem a planilha, a saída explica a falta e não inventa um F1.

```bash
cd PixelOracle-API
ml-service/.venv/bin/python poc/tetrade/04-piso-sem-rede/run.py
```

Nesta execução a planilha não existe. Decisão: sem go.

O que um F1 futuro não será: não será previsão de venda e não será o número do BERTimbau.

O cabeçalho esperado está em `../dados/rotulos.csv.exemplo`. `review_id` e `game_id` são os ids internos do banco.
