import { describe, expect, it } from "vitest";
import { setup } from "./helpers.js";

describe("GET /health", () => {
  it("responde ok", async () => {
    const { app } = setup();
    const res = await app.request("/health");
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ status: "ok" });
  });
});

describe("POST /services", () => {
  it("crea un servicio", async () => {
    const { post } = setup();
    const res = await post("/services", { name: "checkout", team: "payments" });
    expect(res.status).toBe(201);
    const body = await res.json();
    expect(body.id).toBeDefined();
  });

  it("usa los valores por defecto del SLO", async () => {
    const { app, post } = setup();
    await post("/services", { name: "checkout", team: "payments" });
    const res = await app.request("/services/1");
    const service = await res.json();
    expect(service.slo_target).toBe(99.9);
    expect(service.sli_type).toBe("availability");
  });

  it("rechaza un servicio sin equipo", async () => {
    const { post } = setup();
    const res = await post("/services", { name: "checkout" });
    expect(res.status).toBe(400);
  });

  it("rechaza un tipo de SLI desconocido", async () => {
    const { post } = setup();
    const res = await post("/services", { name: "checkout", team: "payments", sli_type: "uptime" });
    expect(res.status).toBe(400);
  });

  it("rechaza un cuerpo que no es JSON", async () => {
    const { app } = setup();
    const res = await app.request("/services", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{name",
    });
    expect(res.status).toBe(400);
    expect((await res.json()).error).toBeDefined();
  });

  it("responde 409 si el nombre ya existe", async () => {
    const { post } = setup();
    await post("/services", { name: "checkout", team: "payments" });
    const res = await post("/services", { name: "checkout", team: "otro" });
    expect(res.status).toBe(409);
  });
});

describe("GET /services", () => {
  it("lista los servicios ordenados por nombre", async () => {
    const { app, post } = setup();
    await post("/services", { name: "search", team: "discovery" });
    await post("/services", { name: "checkout", team: "payments" });
    const res = await app.request("/services");
    const services = await res.json();
    expect(services).toHaveLength(2);
    expect(services[0].name).toBe("checkout");
  });
});

describe("GET /services/:id", () => {
  it("devuelve el servicio", async () => {
    const { app, post } = setup();
    await post("/services", { name: "checkout", team: "payments", slo_target: 99.95 });
    const res = await app.request("/services/1");
    expect(res.status).toBe(200);
    const service = await res.json();
    expect(service.name).toBe("checkout");
    expect(service.created_at).toMatch(/Z$/);
  });

  it("responde 404 si no existe", async () => {
    const { app } = setup();
    const res = await app.request("/services/99");
    expect(res.status).toBe(404);
  });
});
