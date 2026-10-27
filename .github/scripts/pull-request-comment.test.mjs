import assert from "node:assert/strict";
import test from "node:test";
import { renderComment, summarizeTestLog } from "./pull-request-comment.mjs";

test("lê a contagem TAP do node:test", () => {
  const log = "ok 1 - pitch válido\n# tests 5\n# pass 5\n# fail 0\n";
  assert.deepEqual(summarizeTestLog(log, "node"), { found: true, passed: 5, failed: 0 });
});

test("lê a contagem do reporter spec", () => {
  const log = "✔ pitch válido\nℹ tests 5\nℹ pass 5\nℹ fail 0\n";
  assert.deepEqual(summarizeTestLog(log, "node"), { found: true, passed: 5, failed: 0 });
});

test("lê a linha do Vitest com falha", () => {
  const log = " Test Files  1 failed | 1 passed (2)\n      Tests  2 failed | 5 passed (7)\n";
  assert.deepEqual(summarizeTestLog(log, "vitest"), { found: true, passed: 5, failed: 2 });
});

test("ignora cor de terminal", () => {
  const log = "\u001b[32m      Tests  7 passed (7)\u001b[0m\n";
  assert.deepEqual(summarizeTestLog(log, "vitest"), { found: true, passed: 7, failed: 0 });
});

test("log vazio não inventa número", () => {
  assert.deepEqual(summarizeTestLog("", "node"), { found: false, passed: null, failed: null });
});

test("monta a tabela do contrato quando tudo passa", () => {
  const body = renderComment({
    marker: "pixel-oracle-ci:api",
    check: "api",
    summary: { found: true, passed: 5, failed: 0 },
    contractLabel: "parseGamePitch",
  });
  assert.match(body, /<!-- pixel-oracle-ci:api -->/);
  assert.match(body, /5 passaram, 0 falharam/);
  assert.match(body, /Exercitado por `parseGamePitch`/);
});

test("marca falha sem esconder que o contrato rodou", () => {
  const body = renderComment({
    marker: "pixel-oracle-ci:frontend",
    check: "test",
    summary: { found: true, passed: 5, failed: 2 },
    contractLabel: "mapFormToGamePitch",
  });
  assert.match(body, /Rodou \(`mapFormToGamePitch`\), com falha/);
});
