# [27] Saga Pattern explicado fácil | El rollback de microservicios

> Fuente: TheDebugDuck — https://youtu.be/Gbm64asnDsI · notas parafraseadas; «(complemento)» = conocimiento añadido o corrección.

- **Síntoma en producción:** app del pasajero "confirmado", pagos en verde, pero operaciones no tiene viaje (sin asiento, conductor ni registro). Dobles cargos en tickets, viajes fantasma, runbooks de 30 pasos, dashboards verdes servicio por servicio; cada equipo defiende su panel porque el bug es del flujo completo. En los logs apenas un timeout.
- **Causa raíz (mecanismo):** 5 pasos en 5 servicios (inventario, pago, asiento, viaje, email) orquestados por el API Gateway en serie HTTP; cada uno hace commit en su BD. Si el paso 4 falla, los 3 anteriores ya ganaron y no existe rollback cruzado. Además los reintentos (cliente, gateway) sin idempotencia duplican cargos y reservas: efecto dominó.
- **Metáfora visual del video:** estaciones en fila con un hueco entre la estación 3 y la 4; modo detective siguiendo el Order ID por cuatro mundos.
- **Estrategias / solución:**
  1. Saga = secuencia de transacciones locales; ante fallo, **compensaciones** en orden inverso (liberar, reembolsar, cancelar). Compensar no es borrar filas ajenas: es una operación de negocio inversa e idempotente.
  2. **Punto de no retorno (pivot):** antes, compensar hacia atrás; después, solo reintentar o corregir hacia delante.
  3. **Estado durable de la saga:** PENDING/COMPLETED/COMPENSATING, paso actual, fallo, reintentos; permite retomar tras reinicio de pod y alertar sagas atascadas.
  4. Coordinación: **coreografía** (servicios reaccionan a eventos; pocos participantes, reglas claras) u **orquestación** (motor central; procesos largos, muchas ramas, un solo lugar para on-call).
  5. Correlación por Order ID en todos los servicios.
  ```
  Orquestador (reescrito):
  RESERVAR_INVENTARIO ok → COBRAR ok → ASIGNAR_ASIENTO ok → CREAR_VIAJE ✗
    → estado=COMPENSATING
    → LIBERAR_ASIENTO → REEMBOLSAR → LIBERAR_INVENTARIO   (inverso, idempotentes, con reintento)
    → estado=COMPENSATED | FAILED_NEEDS_HUMAN
  ENVIAR_EMAIL solo tras el pivot (no es compensable)      # (complemento)
  ```
- **Trade-offs y cuándo NO aplicar:** más diseño (una compensación por paso), consistencia eventual y estados intermedios visibles. Coreografía escala mal en visibilidad con muchos participantes (flujo implícito); orquestación centraliza lógica y crea dependencia del motor. No aplicar si el proceso vive en una sola BD (usar transacción local). No usar 2PC por "postura enterprise" en todo.
- **Heurísticas y umbrales:** coreografía para pocos participantes y flujo claro; orquestación para flujos largos/ramificados/críticos; alertar sagas que llevan horas en COMPENSATING. Checklist de 6: compensación por paso, log de saga durable, pasos idempotentes, DLQ y reintentos con backoff, métrica de sagas atascadas, runbook sin héroes.
- **Anti-patrones / señales de alerta:** API Gateway que encadena llamadas HTTP con efectos; compensar con DELETE en la BD de otro equipo; sagas sin idempotencia; compensaciones "para el lunes"; estado de saga en memoria; confundir at-least-once con exactly-once; no haber decidido coreografía vs orquestación ("la cadena HTTP decide por ti").
- **Preguntas de revisión arquitectónica:**
  1. ¿Cuál es el pivot del flujo y qué pasos son compensables vs. solo reintentables?
  2. ¿Cada compensación es idempotente, conmutativa respecto a reintentos y probada?
  3. ¿Dónde se persiste el estado de la saga y cómo se reanuda tras un crash?
  4. ¿Qué anomalías por falta de aislamiento son aceptables (p. ej., ver una reserva tentativa) y qué contramedida se usa?
  5. ¿Cómo se detectan y escalan sagas atascadas?
  6. ¿Por qué coreografía u orquestación en este contexto?
- **Caso real / empresa citada:** Shopify (fulfillment asíncrono con webhooks, colas, reintentos), Uber (orquestación de flujos largos con Cadence), Microsoft y AWS (compensating transaction, saga), Stripe (idempotency keys). Lecturas: *Microservices Patterns* (Richardson), *DDIA* (Kleppmann).
- **Precisión técnica:**
  - "No existe rollback global": 2PC/XA existe; se descarta por bloqueo del coordinador, latencia y falta de soporte en brokers/APIs HTTP (complemento).
  - Las sagas carecen de aislamiento (ACD): posibles lecturas sucias y actualizaciones perdidas; contramedidas de Richardson: *semantic lock*, actualizaciones conmutativas, relectura de valor, vista pesimista (complemento).
  - El orden inverso es convención; compensaciones independientes pueden correr en paralelo. Estructura recomendada: pasos compensables → pivot → pasos reintentables (complemento).
  - El orquestador debe actualizar su estado y emitir el siguiente comando sin dual write (Outbox) (complemento). Cadence tiene un fork mantenido, Temporal (complemento).
