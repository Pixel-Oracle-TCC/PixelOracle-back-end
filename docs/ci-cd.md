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

GitFlow adaptado, igual nos dois repositórios. `develop` é a branch de integração. Os workflows já aceitam `develop` e `main`.

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

Disparo: pull request e push em `develop` e `main`. Uma execução nova cancela a anterior do mesmo ref. O nome da execução leva o número do pull request, ou o nome da branch. Permissão dos workflows: leitura do código. O job `api` também pode escrever o comentário no pull request.

### Frontend (`Pixel-Oracle-FrontEnd/.github/workflows/ci.yml`)

Checks: `test`, `build`, `audit`, `secrets`.

- Node 22, `npm ci`
- `npm test -- --watch=false` (app, formulário de pitch e formatadores)
- `npm run build` (o typecheck acontece no build)
- `npm audit --audit-level=critical`
- Gitleaks em todo PR e nos pushes de `develop` e `main`

A aba Summary de cada check é um quadro de passou ou falhou. O job `relatório` junta os quatro. O check `test` comenta no pull request a contagem e se `mapFormToGamePitch` exercitou o `POST /api/report`. O selo do workflow fica no README. Os quatro checks são os que a trava de merge usaria; no plano gratuito de organização, com repositório privado, o GitHub não aplica essa trava.

O `package.json` do frontend fixa `piscina` em 5.3.2 (`overrides`). O `@angular/build` 21.2.8 puxava 5.1.4, que o audit marca como crítica. Avisos high continuam fora desse gate.

Não há ESLint. Prettier não é gate: o repositório ainda não está formatado por inteiro.

### API, ML, Compose e segredos (`.github/workflows/ci.yml`)

Um workflow só. O grafo começa em `mudanças` e termina em `relatório`. O job que o diff não toca fica como "não rodou" e não derruba o pipeline.

- `api`: Node 20, igual ao `api/Dockerfile`. `npm test` de `parseGamePitch`, typecheck, build, audit crítico e `docker build`. Roda com mudança em `api/**`, no script do comentário ou no próprio workflow. Comenta no pull request a contagem e se o contrato de `POST /api/report` foi exercitado. O quadro fica na aba Summary.
- `ml`: Python 3.11, `pip install -r ml-service/requirements-ci.txt` (numpy, pandas, scipy, scikit-learn, requests) e `python scripts/test_pipeline.py`. Roda com mudança em `ml-service/**` ou no workflow. `requirements-ci.txt` deixa Torch e `sentence-transformers` de fora. O pin de `scikit-learn` acompanha `requirements.txt`.
- `compose`: `docker compose config` quando mudam `docker-compose.yml` ou os Dockerfiles. Não constrói a imagem do ML.
- `secrets`: todo PR e todo push em `develop` e `main`. O binário aberto do Gitleaks 8.30.1 varre o histórico do git. A action oficial pede licença em repositório de organização (`Pixel-Oracle-TCC`), então o workflow não usa ela.

O selo único do workflow fica no README.

A chave que chegou a entrar em `api/.env.example` foi apagada do histórico. O exemplo segue sem valor. Se aquela chave ainda estiver ativa no Google AI Studio, revogue.

Dependabot (`.github/dependabot.yml`) abre PR semanal de npm em `api/`, pip em `ml-service/` e GitHub Actions. Updates minor e patch vão agrupados.

## Pull request

Os dois repositórios têm `.github/PULL_REQUEST_TEMPLATE.md`. Ao abrir um PR pela interface do GitHub, a descrição já vem em português, com o que muda, como validar e o checklist. O histórico do que entrou em cada entrega está no `CHANGELOG.md` de cada repo.

## Branch protection

A regra desejada, quando o GitHub passar a aplicá-la:

- Frontend: `test`, `build`, `audit`, `secrets`.
- Backend: só `secrets`. `api`, `ml` e `compose` ficam de fora, porque num pull request que não mexe neles o job aparece como "não rodou".

Os dois repositórios são privados e a organização está no plano gratuito. O GitHub mostra que a regra não é aplicada até a organização ir para o plano Team, ou até o repositório ficar público. Por isso o botão de merge ainda não trava.

## Entrega da coleta

O pull request continua só no CI. A máquina de coleta é outra execução, o workflow `Entrega da coleta` (`.github/workflows/deploy-coleta.yml`).

Dois momentos, fáceis de mostrar no Actions:

1. **Empacota.** Sempre. Valida o `docker-compose.collect.yml` e constrói a imagem enxuta (`ml-service/Dockerfile.collect`). Essa imagem não tem Torch e não chama a Gemini.
2. **Publica.** Envia o código para a EC2 e sobe o Postgres. Um push em `develop` que mexe na coleta (`ml-service/collection/`, scripts de coleta, migrations, compose ou o próprio workflow) publica sozinho. O botão **Run workflow** publica e ainda coleta o número de jogos pedido (o padrão do botão é 1, para a aula terminar na hora).

Sem o secret `DEV_HOST`, o job `publica` fica verde e o quadro diz que a máquina ainda não foi ligada. A imagem mesmo assim foi empacotada.

Secrets no repositório, nunca no git: `DEV_HOST`, `DEV_USER`, `DEV_SSH_KEY`, `DEV_SSH_KNOWN_HOSTS`, `POSTGRES_PASSWORD`, `STEAM_API_KEY`.

Na EC2 o Postgres escuta só em `127.0.0.1:5432`. Do notebook: `ssh -L 5433:127.0.0.1:5432 <usuário>@<host>` e `DATABASE_URL` em `localhost:5433`. A API e a Gemini continuam locais.

Homologação, produção e o frontend publicado continuam de fora. O GitHub Free da organização privada segue sem travar o merge.
