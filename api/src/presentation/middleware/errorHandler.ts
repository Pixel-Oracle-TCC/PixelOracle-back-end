import type { Request, Response, NextFunction } from "express";
import axios from "axios";

function axiosResponseBody(data: unknown): unknown {
  if (data === undefined || data === null) {
    return undefined;
  }
  if (typeof Buffer !== "undefined" && Buffer.isBuffer(data)) {
    const text = data.toString("utf8");
    try {
      return JSON.parse(text) as unknown;
    } catch {
      return text;
    }
  }
  if (data instanceof ArrayBuffer) {
    const text = Buffer.from(data).toString("utf8");
    try {
      return JSON.parse(text) as unknown;
    } catch {
      return text;
    }
  }
  return data;
}

export function errorHandler(
  err: unknown,
  _req: Request,
  res: Response,
  _next: NextFunction
) {
  if (axios.isAxiosError(err)) {
    const status = err.response?.status ?? 502;
    const body = axiosResponseBody(err.response?.data);
    const detail =
      body && typeof body === "object" && "detail" in body
        ? (body as { detail: unknown }).detail
        : (body ?? err.message);
    res.status(status).json({
      status: "erro",
      origem: "ml-service",
      mensagem: detail,
    });
    return;
  }

  const message = err instanceof Error ? err.message : "Erro interno";
  const cause =
    err instanceof Error && err.cause instanceof Error
      ? err.cause.message
      : "";

  if (message.includes("GoogleGenerativeAI") || message.includes("generativelanguage")) {
    const quota =
      /quota|429|rate.?limit|exceeded/i.test(`${message} ${cause}`);
    res.status(quota ? 429 : 502).json({
      status: "erro",
      origem: "gemini",
      mensagem: quota
        ? "Cota da API Gemini esgotada ou indisponível no plano gratuito. Verifique https://aistudio.google.com/apikey (billing, nova chave ou outro modelo)."
        : `Falha ao contactar o Gemini: ${message}`,
    });
    return;
  }

  res.status(500).json({ status: "erro", mensagem: message });
}
