import { z } from "zod";

const isoDate = z.iso.date({ error: "Use o formato YYYY-MM-DD." });

export const releasesQuerySchema = z
  .object({
    from: isoDate,
    to: isoDate,
  })
  .superRefine((data, ctx) => {
    if (data.from > data.to) {
      ctx.addIssue({
        code: "custom",
        message: "A data inicial deve ser menor ou igual à data final.",
        path: ["from"],
      });
    }

    const from = new Date(`${data.from}T00:00:00.000Z`);
    const to = new Date(`${data.to}T00:00:00.000Z`);
    const maxTo = new Date(from);
    maxTo.setUTCFullYear(maxTo.getUTCFullYear() + 5);

    if (to > maxTo) {
      ctx.addIssue({
        code: "custom",
        message: "O intervalo máximo permitido é de 5 anos.",
        path: ["to"],
      });
    }
  });

export type ReleasesQuery = z.infer<typeof releasesQuerySchema>;

export type ValidationIssue = {
  campo: string;
  mensagem: string;
};

function firstQueryValue(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value[0];
  }
  return value;
}

export function parseReleasesQuery(query: unknown):
  | { success: true; data: ReleasesQuery }
  | { success: false; erros: ValidationIssue[] } {
  const raw =
    query && typeof query === "object"
      ? {
          from: firstQueryValue((query as Record<string, unknown>).from),
          to: firstQueryValue((query as Record<string, unknown>).to),
        }
      : query;

  const parsed = releasesQuerySchema.safeParse(raw);
  if (parsed.success) {
    return { success: true, data: parsed.data };
  }

  return {
    success: false,
    erros: parsed.error.issues.map((issue) => ({
      campo: issue.path.join(".") || "query",
      mensagem: issue.message,
    })),
  };
}
