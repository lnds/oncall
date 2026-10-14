---
name: pr
description: Abre el pull request de la rama actual, con la descripción armada desde su spec y el
  resultado de la verificación.
argument-hint: "[nota para quien revisa]"
disable-model-invocation: true
allowed-tools: Bash(git status *), Bash(git diff *), Bash(git log *), Bash(gh pr view *)
---

# Abrir el pull request

Rama: !`git branch --show-current`

Commits respecto de `main`:

!`git log --oneline main..HEAD`

Specs que tocó la rama:

!`git diff --name-only main...HEAD -- docs/specs/`

1. Si hay cambios sin commit, detente y dilo.
2. Invoca la skill `verificar`. Si el veredicto es NO LISTO, detente y muestra qué falló.
3. Si `gh pr view` muestra que la rama ya tiene un PR abierto, entrega su enlace y termina.
4. Sube la rama con `git push -u origin HEAD`.
5. Crea el PR con `gh pr create --base main`:
   - Título: lo que cambia, en una línea, en español.
   - Cuerpo: el objetivo de la spec en dos frases; la lista de criterios de aceptación cubiertos,
     cada uno con la prueba que lo nombra; el bloque de salida de `verificar`; y al final, si la
     hay, esta nota para quien revisa: $ARGUMENTS
   - Sin atribuciones a herramientas.
6. Responde solo con el enlace del PR.
