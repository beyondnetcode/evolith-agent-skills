# [29] Webhooks: el bug silencioso que DUPLICA eventos en producción

> Fuente: TheDebugDuck — https://youtu.be/fF4O4Jqkc0g · notas parafraseadas; «(complemento)» = conocimiento añadido o corrección.

- **Síntoma en producción:** un "río" de POST contra un endpoint sin deploy reciente (parece ataque); filas duplicadas, profundidad de cola creciendo, CPU alta en workers, pico de latencia solo en la ruta de hooks; mismo payload/ID de evento procesado N veces.
- **Causa raíz (mecanismo):** entrega **at-least-once / best effort**: el proveedor reintenta ante timeout o no-2xx porque su prioridad es no perder avisos. Si el handler hace todo dentro del request (transacción grande, side effects, emails) y responde tarde, el proveedor asume fallo y reenvía; cada POST es una petición HTTP distinta → procesamiento duplicado. Bucle de amplificación: endpoint lento → reintentos → más carga → health checks fallan → más reintentos. Además: orden distinto al de la API y carrera con lecturas eventualmente consistentes.
- **Metáfora visual del video:** mensajero que toca el timbre dos veces porque nadie abrió a la primera.
- **Estrategias / solución:**
  1. **Ack rápido + cola:** el handler solo valida, verifica firma y encola; responde 2xx (202) en milisegundos; workers consumen con backpressure y métricas.
  2. **Deduplicación por ID de evento** en tabla "ya visto" con restricción única: primera vez inserta y procesa; conflicto → salir sin efectos.
  3. **Firma:** verificar HMAC sobre el cuerpo **crudo** con el secreto del proveedor, tolerar skew de reloj en el timestamp, rotar secretos con doble ventana, registrar intentos fallidos; allowlists por IP son frágiles.
  4. **Carrera con lectura eventual:** si al releer la API el recurso aún no aparece, no abortar: confiar en el payload firmado o reintentar la lectura con backoff.
  5. **DLQ** para payloads que rompen el parser; reprocesar con humano en el loop.
  ```
  POST /webhooks/proveedor                                   (reescrito)
    raw = cuerpo_en_bytes()                                  # antes de parsear JSON
    exigir hmac_valido(raw, ts, secreto_actual | secreto_anterior) y |now - ts| < tolerancia
    INSERT INTO inbox(event_id UNIQUE, tipo, payload, estado='RECIBIDO') ON CONFLICT DO NOTHING
    encolar(event_id); responder 202
  worker(event_id):
    tx: fila = SELECT ... FROM inbox WHERE event_id=? AND estado='RECIBIDO' FOR UPDATE
        si no hay fila → return (ya procesado)
        aplicar_efecto(fila); UPDATE inbox SET estado='PROCESADO'
    error permanente → DLQ
  ```
- **Trade-offs y cuándo NO aplicar:** la cola añade latencia y un componente más; la tabla de dedupe crece (TTL/purga). Responder 2xx antes de procesar traslada la responsabilidad de reintento a tu sistema (necesitas DLQ y reproceso propios). Para eventos críticos, complementar con reconciliación periódica contra la API del proveedor.
- **Heurísticas y umbrales:** responder en milisegundos; 202 Accepted; checklist: responder rápido y encolar, verificar firma y rechazar temprano, dedupe por ID, métricas por tipo y proveedor, DLQ y alertas, prueba de carga con reintentos simulados. Diagnóstico: alinear timestamps de reintento del proveedor con tus timeouts. (complemento) Plazos típicos: GitHub ~10 s, Shopify ~5 s; Stripe tolera 5 min de desfase en la firma y reintenta hasta 3 días.
- **Anti-patrones / señales de alerta:** handler que hace "el universo" antes de responder; ausencia de restricción única sobre event_id; parsear/re-serializar JSON antes de verificar la firma; confiar en IP allowlist; asumir orden de llegada; abortar si el GET de confirmación no ve aún el recurso; sin DLQ; asumir exactly-once.
- **Preguntas de revisión arquitectónica:**
  1. ¿El endpoint responde dentro del timeout del proveedor bajo carga pico?
  2. ¿Dónde está la restricción única por event_id y está en la misma transacción que el efecto?
  3. ¿Cómo se verifica la firma (cuerpo crudo, tolerancia temporal, rotación de secretos)?
  4. ¿Cómo se maneja el desorden (versión/timestamp del recurso, o releer estado actual)?
  5. ¿Qué pasa si el proveedor deja de enviar (reconciliación contra API)?
  6. ¿Hay métricas de duplicados y latencia por proveedor y tipo de evento?
- **Caso real / empresa citada:** GitHub (semántica HTTP explícita, consola de entregas), Shopify (procesamiento asíncrono, tolerar retrasos/duplicados/desorden), Stripe (firma con cuerpo crudo, skew de reloj, idempotencia), Twilio (reintentos de callbacks). Lecturas: *DDIA*, *Enterprise Integration Patterns*, *Release It!* (Nygard), *Building Event-Driven Microservices* (Bellemare).
- **Precisión técnica:**
  - GitHub **no** reentrega automáticamente las entregas fallidas: se reenvían manualmente o vía API (complemento, corrige al video).
  - "Insertar el ID y luego procesar" pierde eventos si el proceso cae entre ambos: la marca debe confirmarse en la misma transacción que el efecto, o usar estados RECIBIDO/PROCESADO (complemento).
  - Este diseño es el **Inbox pattern** (simétrico al Outbox) (complemento).
  - "Es el primo hermano del problema de concurrencia": dos reintentos simultáneos pueden correr en paralelo; la restricción única (no un `SELECT` previo) es lo que evita la carrera (complemento).
