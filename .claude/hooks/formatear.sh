#!/usr/bin/env bash
# PostToolUse: formatea el archivo recién editado con el formateador de su servicio.
set -euo pipefail

archivo=$(jq -r '.tool_input.file_path // empty')
[ -n "$archivo" ] && [ -f "$archivo" ] || exit 0

case "$archivo" in
  */services/incidents/*.py)
    cd "$CLAUDE_PROJECT_DIR/services/incidents" && uv run --quiet ruff format --quiet "$archivo"
    ;;
  */services/notifications/*.go)
    gofmt -w "$archivo"
    ;;
esac
exit 0
