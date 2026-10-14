#!/usr/bin/env bash
# PreToolUse: impide editar una migración que ya está en main.
set -euo pipefail

archivo=$(jq -r '.tool_input.file_path // empty')
case "$archivo" in
  */migrations/*.sql) ;;
  *) exit 0 ;;
esac

ruta=${archivo#"$CLAUDE_PROJECT_DIR"/}
if git -C "$CLAUDE_PROJECT_DIR" cat-file -e "main:$ruta" 2>/dev/null; then
  echo "$ruta ya está en main: una migración aplicada no se edita. Crea un archivo nuevo con el número siguiente, V<n>__<descripcion>.sql." >&2
  exit 2
fi
exit 0
