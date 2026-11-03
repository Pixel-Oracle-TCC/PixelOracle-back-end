# Provas de conceito — Tétrade Elemental

Estas são as provas do modelo atual. Uma review da Steam recebe um rótulo em cada um dos quatro eixos da Tétrade: Mecânica, Narrativa, Estética e Tecnologia. O PDF para quem não mexe no código está em [tetrade/POCs-da-Tetrade.pdf](tetrade/POCs-da-Tetrade.pdf).

Não prevê venda. Não usa a Gemini. Não altera o código de coleta nem o da análise por aspecto que já existia.

```bash
cd PixelOracle-API
./poc/tetrade/run_all.sh
```

| Prova | O que mostra |
| --- | --- |
| 1. Dados | 5.027 reviews em português, sem coluna de autor |
| 2. Regra do rótulo | Os 13 exemplos do manual passam na contagem |
| 3. Divisão por jogo | Teste com 117 reviews em jogos que o treino não vê |
| 4. Piso sem rede neural | Sem planilha humana, sem F1 |
| 5. Ajuste fino | BERTimbau e XLM-RoBERTa escritos e não treinados |
| 6. Onde erra | Sem previsão, sem matriz |
| 7. Textos difíceis | Sem flag de ironia, sem taxa de erro |

O Kappa entre duas pessoas e o F1 do modelo ficam para quando existir `tetrade/dados/rotulos.csv`. Os limites (Kappa 0,6 e macro-F1 0,60) já estão escritos e esta rodada não declara que a ideia passou.
