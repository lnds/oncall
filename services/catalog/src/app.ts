import { Hono, type Context } from "hono";
import type { ContentfulStatusCode } from "hono/utils/http-status";
import { z } from "zod";
import { DuplicateServiceError } from "./domain.js";
import { isoDate } from "./json.js";
import type { CatalogRepository } from "./repository.js";

const serviceInput = z.object({
  name: z.string().trim().min(1),
  team: z.string().trim().min(1),
  slo_target: z.number().gt(0).lte(100).default(99.9),
  sli_type: z.enum(["availability", "latency"]).default("availability"),
});

const shiftInput = z.object({
  service_id: z.number().int().positive(),
  person: z.string().trim().min(1),
  email: z.email(),
  start_date: z.iso.date(),
  end_date: z.iso.date(),
});

export interface AppOptions {
  /** La fecha de hoy como `YYYY-MM-DD`; se inyecta para poder fijarla en las pruebas. */
  today?: () => string;
}

function fail(c: Context, status: ContentfulStatusCode, error: string) {
  return c.json({ error }, status);
}

type Parsed<T> = { ok: true; data: T } | { ok: false; error: string };

async function readBody<T>(c: Context, schema: z.ZodType<T>): Promise<Parsed<T>> {
  let raw: unknown;
  try {
    raw = await c.req.json();
  } catch {
    return { ok: false, error: "request body must be valid JSON" };
  }
  const parsed = schema.safeParse(raw);
  if (!parsed.success) {
    const issue = parsed.error.issues[0]!;
    return { ok: false, error: `${issue.path.join(".") || "body"}: ${issue.message}` };
  }
  return { ok: true, data: parsed.data };
}

export function createApp(repo: CatalogRepository, options: AppOptions = {}) {
  const today = options.today ?? (() => isoDate(new Date()));
  const app = new Hono();

  app.get("/health", (c) => c.json({ status: "ok" }));

  app.get("/services", async (c) => c.json(await repo.listServices()));

  app.post("/services", async (c) => {
    const body = await readBody(c, serviceInput);
    if (!body.ok) return fail(c, 400, body.error);
    try {
      const id = await repo.createService(body.data);
      return c.json({ id }, 201);
    } catch (error) {
      if (error instanceof DuplicateServiceError) return fail(c, 409, error.message);
      throw error;
    }
  });

  app.get("/services/:id{[0-9]+}", async (c) => {
    const service = await repo.getService(Number(c.req.param("id")));
    return service ? c.json(service) : fail(c, 404, "service not found");
  });

  app.get("/oncall", async (c) => c.json(await repo.listShifts()));

  app.post("/oncall", async (c) => {
    const body = await readBody(c, shiftInput);
    if (!body.ok) return fail(c, 400, body.error);
    if (!(await repo.getService(body.data.service_id))) {
      return fail(c, 404, "service not found");
    }
    const id = await repo.createShift(body.data);
    return c.json({ id }, 201);
  });

  app.get("/oncall/current/:serviceId{[0-9]+}", async (c) => {
    const shift = await repo.currentShift(Number(c.req.param("serviceId")), today());
    return shift ? c.json(shift) : fail(c, 404, "no on-call for this service today");
  });

  app.notFound((c) => fail(c, 404, "not found"));

  app.onError((error, c) => {
    console.error(error);
    return fail(c, 500, "internal error");
  });

  return app;
}
