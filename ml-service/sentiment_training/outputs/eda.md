# EDA — reviews anotadas (Tétrade de Schell)

- Arquivo: `reviews_anotadas.xlsx`
- SHA-256: `9498e0aaf5f4782fcb264e4c3b7a2938daa3fcd0ea0660c6b90dd4d0b56c67ed`
- Linhas no arquivo: **4000**
- Sem nenhum eixo preenchido (removidas): **3851**
- Parcialmente preenchidas (removidas): **1**
- Rótulo inválido (não mapeado): **1**
- Removidas por MIN_WORDS: **0**
- Rotuladas usadas: **148**
- Jogos distintos (rotuladas): **8**

> **Aviso:** menos de 300 linhas rotuladas (148). Métricas instáveis — use `--smoke` até haver mais anotações.

## Anotador

- `Claude`: 100
- `(vazio)`: 48

## Distribuição das 7 classes por eixo

### Mecânica

| Classe | n | % |
|---|---:|---:|
| POS | 62 | 41.9 |
| NEG | 20 | 13.5 |
| NEU | 3 | 2.0 |
| MAJ_POS | 11 | 7.4 |
| DIV | 10 | 6.8 |
| MAJ_NEG | 8 | 5.4 |
| NM | 34 | 23.0 |

### Narrativa

| Classe | n | % |
|---|---:|---:|
| POS | 30 | 20.3 |
| NEG | 5 | 3.4 |
| NEU | 4 | 2.7 |
| MAJ_POS | 2 | 1.4 |
| DIV | 2 | 1.4 |
| MAJ_NEG | 1 | 0.7 |
| NM | 104 | 70.3 |

### Estética

| Classe | n | % |
|---|---:|---:|
| POS | 55 | 37.2 |
| NEG | 9 | 6.1 |
| NEU | 3 | 2.0 |
| MAJ_POS | 3 | 2.0 |
| DIV | 0 | 0.0 |
| MAJ_NEG | 0 | 0.0 |
| NM | 78 | 52.7 |

### Tecnologia

| Classe | n | % |
|---|---:|---:|
| POS | 6 | 4.1 |
| NEG | 17 | 11.5 |
| NEU | 1 | 0.7 |
| MAJ_POS | 0 | 0.0 |
| DIV | 1 | 0.7 |
| MAJ_NEG | 0 | 0.0 |
| NM | 123 | 83.1 |

**Classes com menos de 30 exemplos:** Mecânica/NEG (20), Mecânica/NEU (3), Mecânica/MAJ_POS (11), Mecânica/DIV (10), Mecânica/MAJ_NEG (8), Narrativa/NEG (5), Narrativa/NEU (4), Narrativa/MAJ_POS (2), Narrativa/DIV (2), Narrativa/MAJ_NEG (1), Estética/NEG (9), Estética/NEU (3), Estética/MAJ_POS (3), Tecnologia/POS (6), Tecnologia/NEG (17), Tecnologia/NEU (1), Tecnologia/DIV (1)

**Classes ausentes:** Estética/DIV, Estética/MAJ_NEG, Tecnologia/MAJ_POS, Tecnologia/MAJ_NEG

## Tamanho do texto (palavras)

- média 97.5, mediana 45.0, p90 266.3, p99 625.6
- < 20 palavras: 39
- > 200 palavras: 21

## Quatro eixos = Não mencionado

- 28 reviews (18.9%)

## Split por jogo

- semente escolhida: 23 (menor desvio de distribuição)
- train 116 / val 0 / test 32 reviews
- jogos train/val/test: 6 / 0 / 2
