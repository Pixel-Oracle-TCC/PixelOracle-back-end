# Resultados — sentimento por eixo

- gerado em UTC: 2026-11-09T02:09:23.745510+00:00
- hash dos dados: `7ae9b1ec6352cfb6d237d47f1bb176be8ff6abc437e0b24a21df1cd863ed90c1`
- versões: {"python": "3.12.3", "platform": "Linux-6.8.0-86-generic-x86_64-with-glibc2.39", "pandas": "3.1.0", "numpy": "2.5.4", "sklearn": "1.6.1", "torch": "2.15.0+cpu", "transformers": "4.46.3", "matplotlib": "3.11.2"}

## Tabela por execução

| modelo | esquema | semente | Mecânica_macro_f1 | Mecânica_acc | Narrativa_macro_f1 | Narrativa_acc | Estética_macro_f1 | Estética_acc | Tecnologia_macro_f1 | Tecnologia_acc | media_macro_f1 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 7 | 13 | 0.2798 | 0.5610 | 0.1807 | 0.7073 | 0.2123 | 0.7439 | 0.1690 | 0.9146 | 0.2105 |
| bertimbau | 7 | 13 | 0.3480 | 0.6098 | 0.2118 | 0.7561 | 0.2625 | 0.7439 | 0.1882 | 0.8049 | 0.2526 |
| xlmr | 7 | 13 | 0.3493 | 0.6585 | 0.1875 | 0.6829 | 0.2062 | 0.7073 | 0.1647 | 0.8415 | 0.2269 |

## Agregado (média ± desvio das sementes)

| index | modelo | esquema | mean | std |
| --- | --- | --- | --- | --- |
| 0 | baseline | 7 | 0.2105 | nan |
| 1 | bertimbau | 7 | 0.2526 | nan |
| 2 | xlmr | 7 | 0.2269 | nan |

## Notas

- baseline seed 13 media_macro_f1=0.2105 ckpt=`checkpoints/baseline_7_seed13.joblib`
- bertimbau seed 13 val=0.2233 test_mean=0.2526 early stop época 8; melhor val na época 5; ckpt=`checkpoints/bertimbau_7_seed13/best.pt`
- xlmr seed 13 val=0.2167 test_mean=0.2269 10 épocas; ckpt=`checkpoints/xlmr_7_seed13/best.pt`
- split: 316 treino / 82 teste por `game_id`; val 61 recortado do treino
- comparação com a rodada de 148 rótulos: `outputs/comparacao.md`
