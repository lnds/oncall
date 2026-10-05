import {
  DuplicateServiceError,
  type NewService,
  type NewShift,
  type Service,
  type Shift,
  type ShiftWithService,
} from "./domain.js";
import { isoInstant } from "./json.js";
import { currentShift } from "./oncall.js";
import type { CatalogRepository } from "./repository.js";

/** Repositorio en memoria, con la misma semántica que el de Postgres. */
export class MemoryCatalogRepository implements CatalogRepository {
  private services: Service[] = [];
  private shifts: Shift[] = [];

  constructor(private readonly clock: () => Date = () => new Date()) {}

  async listServices(): Promise<Service[]> {
    return [...this.services].sort((a, b) => a.name.localeCompare(b.name));
  }

  async createService(service: NewService): Promise<number> {
    if (this.services.some((s) => s.name === service.name)) {
      throw new DuplicateServiceError(service.name);
    }
    const id = this.services.length + 1;
    this.services.push({ id, ...service, created_at: isoInstant(this.clock()) });
    return id;
  }

  async getService(id: number): Promise<Service | undefined> {
    return this.services.find((s) => s.id === id);
  }

  async listShifts(): Promise<ShiftWithService[]> {
    return this.shifts
      .map((shift) => ({
        ...shift,
        service_name: this.services.find((s) => s.id === shift.service_id)?.name ?? "",
      }))
      .sort((a, b) => b.start_date.localeCompare(a.start_date) || b.id - a.id);
  }

  async createShift(shift: NewShift): Promise<number> {
    const id = this.shifts.length + 1;
    this.shifts.push({ id, ...shift });
    return id;
  }

  async currentShift(serviceId: number, day: string): Promise<Shift | undefined> {
    return currentShift(
      this.shifts.filter((s) => s.service_id === serviceId),
      day,
    );
  }
}
