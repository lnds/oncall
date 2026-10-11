---
paths:
  - "services/*/tests/**"
  - "services/notifications/*_test.go"
---

# Pruebas

- Corren sin Docker ni base de datos: usan el repositorio en memoria y dobles de los otros
  servicios.
- El tiempo se controla con el reloj falso de cada servicio, nunca con esperas.
- Cada criterio de aceptación de la spec tiene al menos una prueba que lo nombra.
- Una prueba que falla no se borra ni se debilita para que pase: se arregla el código o se
  reporta que la prueba está mal, con el motivo.
