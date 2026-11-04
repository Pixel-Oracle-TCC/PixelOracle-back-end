# Prova 5 — O modelo de língua, ainda sem treinar

BERTimbau é um modelo treinado em português. XLM-RoBERTa é um modelo de várias línguas. A ideia é um encoder só e quatro saídas, uma por eixo. Três sementes (13, 42 e 2024), porque com poucas reviews o número muda de uma execução para outra. Isso custa GPU e centenas de rótulos humanos. Esta etapa não baixa o modelo e não treina.

```bash
cd PixelOracle-API
ml-service/.venv/bin/python poc/tetrade/05-ajuste-fino/run.py
```

A saída registra os hiperparâmetros combinados (AdamW, taxa 2e-5, batch 16, até 10 épocas, paciência 3, 256 tokens) e a decisão sem go. `TETRADE_TREINAR=1` não libera o treino enquanto a planilha e a GPU não existirem. As dependências estão comentadas em `../requirements-treino.txt` e não foram instaladas.

O que isto não é: uma comparação em que o transformer ganhou ou perdeu do TF-IDF.
