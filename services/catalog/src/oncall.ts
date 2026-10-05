import type { Shift } from "./domain.js";

/**
 * Indica si el turno está vigente en `day`. Las fechas `YYYY-MM-DD` se pueden
 * comparar como texto porque el orden lexicográfico coincide con el cronológico.
 */
export function isActiveOn(shift: Shift, day: string): boolean {
  return shift.start_date <= day && day < shift.end_date;
}

/** El turno vigente en `day`; si hay más de uno, el que se registró primero. */
export function currentShift<T extends Shift>(shifts: readonly T[], day: string): T | undefined {
  return shifts
    .filter((shift) => isActiveOn(shift, day))
    .sort((a, b) => a.id - b.id)[0];
}
