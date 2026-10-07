# Backlog

Lo que el equipo pidió y todavía no está hecho. Las historias están escritas como llegaron, sin
especificar: antes de construir cualquiera hay que precisar qué significa «terminada».

## Historias

### 1. Reconocer un incidente

Quien está de guardia necesita decir «lo vi, me hago cargo» sin cambiar todavía el estado del
incidente. Queremos saber cuánto tardó cada persona en reconocer cada incidente.

### 2. Escalar si nadie responde

Si un SEV1 o SEV2 no se reconoce a tiempo, hay que avisarle a alguien más. Todavía no definimos
quién es ese alguien ni cuánto es «a tiempo».

### 3. MTTA y MTTR por servicio

Un panel con el tiempo medio hasta reconocer y hasta resolver, por servicio y por severidad, en
una ventana de tiempo que elige quien lo mira.

### 4. Incidentes duplicados

Cuando checkout se cae, cinco personas abren cinco incidentes. Queremos detectarlo y agrupar los
duplicados bajo uno solo.

### 5. Post-mortem obligatorio

Los SEV1 y SEV2 no deberían poder darse por cerrados sin post-mortem. Hoy «resuelto» es el
último estado; quizá falte otro.

### 6. Acciones del post-mortem con dueño

Las acciones del post-mortem son un texto libre. Queremos que cada una tenga responsable, fecha
comprometida y estado, y ver las vencidas.

### 7. Reemplazos de turno

Alguien de guardia se enferma y otra persona lo cubre dos días. Hoy hay que editar el turno a
mano en la base.

### 8. Canales de aviso

Los avisos solo quedan en el log de notifications. Queremos mandarlos a un webhook (Slack o
similar), con reintentos si el destino no responde.

## Reportes de usuarios

Llegaron por el canal de soporte. Nadie los ha investigado.

- «El domingo era mi último día de turno, hubo un SEV2 y no me llegó nada.»
- «A veces el aviso le llega a alguien que no está de guardia esa semana.»
