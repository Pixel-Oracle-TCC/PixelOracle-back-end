# EDA — reviews anotadas (Tétrade de Schell)

- Arquivo: `reviews_anotadas.xlsx`
- SHA-256: `7ae9b1ec6352cfb6d237d47f1bb176be8ff6abc437e0b24a21df1cd863ed90c1`
- Linhas no arquivo: **4000**
- Sem nenhum eixo preenchido (removidas): **3601**
- Parcialmente preenchidas (removidas): **1**
- Rótulo inválido (não mapeado): **1**
- Removidas por MIN_WORDS: **0**
- Rotuladas usadas: **398**
- Jogos distintos (rotuladas): **21**

## Anotador

- `Claude`: 350
- `(vazio)`: 48

## Distribuição das 7 classes por eixo

### Mecânica

| Classe | n | % |
|---|---:|---:|
| POS | 133 | 33.4 |
| NEG | 51 | 12.8 |
| NEU | 11 | 2.8 |
| MAJ_POS | 25 | 6.3 |
| DIV | 32 | 8.0 |
| MAJ_NEG | 17 | 4.3 |
| NM | 129 | 32.4 |

### Narrativa

| Classe | n | % |
|---|---:|---:|
| POS | 65 | 16.3 |
| NEG | 19 | 4.8 |
| NEU | 8 | 2.0 |
| MAJ_POS | 3 | 0.8 |
| DIV | 2 | 0.5 |
| MAJ_NEG | 1 | 0.3 |
| NM | 300 | 75.4 |

### Estética

| Classe | n | % |
|---|---:|---:|
| POS | 113 | 28.4 |
| NEG | 23 | 5.8 |
| NEU | 10 | 2.5 |
| MAJ_POS | 6 | 1.5 |
| DIV | 2 | 0.5 |
| MAJ_NEG | 2 | 0.5 |
| NM | 242 | 60.8 |

### Tecnologia

| Classe | n | % |
|---|---:|---:|
| POS | 16 | 4.0 |
| NEG | 55 | 13.8 |
| NEU | 7 | 1.8 |
| MAJ_POS | 0 | 0.0 |
| DIV | 3 | 0.8 |
| MAJ_NEG | 0 | 0.0 |
| NM | 317 | 79.6 |

**Classes com menos de 30 exemplos:** Mecânica/NEU (11), Mecânica/MAJ_POS (25), Mecânica/MAJ_NEG (17), Narrativa/NEG (19), Narrativa/NEU (8), Narrativa/MAJ_POS (3), Narrativa/DIV (2), Narrativa/MAJ_NEG (1), Estética/NEG (23), Estética/NEU (10), Estética/MAJ_POS (6), Estética/DIV (2), Estética/MAJ_NEG (2), Tecnologia/POS (16), Tecnologia/NEU (7), Tecnologia/DIV (3)

**Classes ausentes:** Tecnologia/MAJ_POS, Tecnologia/MAJ_NEG

## Tamanho do texto (palavras)

- média 84.1, mediana 38.0, p90 220.2, p99 556.1
- < 20 palavras: 116
- > 200 palavras: 44

## Quatro eixos = Não mencionado

- 92 reviews (23.1%)

## Split por jogo

- semente escolhida: 26 (menor desvio de distribuição)
- train 316 / val 0 / test 82 reviews
- jogos train/val/test: 17 / 0 / 4
