# Treino anterior (148 rótulos, 8 jogos)

Referência da rodada de 2026-11-03, antes dos lotes 2 e 3. Split 116 treino / 32 teste. Modelo: TF-IDF + LogReg, esquema 7, semente 13.

| modelo | Mecânica_macro_f1 | Mecânica_acc | Narrativa_macro_f1 | Narrativa_acc | Estética_macro_f1 | Estética_acc | Tecnologia_macro_f1 | Tecnologia_acc | media_macro_f1 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 0.2832 | 0.4688 | 0.1814 | 0.6875 | 0.1871 | 0.6250 | 0.2279 | 0.8750 | 0.2199 |

BERTimbau e XLM-R naquela rodada só passaram por `--smoke` (subconjunto + 1 época). Não entram na comparação de teste.
