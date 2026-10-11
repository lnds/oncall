---
paths:
  - "services/*/migrations/*.sql"
---

# Migraciones

- Una migración aplicada no se edita. Todo cambio de esquema va en un archivo nuevo, con el número
  siguiente: `V<n>__<descripcion_en_snake_case>.sql`.
- SQL plano para Flyway, con una línea de comentario al inicio que diga para qué es.
- Las columnas nuevas de una tabla con datos llevan valor por defecto o aceptan `NULL`.
- Si la migración cambia lo que guarda un repositorio, actualiza también su implementación en
  memoria.
