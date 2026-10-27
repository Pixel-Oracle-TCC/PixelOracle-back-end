import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { parseGamePitch } from "./parseGamePitch.js";

const pitchValido = {
  titulo: "Eco do Abismo",
  descricao: "Metroidvania com mapa interligado e combate preciso.",
  genres: ["Indie", "Ação"],
};

describe("parseGamePitch", () => {
  it("aceita o pitch mínimo do formulário", () => {
    const pitch = parseGamePitch(pitchValido);
    assert.equal(pitch.titulo, "Eco do Abismo");
    assert.equal(pitch.descricao, pitchValido.descricao);
    assert.deepEqual(pitch.genres, ["Indie", "Ação"]);
    assert.equal(pitch.price_brl, undefined);
    assert.equal(pitch.top_k, undefined);
  });

  it("aceita aliases do contrato antigo", () => {
    const pitch = parseGamePitch({
      name: "  Eco  ",
      ideia: "Uma ideia com mais de dez caracteres.",
      description: "ignorada porque ideia vem primeiro",
      genres: ["RPG"],
    });
    assert.equal(pitch.titulo, "Eco");
    assert.equal(pitch.descricao, "Uma ideia com mais de dez caracteres.");
  });

  it("rejeita corpo vazio, descrição curta e gêneros ausentes", () => {
    assert.throws(() => parseGamePitch(null), /Body JSON inválido/);
    assert.throws(() => parseGamePitch({ ...pitchValido, titulo: "  " }), /titulo/);
    assert.throws(() => parseGamePitch({ ...pitchValido, descricao: "curta" }), /mínimo 10/);
    assert.throws(() => parseGamePitch({ ...pitchValido, genres: [] }), /genres/);
  });

  it("rejeita preço negativo e top_k fora de 1 a 20", () => {
    assert.throws(() => parseGamePitch({ ...pitchValido, price_brl: -1 }), /price_brl/);
    assert.throws(() => parseGamePitch({ ...pitchValido, top_k: 0 }), /top_k/);
    assert.throws(() => parseGamePitch({ ...pitchValido, top_k: 21 }), /top_k/);
  });

  it("guarda preço zero e top_k válido", () => {
    const pitch = parseGamePitch({ ...pitchValido, price_brl: 0, top_k: 5 });
    assert.equal(pitch.price_brl, 0);
    assert.equal(pitch.top_k, 5);
  });
});
