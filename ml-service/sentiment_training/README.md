# Treino de sentimento por eixo (Tétrade de Schell)

Pacote **isolado** do runtime da API Pixel Oracle. Nada aqui é importado por `main.py` / rotas.

## Decisões (Passo -1)

| Item | Encontrado no `ml-service` | O que fizemos |
|---|---|---|
| Python | 3.11 (Dockerfile `python:3.11-slim`) | Mesma versão |
| Deps da API | `requirements.txt` + torch CPU no Docker | **Não alterado.** Treino usa `requirements-training.txt` + venv `.venv-training/` |
| Organização | pacotes na raiz (`ml/`, `absa/`, `scripts/`) | Pasta nova `sentiment_training/` com `src/` + `scripts/` como pedido |
| Testes | `python scripts/test_pipeline.py` (sem pytest) | Testes novos no mesmo estilo (`python tests/test_*.py`) |
| Lint | sem ruff/black/mypy no repo | type hints + docstrings no estilo do serviço |
| Logging | `print` nos scripts; `logging` pontual | `logging` nos scripts de treino |
| Hugging Face | `neuralmind/bert-base-portuguese-cased` e `xlm-roberta-base` existem | nomes em `src/config.py` |

**Arquivo de dados:** ainda **não está no repositório**. Coloque `data/reviews_anotadas.xlsx` (aba `Reviews`) ou `data/reviews_anotadas.csv` (`;` / utf-8-sig).

## Instalação (não mistura com a API)

```bash
cd ml-service/sentiment_training
python3.11 -m venv .venv-training
source .venv-training/bin/activate
pip install -r requirements-training.txt
# GPU (opcional):
# pip install torch --index-url https://download.pytorch.org/whl/cu124
```

## Dados

Colunas mínimas: `game_id`, `texto`, `Mecânica`, `Narrativa`, `Estética`, `Tecnologia`.
Entrada do modelo: **somente `texto`**.

Rótulos vazios saem do treino. Valor fora do dicionário → `outputs/rotulos_invalidos.csv` e o script para.

## Como rodar

```bash
# 0) EDA + split por jogo (obrigatório antes do treino completo)
python scripts/run_eda.py

python scripts/run_eda.py --only-human
python scripts/run_eda.py --min-words 20 --test-human-only

# 1) smoke (valida pipeline; métricas não comparáveis)
python scripts/run_baseline.py --scheme 7 --smoke --drop-invalid
python scripts/run_transformer.py --model bertimbau --scheme 7 --smoke --drop-invalid
python scripts/run_transformer.py --model xlmr --scheme 7 --smoke --drop-invalid

# 2) 80% treino / 20% teste por game_id (val recortado do treino; < 300 rotuladas)
python scripts/run_eda.py --drop-invalid
python scripts/run_baseline.py --scheme 7 --drop-invalid --allow-small --force-split
python scripts/run_transformer.py --model bertimbau --scheme 7 --drop-invalid --allow-small
python scripts/run_transformer.py --model xlmr --scheme 7 --drop-invalid --allow-small
# depois: --scheme 5 e --scheme binary
```

## Interpretar resultados

- Métrica principal: **macro-F1 médio dos 4 eixos** no teste.
- `outputs/resultados.md` / `.csv`: comparação.
- `outputs/predicoes_*.csv`: ouro vs predição.
- `outputs/cm_*.png`: matrizes de confusão.
- Sem GPU o transformer avisa e deve rodar com `--smoke`.

## Testes

```bash
cd ml-service/sentiment_training
python tests/test_labels.py
python tests/test_split.py
python tests/test_metrics.py

cd ../
python scripts/test_pipeline.py   # testes JÁ existentes da API (não devem quebrar)
```
