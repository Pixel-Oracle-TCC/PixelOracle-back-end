# Comparação — treino anterior vs reviews novas

Classificação da review nos quatro eixos da Tétrade (7 classes). Métrica principal: **macro-F1 médio dos 4 eixos** no teste. RMSE/MAE não se aplicam.

## Dados

| | Anterior (2026-11-03) | Atual (planilha 2026-11-08) |
| --- | ---: | ---: |
| Arquivo | `reviews_anotadas.xlsx` | `data/reviews_anotadas.xlsx` (hash `7ae9b1ec…`) |
| Rotuladas usadas | 148 | 398 |
| Jogos | 8 | 21 |
| Split por jogo | 116 treino / 32 teste (6 / 2 jogos) | 316 treino / 82 teste (17 / 4 jogos); val recortado do treino: 255 / 61 |
| Anotador | 100 Claude + 48 sem marca | 350 Claude + 48 sem marca |

Pré-processamento atual: nulos nos eixos e no texto saem; 1 rótulo inválido vai para `rotulos_invalidos.csv`; texto sem bytes de controle, tags HTML, URLs e espaços repetidos. Sem `steamid` nem endpoint de usuário.

O teste **não é o mesmo conjunto** das 148: há mais jogos e o par de jogos do teste mudou. A comparação é de protocolo (80/20 por jogo), não de linha a linha.

## Macro-F1 médio (teste)

| modelo | 148 rótulos | 398 rótulos (limpo) | Δ |
| --- | ---: | ---: | ---: |
| TF-IDF + LogReg | 0.2199 | 0.2105 | −0.0094 |
| BERTimbau | só `--smoke` | **0.2526** | — |
| XLM-RoBERTa | só `--smoke` | 0.2269 | — |

BERTimbau passa o baseline no teste novo (+0.042). XLM-R também passa o baseline (+0.016), abaixo do BERTimbau.

## Por eixo (398 rótulos, semente 13)

| modelo | Mecânica F1 / acc | Narrativa F1 / acc | Estética F1 / acc | Tecnologia F1 / acc |
| --- | --- | --- | --- | --- |
| baseline | 0.280 / 0.561 | 0.181 / 0.707 | 0.212 / 0.744 | 0.169 / 0.915 |
| bertimbau | 0.348 / 0.610 | 0.212 / 0.756 | 0.263 / 0.744 | 0.188 / 0.805 |
| xlmr | 0.349 / 0.659 | 0.188 / 0.683 | 0.206 / 0.707 | 0.165 / 0.841 |

Acurácia de Tecnologia e Narrativa sobe porque a maioria das reviews é `NM`. O macro-F1 mostra as classes raras.

## Baseline: 148 vs 398 (mesmo modelo)

| eixo | F1 148 | F1 398 | acc 148 | acc 398 |
| --- | ---: | ---: | ---: | ---: |
| Mecânica | 0.283 | 0.280 | 0.469 | 0.561 |
| Narrativa | 0.181 | 0.181 | 0.688 | 0.707 |
| Estética | 0.187 | 0.212 | 0.625 | 0.744 |
| Tecnologia | 0.228 | 0.169 | 0.875 | 0.915 |

Acurácia sobe; macro-F1 de Tecnologia cai no teste novo (mais `NM`, classes mistas quase ausentes).

## Artefatos

- Pesos: `checkpoints/baseline_7_seed13.joblib`, `checkpoints/bertimbau_7_seed13/best.pt` (época 5, val 0.223), `checkpoints/xlmr_7_seed13/best.pt` (época 10, val 0.217)
- Matrizes: `outputs/cm_<modelo>_7_13_<eixo>.png`
- Predições: `outputs/predicoes_<modelo>_7.csv`
- Tabela: `outputs/resultados.md`
