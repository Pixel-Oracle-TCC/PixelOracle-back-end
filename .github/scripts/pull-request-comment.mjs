import fs from "node:fs";
import { pathToFileURL } from "node:url";

export function stripAnsi(text) {
  return text.replace(/\u001b\[[0-9;]*m/g, "");
}

function lastNumber(text, pattern) {
  const matches = [...text.matchAll(pattern)];
  if (matches.length === 0) return null;
  return Number(matches[matches.length - 1][1]);
}

export function summarizeTestLog(raw, format) {
  const log = stripAnsi(raw ?? "");
  if (!log.trim()) return { found: false, passed: null, failed: null };

  if (format === "node") {
    const passed = lastNumber(log, /^# pass (\d+)/gm) ?? lastNumber(log, /^ℹ pass (\d+)/gm);
    const failed = lastNumber(log, /^# fail (\d+)/gm) ?? lastNumber(log, /^ℹ fail (\d+)/gm);
    if (passed == null && failed == null) return { found: false, passed: null, failed: null };
    return { found: true, passed: passed ?? 0, failed: failed ?? 0 };
  }

  if (format === "vitest") {
    const lines = [...log.matchAll(/^\s*Tests\s+(.+)$/gm)];
    if (lines.length === 0) return { found: false, passed: null, failed: null };
    const line = lines[lines.length - 1][1];
    const both = line.match(/(\d+)\s+failed\s+\|\s+(\d+)\s+passed/);
    if (both) return { found: true, passed: Number(both[2]), failed: Number(both[1]) };
    const passedOnly = line.match(/(\d+)\s+passed/);
    const failedOnly = line.match(/(\d+)\s+failed/);
    if (!passedOnly && !failedOnly) return { found: false, passed: null, failed: null };
    return {
      found: true,
      passed: passedOnly ? Number(passedOnly[1]) : 0,
      failed: failedOnly ? Number(failedOnly[1]) : 0,
    };
  }

  if (format === "python") {
    const passed = lastNumber(log, /✅ (\d+) testes sintéticos OK/g);
    if (passed == null) return { found: false, passed: null, failed: null };
    return { found: true, passed, failed: 0 };
  }

  return { found: false, passed: null, failed: null };
}

export function labelOutcome(outcome) {
  if (outcome === "success") return "passou";
  if (outcome === "failure") return "falhou";
  if (!outcome || outcome === "skipped") return "não rodou";
  return outcome;
}

function testDetail(summary) {
  if (!summary?.found) return "Não li a contagem no log";
  return `${summary.passed} passaram, ${summary.failed} falharam`;
}

export function parseRows(text, summary) {
  if (!text?.trim()) return [];
  return text
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [stage, outcome, detail] = line.split("|");
      const clean = (detail ?? "").trim();
      return {
        stage: stage.trim(),
        outcome: (outcome ?? "").trim(),
        detail: clean === "tests" ? testDetail(summary) : clean,
      };
    });
}

export function renderSummary({ title, rows }) {
  return [
    `## ${title}`,
    "",
    "| Etapa | Resultado | Detalhe |",
    "|-------|-----------|---------|",
    ...rows.map((row) => `| ${row.stage} | ${labelOutcome(row.outcome)} | ${row.detail} |`),
    "",
  ].join("\n");
}

export function renderComment({ marker, check, summary, contractLabel, rows = [] }) {
  const tests = summary.found
    ? `${summary.passed} passaram, ${summary.failed} falharam`
    : "Não li a contagem no log";
  let contract = "Não deu para confirmar";
  if (summary.found && summary.failed === 0) contract = `Exercitado por \`${contractLabel}\``;
  if (summary.found && summary.failed > 0) contract = `Rodou (\`${contractLabel}\`), com falha`;

  const table = rows.length
    ? [
        "| Etapa | Resultado | Detalhe |",
        "|-------|-----------|---------|",
        ...rows.map((row) => `| ${row.stage} | ${labelOutcome(row.outcome)} | ${row.detail} |`),
      ]
    : [
        "| Check | Testes | Contrato `POST /api/report` |",
        "|-------|--------|------------------------------|",
        `| \`${check}\` | ${tests} | ${contract} |`,
      ];

  return [
    `<!-- ${marker} -->`,
    "## Validação no pull request",
    "",
    ...table,
    "",
    rows.length ? `Contrato \`POST /api/report\`: ${contract}` : "A aba Summary deste check guarda o quadro.",
    "",
  ].join("\n");
}

function headers(token) {
  return {
    Authorization: `Bearer ${token}`,
    Accept: "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
  };
}

async function findComment(owner, repo, number, marker, token) {
  const needle = `<!-- ${marker} -->`;
  for (let page = 1; page <= 5; page += 1) {
    const url = `https://api.github.com/repos/${owner}/${repo}/issues/${number}/comments?per_page=100&page=${page}`;
    const response = await fetch(url, { headers: headers(token) });
    if (!response.ok) throw new Error(`listar comentários falhou: ${response.status}`);
    const comments = await response.json();
    const found = comments.find((comment) => comment.body?.includes(needle));
    if (found) return found;
    if (comments.length < 100) return null;
  }
  return null;
}

async function publish(owner, repo, number, body, marker, token) {
  const existing = await findComment(owner, repo, number, marker, token);
  if (existing) {
    const response = await fetch(`https://api.github.com/repos/${owner}/${repo}/issues/comments/${existing.id}`, {
      method: "PATCH",
      headers: { ...headers(token), "Content-Type": "application/json" },
      body: JSON.stringify({ body }),
    });
    if (!response.ok) throw new Error(`atualizar comentário falhou: ${response.status}`);
    return "atualizado";
  }
  const response = await fetch(`https://api.github.com/repos/${owner}/${repo}/issues/${number}/comments`, {
    method: "POST",
    headers: { ...headers(token), "Content-Type": "application/json" },
    body: JSON.stringify({ body }),
  });
  if (!response.ok) throw new Error(`criar comentário falhou: ${response.status}`);
  return "criado";
}

async function main() {
  const logPath = process.env.CI_LOG;
  const raw = logPath && fs.existsSync(logPath) ? fs.readFileSync(logPath, "utf8") : "";
  const summary = summarizeTestLog(raw, process.env.CI_FORMAT);
  const rows = parseRows(process.env.CI_ROWS, summary);
  if (process.env.GITHUB_STEP_SUMMARY && rows.length) {
    fs.appendFileSync(
      process.env.GITHUB_STEP_SUMMARY,
      renderSummary({ title: process.env.CI_TITLE || "Validação", rows }),
    );
  }

  if (!process.env.CI_MARKER || process.env.GITHUB_EVENT_NAME !== "pull_request") return;

  const body = renderComment({
    marker: process.env.CI_MARKER,
    check: process.env.CI_CHECK,
    summary,
    contractLabel: process.env.CI_CONTRACT_LABEL,
    rows,
  });
  const event = JSON.parse(fs.readFileSync(process.env.GITHUB_EVENT_PATH, "utf8"));
  const [owner, repo] = process.env.GITHUB_REPOSITORY.split("/");
  const result = await publish(owner, repo, event.pull_request.number, body, process.env.CI_MARKER, process.env.GITHUB_TOKEN);
  console.log(`comentário ${result}`);
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch((error) => {
    console.error(error.message);
    process.exit(1);
  });
}
