import { describe, expect, it } from "vitest";
import { currentShift, isActiveOn } from "../src/oncall.js";
import { setup } from "./helpers.js";

const shift = {
  id: 1,
  service_id: 1,
  person: "Ana Soto",
  email: "ana@example.com",
  start_date: "2026-10-01",
  end_date: "2026-10-31",
};

describe("isActiveOn", () => {
  it("cubre el primer día del turno", () => {
    expect(isActiveOn(shift, "2026-10-01")).toBe(true);
  });

  it("cubre un día intermedio", () => {
    expect(isActiveOn(shift, "2026-10-15")).toBe(true);
  });

  it("no cubre un día anterior al turno", () => {
    expect(isActiveOn(shift, "2026-09-30")).toBe(false);
  });
});

describe("currentShift", () => {
  it("devuelve undefined si no hay turnos", () => {
    expect(currentShift([], "2026-10-06")).toBeUndefined();
  });

  it("elige el turno vigente", () => {
    const old = { ...shift, id: 2, start_date: "2026-09-01", end_date: "2026-09-30" };
    expect(currentShift([old, shift], "2026-10-06")?.id).toBe(1);
  });
});

describe("POST /oncall", () => {
  it("crea un turno", async () => {
    const { post } = setup();
    await post("/services", { name: "checkout", team: "payments" });
    const res = await post("/oncall", { ...shift, id: undefined });
    expect(res.status).toBe(201);
  });

  it("responde 404 si el servicio no existe", async () => {
    const { post } = setup();
    const res = await post("/oncall", { ...shift, id: undefined });
    expect(res.status).toBe(404);
  });

  it("rechaza un correo inválido", async () => {
    const { post } = setup();
    await post("/services", { name: "checkout", team: "payments" });
    const res = await post("/oncall", { ...shift, id: undefined, email: "ana" });
    expect(res.status).toBe(400);
  });

  it("rechaza una fecha mal formada", async () => {
    const { post } = setup();
    await post("/services", { name: "checkout", team: "payments" });
    const res = await post("/oncall", { ...shift, id: undefined, start_date: "01-10-2026" });
    expect(res.status).toBe(400);
  });
});

describe("GET /oncall", () => {
  it("incluye el nombre del servicio", async () => {
    const { app, post } = setup();
    await post("/services", { name: "checkout", team: "payments" });
    await post("/oncall", { ...shift, id: undefined });
    const res = await app.request("/oncall");
    const shifts = await res.json();
    expect(shifts[0].service_name).toBe("checkout");
  });
});

describe("GET /oncall/current/:serviceId", () => {
  it("devuelve quien está de guardia hoy", async () => {
    const { app, post } = setup();
    await post("/services", { name: "checkout", team: "payments" });
    await post("/oncall", { ...shift, id: undefined });
    const res = await app.request("/oncall/current/1");
    expect(res.status).toBe(200);
    expect((await res.json()).person).toBe("Ana Soto");
  });

  it("responde 404 si nadie está de guardia", async () => {
    const { app, post } = setup();
    await post("/services", { name: "checkout", team: "payments" });
    const res = await app.request("/oncall/current/1");
    expect(res.status).toBe(404);
  });
});
