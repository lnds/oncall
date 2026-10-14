#!/usr/bin/env bash
# Stop: no deja terminar mientras fallen las pruebas de un servicio que cambió.
set -uo pipefail

entrada=$(cat)
# Si el agente ya está corrigiendo por este hook, lo deja terminar para no entrar en un ciclo.
[ "$(jq -r '.stop_hook_active // false' <<<"$entrada")" = "true" ] && exit 0

cd "$CLAUDE_PROJECT_DIR"
servicios=$({ git diff --name-only main...HEAD; git status --porcelain | cut -c4-; } |
  sed -n 's#^services/\([^/]*\)/.*#\1#p' | sort -u)
[ -z "$servicios" ] && exit 0

fallas=""
for servicio in $servicios; do
  case "$servicio" in
    incidents) comando="uv run pytest -q" ;;
    catalog) comando="npm test --silent" ;;
    notifications) comando="go test ./..." ;;
    *) continue ;;
  esac
  if ! salida=$(cd "services/$servicio" && $comando 2>&1); then
    fallas+="== services/$servicio: $comando"$'\n'"$(tail -n 30 <<<"$salida")"$'\n'
  fi
done

if [ -n "$fallas" ]; then
  printf 'Las pruebas fallan, así que la tarea no está terminada. Corrígelas antes de cerrar:\n%s' "$fallas" >&2
  exit 2
fi
exit 0
