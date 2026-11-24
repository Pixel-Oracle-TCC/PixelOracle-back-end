# EDA — reviews anotadas (Tétrade de Schell)

- Arquivo: `reviews_anotadas.xlsx`
- SHA-256: `62858c46123f6389e0ab822890d89e1e1e0eb5d97e822aec2a7ff2f6142c1310`
- Linhas no arquivo: **4000**
- Sem nenhum eixo preenchido (removidas): **3001**
- Parcialmente preenchidas (removidas): **1**
- Rótulo inválido (não mapeado): **1**
- Removidas por MIN_WORDS: **0**
- Rotuladas usadas: **998**
- Jogos distintos (rotuladas): **55**

## Anotador

- `Claude`: 750
- `Grok`: 200
- `(vazio)`: 48

## Distribuição das 7 classes por eixo

### Mecânica

| Classe | n | % |
|---|---:|---:|
| POS | 334 | 33.5 |
| NEG | 123 | 12.3 |
| NEU | 25 | 2.5 |
| MAJ_POS | 52 | 5.2 |
| DIV | 69 | 6.9 |
| MAJ_NEG | 49 | 4.9 |
| NM | 346 | 34.7 |

### Narrativa

| Classe | n | % |
|---|---:|---:|
| POS | 156 | 15.6 |
| NEG | 29 | 2.9 |
| NEU | 12 | 1.2 |
| MAJ_POS | 6 | 0.6 |
| DIV | 5 | 0.5 |
| MAJ_NEG | 2 | 0.2 |
| NM | 788 | 79.0 |

### Estética

| Classe | n | % |
|---|---:|---:|
| POS | 261 | 26.2 |
| NEG | 36 | 3.6 |
| NEU | 12 | 1.2 |
| MAJ_POS | 11 | 1.1 |
| DIV | 5 | 0.5 |
| MAJ_NEG | 3 | 0.3 |
| NM | 670 | 67.1 |

### Tecnologia

| Classe | n | % |
|---|---:|---:|
| POS | 30 | 3.0 |
| NEG | 125 | 12.5 |
| NEU | 10 | 1.0 |
| MAJ_POS | 0 | 0.0 |
| DIV | 6 | 0.6 |
| MAJ_NEG | 0 | 0.0 |
| NM | 827 | 82.9 |

**Classes com menos de 30 exemplos:** Mecânica/NEU (25), Narrativa/NEG (29), Narrativa/NEU (12), Narrativa/MAJ_POS (6), Narrativa/DIV (5), Narrativa/MAJ_NEG (2), Estética/NEU (12), Estética/MAJ_POS (11), Estética/DIV (5), Estética/MAJ_NEG (3), Tecnologia/NEU (10), Tecnologia/DIV (6)

**Classes ausentes:** Tecnologia/MAJ_POS, Tecnologia/MAJ_NEG

## Tamanho do texto (palavras)

- média 78.8, mediana 35.0, p90 192.0, p99 633.5
- < 20 palavras: 315
- > 200 palavras: 96

## Quatro eixos = Não mencionado

- 251 reviews (25.2%)

## Split por jogo

- semente escolhida: 24 (menor desvio de distribuição)
- train 797 / val 0 / test 201 reviews
- jogos train/val/test: 45 / 0 / 10
