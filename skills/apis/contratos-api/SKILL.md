---
name: contratos-api
description: Criterio para diseñar, evolucionar y revisar contratos de API HTTP — breaking changes (incluidos los semánticos que responden 200 OK), versionado por URL, header, query o media type, expand/contract y tolerant reader, deprecación y sunset (headers Deprecation y Sunset), OpenAPI y diff de contratos, códigos de estado correctos (401 vs 403, 404 vs 410, 409/412/422, 429, 500/502/503/504), errores consistentes con Problem Details (RFC 9457) y fechas sin ambigüedad (UTC, instante vs fecha civil vs hora local con zona IANA, DST, epoch en segundos o milisegundos, timestamptz). Úsala siempre que un diseño, PR, ADR o incidente toque endpoints, integraciones B2B o apps móviles, renombrar o quitar campos, cambiar unidades o enums, publicar una v2 o retirar una versión, definir respuestas de error o políticas de reintento, o guardar, transmitir o mostrar fechas y horas (agendas, cobros recurrentes, reportes por día, zonas horarias, cambio de horario), aunque el usuario no nombre el patrón.
license: MIT
metadata:
  categoria: apis
  version: "1.0.0"
  idioma: es
  fuentes: "TheDebugDuck: 32, 35, 37"
  relacionadas: "seguridad-aplicaciones, estilos-arquitectonicos, resiliencia-operacion"
---

# Contratos de API: evolución, semántica HTTP y tiempo

Conocimiento destilado de TheDebugDuck (videos 32, 35 y 37) y completado con fuentes primarias (RFC 9110, 9457, 9745, 8594, 6585, 3339, 9557; IANA tz; OpenAPI 3.1). Un contrato es **todo lo observable** por un cliente —forma, significado, unidades, códigos, errores y tiempos—, y los clientes que no controlas no se actualizan a tu ritmo. El objetivo: que ningún consumidor cambie de comportamiento sin haberlo decidido.

> Las tres referencias se elaboraron desde el título y el temario público de cada video (la transcripción no estuvo disponible); lo que no figura en el temario va marcado «(complemento)».

## Cómo usar esta skill

1. Ubica el área con la matriz: **evolución/versionado** (32), **códigos y errores** (37) o **fechas y zonas** (35). Un cambio de API suele tocar dos: p. ej. pasar un campo a UTC es un breaking change (32 + 35).
2. Pide evidencia antes de opinar: OpenAPI y su diff contra `main`, consumidores reales (logs por client_id, versión de app, partner), tipos de columnas temporales en la BD, handler global de errores, política de reintentos del cliente o gateway.
3. Lee **solo** la referencia implicada: trae síntoma, mecanismo, ejemplos, trade-offs, anti-patrones, preguntas y precisiones.
4. Entrega con el formato de salida. Si el repositorio tiene ADRs o registro de hallazgos, la decisión de versionado o de modelo temporal va a un ADR y lo que no se cierre, al registro.

## Índice de referencias

| Tema | Archivo | Léelo cuando… |
|---|---|---|
| Contrato, breaking changes, versionado URL/header/query/media type, expand/contract, deprecación y sunset, OpenAPI, gateways, observabilidad | `references/32-versionado-de-api.md` | cambias o retiras campos, endpoints o enums; publicas una v2; "200 OK pero los números no cuadran"; clientes móviles o B2B |
| UTC, zonas IANA, instante vs fecha civil vs hora local, DST, epoch s/ms, `timestamptz`, frontend | `references/35-utc-y-fechas.md` | guardas, transmites o muestras fechas; agendas eventos futuros; jobs en hora local; reportes "por día"; bugs tras el cambio de horario |
| Familias 2xx–5xx, 200/201/202/204/304, 401/403, 404/410, 409/412/422, 429, 500/502/503/504, Problem Details, reintentos | `references/37-codigos-http.md` | defines respuestas y errores; revisas clientes, SDKs o gateways que reintentan, cachean o alertan según el código |

## Principios (y por qué)

- **El contrato incluye la semántica.** Cambiar unidades, impuestos, zona horaria o el significado de un estado con la misma forma rompe clientes y ningún validador de esquema lo detecta: solo lo ven las métricas de negocio.
- **Compatibilidad por defecto; versión como último recurso.** Cada versión viva multiplica código, pruebas, soporte y superficie de seguridad. Primero aditivo, luego expand/contract; versión mayor solo si ambos fallan.
- **Clientes tolerantes con lo desconocido, estrictos con lo que usan.** Ignorar campos nuevos y tratar enums como abiertos permite evolucionar sin coordinar despliegues; validar estrictamente los campos que sí se usan evita aceptar basura (la tolerancia indiscriminada osifica el protocolo, RFC 9413).
- **Deprecar es un proceso medido, no una fecha.** Sin uso por versión y por consumidor no sabes a quién rompes; `Deprecation` avisa sin cambiar el comportamiento, `Sunset` fija el fin y después se responde 410.
- **El contrato vive en OpenAPI y se protege en CI.** Un diff automático que falla ante breaking changes no declarados detecta en el PR lo que de otro modo detecta un partner en producción.
- **El código HTTP es para máquinas; el cuerpo, para el detalle.** Reintentos, caches, breakers, SDKs y SLO deciden por el código. Si miente (200 con error), cada capa decide mal.
- **Un solo formato de error con causa estable.** `application/problem+json` con `type` estable y `trace_id`: los clientes ramifican por `type`, nunca por texto, y soporte correlaciona sin pedir capturas.
- **Reintentar es un contrato entre código e idempotencia.** 429/503/504 invitan a reintentar solo si repetir es seguro; un POST sin `Idempotency-Key` tras un 504 puede cobrar dos veces.
- **Instante, fecha civil y hora local con zona son tipos distintos.** Lo que ocurrió va en UTC; un cumpleaños no tiene hora; una cita futura es hora local + zona IANA, porque los gobiernos cambian las reglas con semanas de aviso.
- **La zona es un ID IANA; el offset es un dato derivado.** `-05:00` no dice qué pasará en noviembre; `America/Lima` sí, siempre que tzdata esté al día en cada runtime.
- **Unidades explícitas.** Epoch en segundos o milisegundos, céntimos o unidades, con o sin impuestos: en el nombre del campo o en el formato, nunca implícito.

## Matriz "si ves X → considera Y"

| Si ves… | Considera… | Evita… |
|---|---|---|
| 200 OK y el negocio dice que los números no cuadran | cambio semántico de contrato: diff de OpenAPI y del significado; métricas de negocio por versión | buscar solo errores 5xx en logs |
| Renombrar, cambiar tipo o unidad de un campo | expand/contract: campo nuevo junto al viejo, medir uso, `Deprecation`, retirar al llegar a ≈ 0 | cambiar in-place "porque nadie lo usa" |
| Añadir un valor a un enum | enum declarado abierto en el contrato + clientes con rama `default` | `switch` exhaustivo o deserialización estricta en clientes |
| Rediseño grande de recursos | versión mayor en la ruta (`/v2`), ≤ 2 mayores vivas | `v2` como copia completa de `v1` que diverge |
| Cambios pequeños y frecuentes | versiones por fecha en header, versión fijada por cliente o cuenta | default "latest" cuando falta el header |
| Retirar una versión o endpoint | `Deprecation` + `Sunset` + `Link`, aviso directo, brownouts, 410 tras la fecha | apagar por fecha sin medir quién queda; 404 genérico |
| App móvil o partner B2B que no controlas | ventanas largas, compatibilidad aditiva, contrato de consumidor (Pact) | asumir que "todos actualizan" |
| Versionado por header detrás de CDN | `Vary` con el header de versión | caché que mezcla v1 y v2 |
| Error de negocio devuelto con 200 | código correcto + `application/problem+json` con `type` estable | `{"success": false}` |
| Token expirado vs sin permiso | 401 + `WWW-Authenticate` (refrescar) / 403 (no reintentar) | 403 para expirado; 401 para permisos |
| Validación, duplicado o edición concurrente | 422 (semántica), 409 (estado o duplicado), 412 con `If-Match` (lost update) | 500 por excepción sin mapear; 400 para todo sin `type` |
| Cliente que excede su cuota | 429 + `Retry-After` (+ `RateLimit` si se adopta el borrador) | 503 por cuota; 429 sin indicar cuándo reintentar |
| 502/504 en picos | atribuir al gateway y al upstream; timeouts coherentes; reintento solo idempotente | reescribir todo a 500; reintentar POST sin clave |
| Trabajo que excede el tiempo de la petición | 202 + `Location` a un recurso de estado (o webhook) | mantener la conexión abierta minutos |
| `DateTime.Now`, `LocalDateTime.now()`, `datetime.utcnow()` persistidos | instante en UTC con tipo aware; reloj inyectable | depender de la zona del servidor |
| Columna `timestamp` sin zona para instantes | `timestamptz` + sesión en UTC | confiar en el offset del literal (se ignora en silencio) |
| Cita o reserva futura | hora local + zona IANA + instante derivado, recalculado al actualizar tzdata | guardar solo el UTC calculado hoy |
| Cumpleaños, vencimiento, feriado | `date` / `"2026-09-28"` / `LocalDate` | `2026-09-28T00:00:00Z` (se ve el día anterior en América) |
| Job de negocio entre 01:00 y 03:00 en zona con DST | política de hueco/solape + idempotencia por fecha de negocio; jobs técnicos en UTC | cron local sin política |
| Epoch en el contrato | RFC 3339 con `Z`, o unidad en el nombre (`_epoch_s`, `_epoch_ms`) | `timestamp: 1790553600` sin unidad |

## Preguntas de revisión

1. ¿Qué cambia en lo observable (forma, significado, unidades, códigos, errores, tiempos) y es aditivo o breaking?
2. ¿Quién consume hoy el endpoint y con qué evidencia (client_id, versión de app, partner)?
3. ¿El diff de OpenAPI en CI bloquea breaking changes no declarados? ¿Qué versión recibe quien no envía versión?
4. ¿Hay `Deprecation`, `Sunset`, `Link`, aviso directo y respuesta definida tras el sunset?
5. ¿Algún endpoint devuelve 2xx con error en el cuerpo? ¿Los errores usan un formato único con `type` estable y `trace_id`?
6. ¿Qué códigos reintentan el cliente, el SDK y el gateway, y es seguro repetir cada escritura?
7. Para cada campo temporal: ¿instante, fecha civil o local + zona? ¿BD, JSON y código lo reflejan?
8. ¿Los eventos futuros guardan zona IANA y hay recálculo tras actualizar tzdata? ¿Qué pasa en la noche del cambio de horario?
9. ¿Qué métrica de negocio detectaría en menos de un día un 200 OK con datos incorrectos?

## Precisiones que no se deben repetir

- **"Versionar evita breaking changes."** No: solo aísla a quien no migra. La estrategia principal es no romper (aditivo + tolerant reader + expand/contract).
- **"Añadir un campo o un valor de enum nunca rompe."** Rompe clientes con deserialización estricta o `switch` exhaustivo; es compatible solo si el contrato lo declara y los clientes lo toleran.
- **"Deprecated = deja de funcionar."** `Deprecation` (RFC 9745) no cambia el comportamiento; el fin lo marca `Sunset` (RFC 8594), que además es una pista, no una garantía. `Deprecation` usa `@<segundos Unix>`; `Sunset`, HTTP-date.
- **"401 = no autorizado."** 401 es no autenticado y exige `WWW-Authenticate`; la falta de permisos es 403 (o 404 para ocultar existencia, que RFC 9110 permite).
- **"422 es de WebDAV."** RFC 9110 lo estandarizó como "Unprocessable Content".
- **"Un 504 significa que no se procesó."** El gateway dejó de esperar; el upstream pudo completar la operación. Reintenta solo con idempotencia.
- **"Los errores no se cachean."** 404, 405, 410, 414 y 501 son cacheables heurísticamente: fija `Cache-Control`.
- **"Guarda todo en UTC."** Correcto para instantes; incorrecto para fechas civiles y eventos futuros en hora local.
- **"`timestamptz` guarda la zona."** Guarda el instante; la zona de entrada se pierde. Guarda la zona IANA aparte si la necesitas.
- **"Z y +00:00 son lo mismo."** RFC 9557 redefinió `Z` como "UTC conocido, offset local desconocido"; para enviar instantes en APIs `Z` sigue siendo lo adecuado.
- **"UTC y GMT son lo mismo."** Coinciden en offset; UTC es una escala de tiempo y GMT, una hora civil.

## Formato de salida

Cuando recomiendes algo de este dominio, entrega:

```
Decisión: <mecanismo mínimo>, en una línea.
Clasificación: <aditivo | breaking de forma | breaking semántico | modelo temporal | semántica de errores>.
Contrato resultante: <fragmento OpenAPI, tabla código → type, o por campo: concepto temporal + tipo BD + formato JSON>.
Migración: <expand → migrate → contract con fechas de Deprecation/Sunset y consumidores afectados; o "no aplica">.
Clientes: <qué deben tolerar o cambiar (enums abiertos, reintentos, zona IANA)>.
Verificación: <diff OpenAPI en CI, pruebas de contrato, pruebas con reloj fijo y fechas DST, métricas por versión y consumidor>.
Cuándo NO: <condición en la que esto sobra>.
Fuente: <referencia(s) usadas, p. ej. references/32-versionado-de-api.md, y RFC citados>.
```
