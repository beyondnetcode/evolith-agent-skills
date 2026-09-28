# [37] ¿Qué significan los códigos HTTP? (explicado fácil)

> Fuente: TheDebugDuck — https://youtu.be/o9WXg3gq64c · notas parafraseadas; «(complemento)» = conocimiento añadido o corrección.
> Estado: elaborado a partir del título y el temario público del video; la transcripción no estuvo disponible (bloqueo de YouTube, 2026-09-28). Lo que no figura en el temario es «(complemento)». Pendiente de contrastar con la transcripción.

- **Síntoma en producción** (complemento): la app muestra "éxito" ante un fallo porque la API responde 200 con `{"success": false}`; el monitoreo marca 0 % de errores mientras el negocio falla; clientes que reintentan un 400 sin fin o no reintentan un 503; bucle de login porque un token expirado recibe 403 (el cliente no refresca) o la falta de permisos recibe 401 (el cliente cierra la sesión); el gateway convierte todo en 500 y nadie sabe si falló el origen o el proxy; un CDN sirve un 404 transitorio durante horas; integradores que parsean mensajes de error en texto libre y se rompen al corregir una tilde.
- **Causa raíz (mecanismo):** los códigos HTTP son el contrato entre la API y el cliente, no decoración. (complemento) Son la parte del contrato que leen las **máquinas intermedias**: SDKs, políticas de reintento, circuit breakers, caches y CDN, balanceadores, monitoreo y SLO. Si el código miente, cada capa decide mal: reintenta lo que no debe, cachea un error, desloguea al usuario o no alerta. El cuerpo sirve para el detalle; el código, para la decisión.
- **Metáfora visual (complemento; propuesta propia, no es la del video):** **el sello del sobre devuelto por correo**. La sala de correo decide sin abrir la carta: "dirección inexistente" (404), "se mudó sin dejar dirección" (410), "rechazado por el destinatario" (403), "remitente no identificado" (401), "oficina cerrada, reintentar el lunes" (503 + `Retry-After`). La carta de dentro (el cuerpo) explica el detalle. Un 200 con error en el cuerpo es un sobre sellado "entregado" que dentro dice "no pude entregarlo": la sala de correo lo archiva como éxito.
- **Estrategias / solución:**
  1. **Familias:** 2xx éxito; 3xx redirección o usar la copia en caché; 4xx el cliente debe cambiar algo antes de repetir; 5xx el servidor o un intermediario falló y repetir puede funcionar. (complemento) Regla de reintento: 4xx no se repite igual (salvo 408, 429 y 409 tras releer); 5xx se reintenta con backoff y jitter **solo** si el método es idempotente o lleva `Idempotency-Key`.
  2. **Distinciones que más se confunden** (temario; mecanismos y headers: complemento):

     | Par | Usa el primero cuando… | Usa el segundo cuando… |
     |---|---|---|
     | 200 / 201 / 204 | 200: éxito con cuerpo | 201: se creó un recurso (+ `Location` con su URI); 204: éxito sin cuerpo (DELETE, PUT sin eco); no puede llevar contenido |
     | 202 / 304 | 202: trabajo aceptado pero no terminado; `Location` a un recurso de estado (`/operaciones/123`); no garantiza que se complete | 304: GET condicional (`If-None-Match` con ETag) y el cliente ya tiene la versión vigente; usa su copia, sin cuerpo |
     | 401 / 403 | no hay credenciales válidas (faltan, expiraron, firma inválida); **debe** incluir `WWW-Authenticate`; el cliente puede refrescar o reautenticar | identidad conocida sin permiso; reautenticar con las mismas credenciales no ayuda |
     | 404 / 410 | no hay representación, sin decir si es temporal o permanente, o no se quiere revelar que existe | retiro intencional y probablemente permanente (endpoint tras el sunset, recurso eliminado definitivamente) |
     | 400 / 422 | petición malformada (JSON inválido, tipo incorrecto) | bien formada pero semánticamente inválida (fin < inicio, regla de validación) |
     | 409 / 412 | conflicto con el estado actual (clave única duplicada, transición de estado inválida, misma `Idempotency-Key` en vuelo) | falló una precondición del cliente (`If-Match: "v7"` y el recurso ya va en v8): evita el *lost update*; 428 exige enviarla |
     | 429 / 503 | un cliente superó **su** cuota (RFC 6585) + `Retry-After` | el servicio entero no puede atender (sobrecarga, mantenimiento, breaker abierto) + `Retry-After` |
     | 500 / 502 / 504 | 500: condición inesperada en el propio servidor (bug, excepción no mapeada) | 502: un gateway recibió una respuesta inválida del upstream; 504: un gateway no recibió respuesta a tiempo del upstream |
     | 301/302 / 307/308 | redirecciones históricas: el cliente puede cambiar POST a GET | 307 (temporal) y 308 (permanente) preservan el método: úsalos en APIs |

  3. **Errores consistentes en toda la API** (temario) con Problem Details, RFC 9457 (complemento):
     ```http
     HTTP/1.1 422 Unprocessable Content
     Content-Type: application/problem+json

     {
       "type": "https://api.ejemplo.com/problemas/validacion",
       "title": "La solicitud tiene campos inválidos",
       "status": 422,
       "detail": "2 campos no cumplen las reglas",
       "instance": "/problemas/ocurrencias/7f3c",
       "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
       "errors": [
         {"pointer": "/fecha_entrega", "code": "fecha_pasada", "detail": "Debe ser posterior a hoy"},
         {"pointer": "/items/0/cantidad", "code": "minimo", "detail": "Mínimo 1"}
       ]
     }
     ```
     `type` es el código estable por el que el cliente ramifica (nunca por `detail`); `title` no cambia entre ocurrencias; `detail` ayuda a corregir, no a depurar; `errors` (extensión) apunta a cada campo con JSON Pointer; `trace_id` correlaciona con logs; sin stack traces, SQL ni nombres internos.
  4. **Un solo punto de mapeo** (complemento): excepciones de dominio → código + `type` en un middleware o exception handler global, no en cada controlador. Documentar en OpenAPI, por operación, los códigos y `type` posibles, y probarlos.
  5. **Política de reintento por código en el cliente, SDK y gateway** (complemento): 408/429/502/503/504 → reintento con backoff exponencial + jitter y respeto de `Retry-After`, con techo; 500 → como mucho 1–2 reintentos si es idempotente (suele ser determinista); 401 → un refresco de token y fallar; 409 → releer y decidir; resto de 4xx → no reintentar.
  6. **Límites comunicados, no adivinados** (complemento): 429 con `Retry-After` (segundos o HTTP-date) y, si se adopta, los headers del borrador IETF `RateLimit-Policy: "default";q=100;w=60` y `RateLimit: "default";r=12;t=30` (`q` cuota y `w` ventana de la política en segundos; `r` cuota disponible y `t` segundos de la ventana efectiva).
  7. **Observabilidad por código y emisor** (complemento): SLO de disponibilidad sobre 5xx (429 aparte); separar 5xx del origen de 502/504 del gateway; tasa de 4xx por consumidor tras cada despliegue (detecta contratos rotos; ver la referencia 32).
- **Trade-offs y cuándo NO aplicar:** un conjunto corto bien usado (200, 201, 202, 204, 304, 400, 401, 403, 404, 409, 410, 412, 422, 429, 500, 502, 503, 504) vale más que códigos exóticos que los clientes no conocen. 400 frente a 422 para validación es debatible: importa más la coherencia y un `type` que distinga la causa. Ocultar existencia con 404 en lugar de 403 mejora la seguridad (p. ej. recursos de otro tenant) a costa de depuración. 202 añade un recurso de estado y polling o webhook: úsalo solo si el trabajo excede el presupuesto de tiempo de la petición. GraphQL, JSON-RPC y gRPC tienen convenciones propias; esta guía aplica a APIs REST/HTTP, y un gateway que transcodifica debe mapear explícitamente (complemento).
- **Heurísticas y umbrales** (complemento):
  - "¿Quién tiene que cambiar algo para que funcione?" El cliente → 4xx; el servidor → 5xx; nadie, ya funcionó → 2xx.
  - "¿Repetir la misma petición puede funcionar?" Sí → 408/429/503/504 (+ `Retry-After`); no → resto de 4xx.
  - Un `type` estable por causa de negocio; nunca ramificar por texto.
  - Cualquier 4xx/404 detrás de CDN lleva `Cache-Control` explícito (`no-store` si es transitorio).
- **Anti-patrones / señales de alerta:** 200 con `{"success": false}` o `{"error": …}`; 500 para validación o "no encontrado" (excepción sin mapear); 403 para token expirado y 401 para falta de permisos; 401 sin `WWW-Authenticate`; 404 para un endpoint retirado tras el sunset (corresponde 410); 503 para la cuota de un cliente (corresponde 429); 429 sin `Retry-After`; formatos de error distintos por equipo; `detail` con stack trace o SQL; reintentar un POST tras 504 sin `Idempotency-Key` (el upstream pudo completarlo: doble cobro); gateway que reescribe todo error del upstream a 500; 204 con cuerpo; 201 sin `Location`.
- **Preguntas de revisión arquitectónica:**
  1. ¿Algún endpoint devuelve 2xx con un error en el cuerpo?
  2. ¿Un token expirado produce 401 con `WWW-Authenticate` y el cliente distingue 401 de 403?
  3. ¿Todos los errores usan un formato único (`application/problem+json`) con `type` estable y `trace_id`?
  4. ¿Qué códigos reintentan el cliente, el SDK y el gateway, con qué backoff y respetando `Retry-After`?
  5. ¿Un 502/504 se puede atribuir al intermediario y al upstream concretos?
  6. ¿Qué respuestas de error pueden quedar en caché de CDN y durante cuánto?
  7. ¿Es seguro reintentar esta escritura tras un 504 (idempotencia)?
- **Caso real / referencias** (complemento; no se sabe qué casos cita el video):
  - Stripe documenta su propio mapeo: 402 "Request Failed" para parámetros válidos cuyo cobro falla (402 está "reservado" en RFC 9110), 409 cuando otra petición usa la misma clave de idempotencia y 424 para fallos de dependencias externas. Ejemplo de que un mapeo propio es válido si está **documentado** y es estable.
  - Primarias: RFC 9110 (jun-2022, semántica HTTP: §15 códigos, §9.2.2 métodos idempotentes, §10.2.3 `Retry-After`); RFC 9457 (jul-2023, Problem Details, obsoleta RFC 7807); RFC 6585 (abr-2012: 428, 429, 431, 511); draft-ietf-httpapi-ratelimit-headers-11 (may-2026, borrador, no RFC).
- **Precisión técnica:**
  - "401 Unauthorized" significa **no autenticado**; el nombre es histórico. RFC 9110 exige `WWW-Authenticate` en toda respuesta 401 (complemento).
  - RFC 9110 permite responder 404 en lugar de 403 para ocultar que un recurso existe (complemento).
  - 404 y 410 son **cacheables heurísticamente** (igual que 200, 203, 204, 206, 300, 301, 308, 405, 414 y 501): sin `Cache-Control` explícito, una caché puede reutilizarlos (complemento).
  - 422 ya no es "solo WebDAV": RFC 9110 lo incorporó como "Unprocessable Content"; 413 pasó a llamarse "Content Too Large" (complemento).
  - 202 es deliberadamente sin compromiso: la operación puede no ejecutarse nunca; HTTP no reenvía el resultado, por eso hace falta un recurso de estado (complemento).
  - 204 termina en los headers: no puede llevar contenido (complemento).
  - 502 y 504 los genera un gateway o proxy; un 504 **no** significa que el upstream no procesó la petición (complemento).
  - RFC 6585 no define cómo contar peticiones ni cómo identificar al cliente para 429, y `Retry-After` es opcional (MAY) (complemento).
  - Usar 503 ante sobrecarga no es obligatorio (un servidor puede rechazar conexiones), pero con `Retry-After` evita reintentos en manada (complemento).
  - El `status` dentro de problem+json es orientativo: manda el código de la línea de estado, que un intermediario puede cambiar (complemento).
  - 426 exige el header `Upgrade` y es para cambiar de protocolo; 402 sigue reservado en el estándar (complemento).
  - Los headers `X-RateLimit-*` no son estándar; el borrador vigente define `RateLimit-Policy` y `RateLimit` con ventanas en segundos relativos para no depender de relojes sincronizados (complemento).
