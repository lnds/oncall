---
name: verificar
description: Corre el lint y las pruebas de los servicios de Oncall que cambiaron en la rama y
  reporta la salida. Úsala antes de dar una tarea por terminada o de hacer commit.
allowed-tools: Bash(git status *), Bash(git diff *), Bash(uv run *), Bash(npm run lint), Bash(npm test), Bash(go vet *), Bash(go test *), Bash(gofmt -l *)
---

# Verificar lo que cambió

Archivos que cambiaron respecto de `main`:

!`git diff --name-only main...HEAD; git status --porcelain`

1. De esa lista, deduce qué servicios de `services/` cambiaron. Si solo cambió documentación,
   dilo y termina.
2. Para cada servicio que cambió, corre desde su carpeta el lint y después las pruebas:

   | Servicio | Lint | Pruebas |
   |---|---|---|
   | `incidents` | `uv run ruff check . && uv run ruff format --check .` | `uv run pytest` |
   | `catalog` | `npm run lint` | `npm test` |
   | `notifications` | `go vet ./... && gofmt -l .` | `go test ./...` |

   `gofmt -l .` no debe listar ningún archivo.
3. No corrijas nada. Si algo falla, reporta y detente.

Responde solo con esto:

```text
Servicios verificados: <lista>
Lint: <pasa | falla>, con la salida si falla
Pruebas: <n pasan, n fallan>, con la salida de las que fallan
Veredicto: LISTO | NO LISTO
```
