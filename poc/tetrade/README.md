# Tétrade Elemental

Estas provas perguntam uma coisa diferente das oito provas do motor do Pixel Oracle. Lá, o sistema aponta o que jogadores de jogos parecidos elogiam e criticam, com número e trecho. Aqui, a pergunta é se dá para classificar a review inteira em quatro eixos da Tétrade de Jesse Schell: Mecânica, Narrativa, Estética e Tecnologia. Não prevê venda. Não usa a Gemini. Não altera o código que já existe no ml-service.

O PDF técnico está em [POCs-da-Tetrade.pdf](POCs-da-Tetrade.pdf). Cada prova traz hipótese, função usada, número medido e o que a métrica não é. O termo (eixo, macro-F1, Kappa, divisão por jogo) é definido na primeira ocorrência.

```bash
cd PixelOracle-API
./poc/tetrade/run_all.sh
```

O script repete as provas automáticas. Não anota review e não treina BERTimbau.

| Prova | Pasta | O que responde nesta execução |
| --- | --- | --- |
| 1 | `01-dados` | 5.027 reviews em português, 205 jogos, sem coluna de autor |
| 2 | `02-regra-do-rotulo` | Os 13 exemplos do manual passam na contagem |
| 3 | `03-divisao-por-jogo` | Teste com 117 reviews em 8 jogos que não estão no treino |
| 4 | `04-piso-sem-rede` | Sem planilha humana, sem F1 |
| 5 | `05-ajuste-fino` | Transformer escrito e não treinado |
| 6 | `06-onde-erra` | Sem previsão, sem matriz |
| 7 | `07-textos-dificeis` | Sem flag de ironia, sem taxa de erro |

## O que falta para dizer se a ideia funciona

- Duas pessoas anotando as mesmas reviews, com Kappa médio de pelo menos 0,6.
- Cerca de 500 reviews rotuladas. O teste humano (100 a 150) continua fechado até lá.
- GPU para BERTimbau e XLM-RoBERTa. O macro-F1 médio sugerido para seguir é 0,60, e o transformer precisa passar do TF-IDF. Esses limites foram escritos antes de ver resultado. Esta rodada não declara go.

A planilha, quando existir, entra em `dados/rotulos.csv`. O cabeçalho está em `dados/rotulos.csv.exemplo`.
