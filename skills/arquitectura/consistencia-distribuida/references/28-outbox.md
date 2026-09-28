# [28] Outbox Pattern: cómo evitar perder eventos en producción

> Fuente: TheDebugDuck — https://youtu.be/aWUpXYlypYA · notas parafraseadas; «(complemento)» = conocimiento añadido o corrección.

- **Síntoma en producción:** Black Friday; pagos en verde, ventas celebrando, almacén sin despachar: miles de pedidos pagados que el resto del sistema no conoce. Tickets "pagué y no llegó", jobs de reconciliación manual, scripts que comparan BD con el topic, colas creciendo de un lado y tablas tranquilas del otro; cada servicio parece sano por separado.
- **Causa raíz (mecanismo):** **dual write**: guardar en la BD y publicar en el broker (Kafka/RabbitMQ) son dos operaciones no atómicas con dos redes y dos fallos posibles. Escenario A: commit OK, publicación perdida (timeout, reinicio, deploy) → **pedido fantasma**. Escenario B: se publica primero y la transacción hace rollback (validación tardía, bug en mapper) → **evento fantasma** con efectos ya ejecutados (stock, SMS). Publicar síncronamente en el request acopla el checkout al bus y alimenta el dominó (timeout → reintento → worker saturado → lag → presión en BD).
- **Metáfora visual del video:** dos mundos (BD y bus) que deben contar la misma historia; guardar y publicar como "dos apuestas seguidas".
- **Estrategias / solución:**
  1. **Transactional Outbox:** en la misma transacción del agregado, insertar la intención del mensaje.
     ```sql
     BEGIN;
       INSERT INTO pedidos (...) VALUES (...);
       INSERT INTO outbox (id, aggregate_type, aggregate_id, event_type, payload, estado, creado_en)
       VALUES (gen_random_uuid(), 'Pedido', :pid, 'PedidoCreado', :json, 'PENDIENTE', now());
     COMMIT;   -- o existen ambos o ninguno
     ```
  2. **Relay** (worker/cron/consumidor interno): lee pendientes, publica, marca enviado, reintenta con backoff; el usuario ya recibió su 200 y el checkout no espera al broker; si el bus cae, los mensajes esperan en la tabla.
     ```sql
     -- (complemento) varios relays sin pisarse
     SELECT * FROM outbox WHERE estado='PENDIENTE' ORDER BY creado_en
     LIMIT 100 FOR UPDATE SKIP LOCKED;
     -- publish(key=aggregate_id, header message_id=id) → UPDATE outbox SET estado='ENVIADO'
     ```
  3. **Consumidor idempotente** (misma clave → mismo efecto): Outbox arregla la salida, no la entrega duplicada.
  4. **Alternativa CDC** (Debezium leyendo binlog/WAL): sin escribir outbox a mano; adecuado para equipos de plataforma maduros. Outbox explícito cuando se quiere control de payload, versionado, privacidad y pruebas claras.
  5. Operación: métrica de edad del pendiente más antiguo, alertas por umbral de lag, DLQ en el relay, runbook para atascos.
- **Trade-offs y cuándo NO aplicar:** latencia añadida (polling), tabla que crece (purga/particionado), un proceso más que operar, entrega at-least-once. CDC puro acopla el contrato público al esquema interno. No aplica si no hay BD transaccional local o si el servicio no tiene estado propio que deba coincidir con el evento.
- **Heurísticas y umbrales:** checklist de 6: outbox en la misma transacción que el agregado; worker con reintento y DLQ; consumidores idempotentes; métrica de edad del mensaje pendiente; alerta por lag sobre umbral; runbook sin héroes. Regla: "Outbox + idempotencia" es el dúo mínimo; uno sin el otro es media solución.
- **Anti-patrones / señales de alerta:** `repo.save(); broker.publish()` en el mismo handler (o al revés); publicar al bus dentro del request crítico "porque va más rápido"; asumir que perder el publish es aceptable si el pedido quedó guardado; sin métricas de lag del outbox; sin runbook; creer en exactly-once mágico.
- **Preguntas de revisión arquitectónica:**
  1. ¿Hay algún punto donde se escriba en BD y se publique sin atomicidad?
  2. ¿El relay preserva el orden por agregado (clave de partición = aggregate_id) y tolera varios workers?
  3. ¿Qué pasa si el relay publica y cae antes de marcar ENVIADO? ¿Los consumidores deduplican por message_id?
  4. ¿Cómo se purga la tabla outbox y se vigila su crecimiento?
  5. ¿Outbox explícito o CDC, y por qué (control de contrato vs. esfuerzo)?
  6. ¿Qué alerta dispara la edad del pendiente más antiguo?
- **Caso real / empresa citada:** Shopify (eventos asíncronos, retrasos, reintentos, orden imperfecto → dedupe y reconciliación contra API), Uber (publicación fiable a escala), ING y Maersk (citados como casos enterprise), Stripe (idempotencia), Microsoft Learn (transactional outbox).
- **Precisión técnica:**
  - Outbox resuelve ambos escenarios (si hay rollback, la fila outbox también se revierte), pero introduce duplicados en la publicación (crash entre publish y marcado) → at-least-once obligatorio (complemento).
  - Con varios relays, el orden global se pierde; ordenar por agregado y usar la misma clave de partición (complemento).
  - Las transacciones de Kafka (EOS) no abarcan la BD; no sustituyen al Outbox (complemento).
  - Outbox y CDC no son excluyentes: Debezium Outbox Event Router lee la tabla outbox por CDC (sin polling y con contrato explícito) (complemento).
  - Citas a ING y Maersk: atribución genérica, no verificada en el video.
