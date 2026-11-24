# Resultados — sentimento por eixo

- gerado em UTC: 2026-11-08T23:40:40.344658+00:00
- hash dos dados: `7ae9b1ec6352cfb6d237d47f1bb176be8ff6abc437e0b24a21df1cd863ed90c1`
- versões: {"python": "3.12.3", "platform": "Linux-6.8.0-86-generic-x86_64-with-glibc2.39", "pandas": "3.1.0", "numpy": "2.5.4", "sklearn": "1.6.1", "torch": "2.15.0+cpu", "transformers": "4.46.3", "matplotlib": "3.11.2"}

## Tabela por execução

| modelo | esquema | semente | Mecânica_macro_f1 | Mecânica_acc | Narrativa_macro_f1 | Narrativa_acc | Estética_macro_f1 | Estética_acc | Tecnologia_macro_f1 | Tecnologia_acc | media_macro_f1 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 7 | 13 | 0.2798 | 0.5610 | 0.1807 | 0.7073 | 0.2123 | 0.7439 | 0.1690 | 0.9146 | 0.2105 |
| baseline | 7 | 42 | 0.2798 | 0.5610 | 0.1807 | 0.7073 | 0.2123 | 0.7439 | 0.1690 | 0.9146 | 0.2105 |
| baseline | 7 | 2024 | 0.2798 | 0.5610 | 0.1807 | 0.7073 | 0.2123 | 0.7439 | 0.1690 | 0.9146 | 0.2105 |
| bertimbau | 7 | 13 | 0.3556 | 0.6220 | 0.2118 | 0.7561 | 0.2594 | 0.7439 | 0.1882 | 0.8049 | 0.2537 |

## Agregado (média ± desvio das sementes)

| index | modelo | esquema | mean | std |
| --- | --- | --- | --- | --- |
| 0 | baseline | 7 | 0.2105 | 0.0000 |
| 1 | bertimbau | 7 | 0.2537 | nan |

## Notas

- bertimbau seed 13 val=0.2202 test_mean=0.2537 ckpt=/home/wendell/Documentos/PixelOracle-back-end/ml-service/sentiment_training/checkpoints/bertimbau_7_seed13/best.pt
