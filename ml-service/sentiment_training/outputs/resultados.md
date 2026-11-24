# Resultados — sentimento por eixo

- gerado em UTC: 2026-11-24T13:02:28.697163+00:00
- hash dos dados: `62858c46123f6389e0ab822890d89e1e1e0eb5d97e822aec2a7ff2f6142c1310`
- versões: {"python": "3.12.3", "platform": "Linux-6.8.0-86-generic-x86_64-with-glibc2.39", "pandas": "3.1.0", "numpy": "2.5.4", "sklearn": "1.6.1", "torch": "2.15.0+cpu", "transformers": "4.46.3", "matplotlib": "3.11.2"}

## Tabela por execução

| modelo | esquema | semente | Mecânica_macro_f1 | Mecânica_acc | Narrativa_macro_f1 | Narrativa_acc | Estética_macro_f1 | Estética_acc | Tecnologia_macro_f1 | Tecnologia_acc | media_macro_f1 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 7 | 13 | 0.3344 | 0.5970 | 0.2229 | 0.8408 | 0.2389 | 0.8408 | 0.1980 | 0.8607 | 0.2486 |
| bertimbau | 7 | 13 | 0.3512 | 0.6070 | 0.2246 | 0.8557 | 0.2233 | 0.8060 | 0.2296 | 0.8806 | 0.2572 |

## Agregado (média ± desvio das sementes)

| index | modelo | esquema | mean | std |
| --- | --- | --- | --- | --- |
| 0 | baseline | 7 | 0.2486 | nan |
| 1 | bertimbau | 7 | 0.2572 | nan |

## Notas

- bertimbau seed 13 val=0.2988 test_mean=0.2572 ckpt=/home/wendell/Documentos/PixelOracle-back-end/ml-service/sentiment_training/checkpoints/bertimbau_7_seed13/best.pt
