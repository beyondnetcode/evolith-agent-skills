# [34] El patrón que evita DOBLES COBROS en APIs (Idempotencia explicada fácil)

> Fuente: TheDebugDuck — https://youtu.be/DGSsZ1PWlr0 · notas parafraseadas; «(complemento)» = conocimiento añadido o corrección.
> Estado: elaborado a partir del título del video (la descripción pública está vacía: no hay temario); la transcripción no estuvo disponible (bloqueo de YouTube, 2026-09-28). Lo que no figura en el título es «(complemento)». Pendiente de contrastar con la transcripción.

- **Síntoma en producción:** dobles cobros en una API. (complemento)
  - El usuario pulsa "Pagar", la red móvil corta o el gateway da timeout, y la app reintenta (o el usuario vuelve a pulsar). El backend ejecuta el cargo dos veces: el usuario ve "error" en pantalla y dos movimientos en su banco.
  - Variantes: pedidos, correos o reservas duplicados, y reintentos automáticos de SDK, mesh o gateway que nadie ve en el código.
- **Causa raíz (mecanismo):** (complemento)
  - El cliente no distingue "no llegó" de "llegó, se ejecutó y se perdió la respuesta". Ante la duda reintenta, y `POST` no es idempotente: RFC 9110 solo declara idempotentes GET, HEAD, OPTIONS, TRACE, PUT y DELETE.
  - Sin una identidad del intento, el servidor ve dos peticiones legítimas.
  - Deshabilitar el botón es UX, no una garantía: no cubre reintentos de red, del SDK ni de colas.
- **Metáfora visual (complemento, propia; la del video no está disponible):** el cheque numerado.
  - El banco no paga dos veces el cheque 0042 de la misma chequera aunque lo presentes dos veces.
  - El número lo escribe quien firma (el cliente), no el banco.
  - Presentar el 0042 con otro importe se rechaza.
  - ⚠️ Límites: las claves caducan (pasado el TTL, la misma clave crea una operación nueva), y el cheque no modela el estado "en proceso" (dos presentaciones simultáneas → 409).
- **Estrategias / solución:** (complemento)
  1. **Clave por intento lógico, generada por el cliente.** Un UUIDv4, o un valor derivado de un objeto propio como el ID del checkout, creado al iniciar la intención. Se reenvía idéntica en cada reintento y solo cambia si el usuario cambia la petición. Header `Idempotency-Key` (borrador IETF: Structured Field de tipo string, p. ej. `Idempotency-Key: "8e03978e-40d5-43e8-bc93-6894a57f9324"`).
  2. **Registro en el servidor** con `UNIQUE (cuenta_id, clave)`: guarda el hash del cuerpo canónico (junto con método y ruta), el estado, el código y el cuerpo de la respuesta, y las fechas.
     ```
     POST /pagos   Idempotency-Key: "5f1c…"                                   (reescrito)
       k = header; si falta en una ruta con efectos → 400
       h = sha256(método + ruta + cuerpo_canónico)
       INSERT INTO idem(cuenta_id, clave, hash, estado, bloqueado_hasta)
         VALUES (:c, :k, :h, 'EN_PROCESO', now() + interval '60 s')
         ON CONFLICT (cuenta_id, clave) DO NOTHING
       si no insertó → fila = SELECT … WHERE cuenta_id=:c AND clave=:k FOR UPDATE
         fila.hash ≠ h                          → 422 (misma clave, otro cuerpo)
         fila.estado = 'COMPLETADA'             → reproducir fila.status + fila.cuerpo (Idempotent-Replayed: true)
         EN_PROCESO y bloqueado_hasta > now()   → 409 + Retry-After
         EN_PROCESO vencido                     → tomar el relevo y reanudar desde el último paso confirmado
       efecto local + UPDATE idem SET estado='COMPLETADA', status=201, cuerpo=:json   -- misma transacción
       efecto externo (PSP) → enviarle una clave derivada (k + paso): el proveedor también deduplica
     ```
     Si el efecto es solo local, basta **una** transacción (clave + efecto + respuesta). En PostgreSQL READ COMMITTED, la segunda petición concurrente espera en el índice único; cuando la primera confirma, encuentra la fila COMPLETADA. El estado EN_PROCESO con relevo solo hace falta cuando hay llamadas externas que no deben ir dentro de la transacción.
  3. **Qué se guarda.**
     - El resultado final: los 2xx y los 4xx de negocio (p. ej. tarjeta rechazada).
     - Los fallos anteriores a la ejecución (validación, autenticación, 429) no se guardan; Stripe también los deja reintentar.
     - Un 5xx con rollback completo libera la clave. Si pudo haber efecto externo, se guarda como indeterminado y se reconcilia (Stripe guarda los 500 y los trata como indeterminados).
  4. **TTL.** Debe superar la ventana máxima de reintento del cliente, incluidas las colas offline del móvil. Stripe permite purgar las claves a partir de 24 h. El borrador pide publicar la política. Purga por lotes o por partición de fecha.
  5. **Preferir la idempotencia natural a la tabla:**
     - `PUT` que reemplaza el estado completo, y `DELETE`.
     - Transiciones condicionales: `UPDATE pago SET estado='PAGADO' WHERE id=:id AND estado='PENDIENTE'`.
     - Upsert por clave de negocio.
     - Un ledger con `UNIQUE (operacion_id)`.
     - `saldo = saldo + x` nunca es idempotente: conviértelo en un asiento con ID.
  6. **Consumidores y webhooks.** El mismo principio, aplicado a `message_id`/`event_id`: Inbox con `UNIQUE` en la misma transacción que el efecto ([29]). El Outbox produce duplicados por diseño ([28]) y el redrive de la DLQ reentrega ([24]).
- **Trade-offs y cuándo NO aplicar:** (complemento)
  - Cuesta una escritura más por petición y una tabla que crece.
  - Las respuestas guardadas pueden contener datos personales: cífralas o guarda solo lo necesario.
  - El estado EN_PROCESO necesita relevo tras una caída.
  - Propagar la clave a un tercero solo sirve si el tercero la soporta. Si no, consulta antes de reintentar y reconcilia.
  - Sobra en GET/HEAD y en operaciones idempotentes por naturaleza.
  - No sustituye al control de concurrencia entre intentos distintos ([33]).
- **Heurísticas y umbrales:** (complemento)
  - Toda ruta `POST`/`PATCH` con efectos monetarios o irreversibles exige clave (400 si falta).
  - La clave tiene alcance por cuenta/tenant, nunca global.
  - Sin datos personales en la clave (Stripe lo desaconseja). Tamaño ≤ 255 caracteres (límite de Stripe).
  - Retención ≥ 24 h.
  - 409 ante concurrencia y 422 ante un cuerpo distinto (borrador IETF).
  - El cliente reintenta con backoff y jitter y **la misma** clave; genera una nueva solo tras corregir un 4xx.
- **Anti-patrones / señales de alerta:**
  - Clave generada en el servidor o regenerada en cada reintento.
  - Clave = timestamp o hash del cuerpo: dos compras legítimas idénticas se fusionan.
  - `SELECT` para "ver si existe" y luego `INSERT` sin restricción única.
  - Marca y efecto en transacciones distintas sin estados intermedios.
  - Responder 200 al reuso con otro cuerpo.
  - Guardar las claves en la memoria de una réplica.
  - TTL menor que la ventana de reintentos.
  - Reintentar un 5xx de pago con una clave nueva.
- **Preguntas de revisión arquitectónica:**
  1. ¿Quién genera la clave, en qué momento del flujo, y sobrevive a un reinicio de la app?
  2. ¿Qué responde el servidor ante la misma clave en tres casos: concurrente, repetida tras completarse y con otro cuerpo?
  3. ¿La marca y el efecto se confirman en la misma transacción? ¿Qué pasa si el proceso cae entre la llamada al PSP y el registro?
  4. ¿La clave se propaga a los terceros con efectos (pasarela, SMS)?
  5. ¿Cuánto tiempo se retiene la clave? ¿Supera la ventana de reintentos del cliente más lento?
  6. ¿Qué operaciones podrían ser idempotentes por diseño y hoy dependen de la tabla?
- **Caso real / referencias (complemento):**
  - Stripe, header `Idempotency-Key`: respuesta guardada incluso en los 500, comparación de parámetros, `Idempotent-Replayed: true`, purga a partir de 24 h, 409 ante conflicto concurrente.
    - https://docs.stripe.com/api/idempotent_requests
    - https://docs.stripe.com/error-low-level
  - Brandur Leach, "Implementing Stripe-like Idempotency Keys in Postgres" (2017, *recovery points*).
  - Airbnb, "Avoiding Double Payments in a Distributed Payments System" (2019).
  - AWS Builders' Library, "Making retries safe with idempotent APIs".
  - RFC 9110 §9.2.2: https://www.rfc-editor.org/rfc/rfc9110#section-9.2.2
  - draft-ietf-httpapi-idempotency-key-header-07: https://datatracker.ietf.org/doc/draft-ietf-httpapi-idempotency-key-header/
- **Precisión técnica:**
  - Según RFC 9110, la idempotencia se refiere al **efecto previsto** en el servidor, no a la respuesta: un segundo `DELETE` que devuelve 404 es correcto. Un `PUT` es idempotente solo si reemplaza estado; si acumula, viola la semántica (complemento).
  - Idempotente no significa seguro frente a concurrencia: dos `PUT` distintos simultáneos se pisan. Usa `If-Match`/ETag (412) o versión ([33]) (complemento).
  - `Idempotency-Key` es un **borrador** IETF (‑07, octubre de 2025, expirado sin llegar a RFC), no un estándar. Es práctica de facto; PayPal, por ejemplo, usa `PayPal-Request-Id` (complemento).
  - En Stripe, los limitadores de tasa corren antes que la capa de idempotencia: un 429 reintentado con la misma clave puede dar otro resultado (complemento).
  - "Exactly-once" de extremo a extremo no existe: at-least-once + idempotencia = efectivamente una vez (complemento).
  - Clave de idempotencia ≠ request ID ≠ correlation ID. El request ID cambia en cada intento; la clave es la misma en todos los intentos del mismo propósito (complemento).
