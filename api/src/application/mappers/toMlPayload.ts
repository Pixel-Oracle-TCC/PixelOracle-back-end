import type { GamePitch, MlGamePayload } from "../../domain/entities/GamePitch.js";

export function toMlPayload(pitch: GamePitch): MlGamePayload {
  const { titulo: _t, descricao: _d, ...rest } = pitch;
  return rest;
}
