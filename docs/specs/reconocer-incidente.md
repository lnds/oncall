# Reconocer un incidente

## Objetivo

Quien está de guardia puede decir «lo vi, me hago cargo» sobre un incidente sin cambiar su estado.
Queda registrado quién lo reconoció y cuándo, para saber cuánto tardó cada persona en reconocer
cada incidente.

## Contexto

- Historia 1 de `BACKLOG.md`.
- Todo ocurre en `services/incidents`: la API (`api.py`), las reglas (`domain.py`), la
  persistencia (`repository.py`, `memory.py`, `migrations/`) y la interfaz web (`static/`).
- El ciclo de vida y las reglas del incidente están en `docs/dominio.md`. El contrato de la API,
  en `docs/arquitectura.md`.

## Decisiones fijadas

- Reconocer **no es un estado**. No se agrega nada a `Status` ni a la tabla de transiciones.
- El reconocimiento se guarda en el incidente: quién y cuándo. La hora la pone el servidor.
- Un incidente se reconoce **una sola vez**. El primero que lo reconoce queda registrado.
- Reconocer deja una entrada en la bitácora.

## Lo que sí / lo que no

**Sí:** la operación de reconocer en la API, los dos campos nuevos en el incidente, su migración,
el botón en el detalle del incidente y la indicación de quién lo reconoció y cuánto tardó.

**No:** avisar a nadie al reconocer, escalar si nadie reconoce (historia 2), calcular el MTTA
(historia 3), ni cambiar lo que pasa con el reconocimiento cuando un incidente se reabre.

## Criterios de aceptación

**EARS**

1. Cuando alguien reconoce un incidente no reconocido, el sistema debe guardar quién lo reconoció
   y la hora del servidor, sin cambiar el estado del incidente.
2. Cuando se reconoce un incidente, el sistema debe agregar a la bitácora una entrada con el autor
   del reconocimiento.
3. Si el incidente ya fue reconocido, entonces el sistema debe rechazar el nuevo reconocimiento con
   `409` y mantener el registro original.
4. Si el incidente está resuelto, entonces el sistema debe rechazar el reconocimiento con `409`.
5. Si el incidente no existe, entonces el sistema debe responder `404`.
6. Si falta quién reconoce, entonces el sistema debe responder `400`.
7. Mientras un incidente no esté reconocido ni resuelto, la interfaz debe ofrecer el botón
   «Reconocer» en su detalle.
8. Mientras un incidente esté reconocido, la interfaz debe mostrar quién lo reconoció y cuánto
   tardó desde el inicio del incidente.

**Gherkin**

```gherkin
# language: es
Característica: Reconocer un incidente

  Escenario: la persona de guardia reconoce un incidente abierto
    Dado un incidente SEV2 abierto a las 10:00 en checkout
    Cuando Ana Soto lo reconoce a las 10:07
    Entonces el incidente sigue en estado "open"
    Y figura reconocido por Ana Soto a las 10:07
    Y la bitácora tiene la entrada del reconocimiento con autor Ana Soto

  Escenario: un segundo reconocimiento no pisa el primero
    Dado un incidente reconocido por Ana Soto a las 10:07
    Cuando Pedro Rojas intenta reconocerlo a las 10:09
    Entonces la respuesta es 409
    Y el incidente sigue reconocido por Ana Soto a las 10:07
```

## Cómo se verifica

```bash
make test-incidents
make lint
```

Y a mano: `make up && make seed`, abrir `http://localhost:8080`, entrar a un incidente abierto,
reconocerlo y ver el nombre y el tiempo en el detalle.

## Preguntas abiertas

- ¿Qué pasa con el reconocimiento cuando un incidente resuelto se reabre? Queda fuera de esta
  tarea; se decide con la historia 2.
