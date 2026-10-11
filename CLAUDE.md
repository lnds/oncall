# Oncall

Plataforma de gestión de incidentes. Tres servicios independientes en `services/`, cada uno con
su lenguaje y su base de datos; se hablan por HTTP con JSON.

## Dónde está cada cosa

- `docs/dominio.md`: las reglas del negocio. Si el código las contradice, el defecto está en el
  código.
- `docs/arquitectura.md`: el contrato de la API de cada servicio. Si cambias una ruta o un campo,
  actualízalo en el mismo commit.
- `docs/specs/`: una spec por tarea. Sin spec no se implementa.
- `BACKLOG.md`: lo pendiente, sin especificar.

## Verificar

Corre solo lo del servicio que tocaste, desde su carpeta. Las pruebas no necesitan Docker ni base
de datos.

| Servicio | Lint | Pruebas |
|---|---|---|
| `services/incidents` | `uv run ruff check . && uv run ruff format --check .` | `uv run pytest` |
| `services/catalog` | `npm run lint` | `npm test` |
| `services/notifications` | `go vet ./... && gofmt -l .` (no debe listar nada) | `go test ./...` |

`make check` corre todo, igual que la CI. Una tarea no está terminada hasta que el lint y las
pruebas del servicio pasan, y el informe final incluye su salida.

## Reglas

- Un servicio no lee la base de otro ni importa su código: se piden los datos por HTTP.
- Cada repositorio tiene una implementación en memoria para las pruebas. Las dos se comportan
  igual: si cambias una, cambia la otra.
- La hora sale del reloj inyectado (`clock`), nunca de `datetime.now()` ni `Date.now()` directos.
- No agregues dependencias sin preguntar.
- No reformatees ni refactorices lo que la tarea no pide.

## Reglas por tema

Viven en `.claude/rules/`. Las que tienen `paths` se cargan solo al tocar esos archivos.

- `git.md`: commits y ramas. Siempre.
- `pruebas.md`: al tocar `services/*/tests/`.
- `migraciones.md`: al tocar `services/*/migrations/`.

El procedimiento para verificar una rama está en la skill `verificar`; los permisos, en
`.claude/settings.json`.
