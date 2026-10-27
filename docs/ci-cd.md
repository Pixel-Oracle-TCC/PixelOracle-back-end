# CI/CD e ambientes

Contrato de integração e entrega do Pixel Oracle. O CI abaixo já roda no GitHub Actions. O CD (deploy em DEV, homologação e produção) está definido aqui e ainda não está ligado a nenhuma nuvem.

O manual da disciplina fala em monorepo, serviço de IA separado e rota `/predict`. O código real é outro, e os pipelines seguem o código.

| Manual | Código |
|--------|--------|
| `apps/frontend` | Repositório [Pixel-Oracle-FrontEnd](https://github.com/Pixel-Oracle-TCC/Pixel-Oracle-FrontEnd) |
| `apps/api` | `api/` neste repositório (Express, porta 3000) |
| `services/ml` | `ml-service/` (FastAPI, porta 8000) |
| `services/ia-generativa` | Gemini dentro da API (`api/src`). Sem pipeline próprio |
| `data/` | Migrations e scripts em `ml-service/`. Sem workflow separado |
| `POST /predict` | `GET /api/health` e `POST /api/report` |

## Branches

GitFlow adaptado, igual nos dois repositórios. `develop` ainda precisa ser criada a partir de `main` no GitHub; os workflows já aceitam essa branch.

| Branch | Papel |
|--------|--------|
| `main` | Produção. Recebe só merge de `release/*` ou `hotfix/*`, com tag SemVer (`v1.2.0`). |
| `develop` | Integração do time. Espelha o ambiente DEV. |
| `feature/<escopo>` | Uma história. Abre PR para `develop`. |
| `release/<versao>` | Congelamento para homologação. PR para `main` e merge de volta em `develop`. |
| `hotfix/<descricao>` | Correção a partir de `main`. Depois, backport para `develop` e para a `release/*` aberta. |
| `chore/*`, `docs/*` | Tooling, CI ou documentação, sem regra de negócio. |

Não há push direto em `main` nem em `develop`. O autor do PR não aprova o próprio merge.

## Ambientes

Quando o CD existir, cada ambiente terá frontend estático, container da API, container do ML e Postgres com pgvector. `GEMINI_API_KEY` e `STEAM_API_KEY` ficam nos secrets do ambiente no GitHub, nunca no git.

| Ambiente | Origem | Gatilho futuro | Deploy |
|----------|--------|----------------|--------|
| DEV | `develop` | Push em `develop` | Automático (`deploy-dev`) |
| HMG | `release/*` | CI verde na release | Automático (`deploy-hmg`) |
| PROD | `main` + tag `vMAJOR.MINOR.PATCH` | Aprovação do responsável da release | Semi-automático (`deploy-prod`) |

- DEV não pede aprovação. O `apiUrl` do frontend aponta para a API de DEV e `useMockApi` fica desligado.
- HMG serve o checklist da sprint: pitch em `/analisar` até o relatório (`POST /api/report`).
- PROD usa um GitHub Environment `prod` com revisor obrigatório. Migration de banco só depois de backup.
- A imagem Docker do ML (Torch CPU) entra no deploy de DEV e HMG, não no CI de pull request.

Antes desse CD, o frontend precisa de um `apiUrl` por ambiente. Hoje `src/environments/environment.ts` e `environment.development.ts` apontam os dois para `http://localhost:3000`.

Feature flags do manual (`ff_recomendacoes_generativas` e similares) ficam para uma etapa seguinte. Sem `GEMINI_API_KEY`, a narrativa da API já cai no fallback.

## O que o CI faz hoje

Disparo: pull request e push em `develop` e `main`. Uma execução nova cancela a anterior do mesmo ref. Permissão dos workflows: só leitura do código.

### Frontend (`Pixel-Oracle-FrontEnd/.github/workflows/ci.yml`)

Checks: `test`, `build`, `audit`, `secrets`.

- Node 22, `npm ci`
- `npm test -- --watch=false` (app, formulário de pitch e formatadores)
- `npm run build` (o typecheck acontece no build)
- `npm audit --audit-level=critical`
- Gitleaks em todo PR e nos pushes de `develop` e `main`

O resumo dos testes fica na aba Summary do check `test`.

O `package.json` do frontend fixa `piscina` em 5.3.2 (`overrides`). O `@angular/build` 21.2.8 puxava 5.1.4, que o audit marca como crítica. Avisos high continuam fora desse gate.

Não há ESLint. Prettier não é gate: o repositório ainda não está formatado por inteiro.

### API (`.github/workflows/ci-api.yml`)

Check: `api`. Só roda se o PR ou o push mexer em `api/**` (ou no próprio workflow).

- Node 20, igual ao `api/Dockerfile`
- `npm test` — testes unitários de `parseGamePitch`
- `npm run typecheck`, `npm run build`, `npm audit --audit-level=critical`
- `docker build` da API

O resumo dos testes fica na aba Summary do check `api`.

### ML (`.github/workflows/ci-ml.yml`)

Check: `ml`. Só roda se mexer em `ml-service/**`.

- Python 3.11
- `pip install -r ml-service/requirements-ci.txt` (numpy, pandas, scipy, scikit-learn, requests)
- `python scripts/test_pipeline.py`

O resumo fica na aba Summary do check `ml`. `requirements-ci.txt` deixa Torch e `sentence-transformers` de fora. O pin de `scikit-learn` acompanha `requirements.txt`.

### Compose (`.github/workflows/ci-compose.yml`)

Check: `compose`. Roda quando mudam `docker-compose.yml` ou os Dockerfiles. `docker compose config` valida o arquivo e não constrói a imagem do ML.

### Segredos (`.github/workflows/security.yml`)

Check: `secrets`. Roda em todo PR e nos pushes de `develop` e `main`, sem filtro de pasta. O binário aberto do Gitleaks 8.30.1 varre o histórico do git. A action oficial pede licença em repositório de organização (`Pixel-Oracle-TCC`), então o workflow não usa ela.

A chave que chegou a entrar em `api/.env.example` foi apagada do histórico. O exemplo segue sem valor. Se aquela chave ainda estiver ativa no Google AI Studio, revogue.

Dependabot (`.github/dependabot.yml`) abre PR semanal de npm em `api/`, pip em `ml-service/` e GitHub Actions. Updates minor e patch vão agrupados.

## Pull request

Os dois repositórios têm `.github/PULL_REQUEST_TEMPLATE.md`. Ao abrir um PR pela interface do GitHub, a descrição já vem em português, com o que muda, como validar e o checklist. O histórico do que entrou em cada entrega está no `CHANGELOG.md` de cada repo.

## Branch protection

No GitHub, em `main` e `develop`: PR obrigatório, uma aprovação de outra pessoa, conversa resolvida.

Checks que podem ser obrigatórios sem travar PR alheio à pasta:

- Frontend: `test`, `build`, `audit`, `secrets` (o workflow sempre roda).
- Backend: `secrets` (sempre roda).

`api`, `ml` e `compose` usam filtro de caminho. Se forem marcados como obrigatórios, um PR que não dispara o workflow fica esperando um check que não existe. Só exija esses três se a regra do repositório tratar workflow ignorado como sucesso.

## O que fica para o CD

Ainda não há `deploy-dev.yml`, `deploy-hmg.yml` nem `deploy-prod.yml`, nem VPS ou plataforma gerenciada.

Quando for a hora:

1. `apiUrl` (e `useMockApi: false`) por ambiente no frontend.
2. GitHub Environments `dev`, `hmg` e `prod`, com reviewers só em `prod`.
3. Build e publicação das imagens da API e do ML. A do ML inclui o Torch CPU e não deve rodar em todo PR.
4. Postgres com volume, migrations versionadas e backup antes de aplicar em produção.
5. Smoke depois do deploy: `GET /api/health` e um `POST /api/report` de fixture em DEV e HMG.
