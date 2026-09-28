---
name: consistencia-distribuida
description: Criterio de arquitecto para consistencia y mensajería en sistemas distribuidos — Outbox, Inbox/deduplicación, idempotencia, Saga (orquestación vs coreografía), CQRS, Dead Letter Queue, webhooks, consistencia eventual, read-your-writes, race conditions, locks distribuidos y reservas de recursos escasos. Úsala siempre que un diseño, ADR, PR o incidente involucre guardar y publicar eventos, flujos que cruzan varios servicios o bases, colas/brokers (Kafka, RabbitMQ, SQS, Service Bus), reintentos, cobros o stock duplicados, datos que "cambian al refrescar", doble venta, o la pregunta "¿cómo garantizo que esto pase exactamente una vez?", aunque el usuario no nombre el patrón.
license: MIT
metadata:
  categoria: arquitectura
  version: "1.0.0"
  idioma: es
  fuentes: "TheDebugDuck: 11, 23, 24, 26, 27, 28, 29, 33, 34"
  relacionadas: "datos-persistencia, resiliencia-operacion, radar-arquitectura"
---

# Consistencia distribuida y mensajería

Conocimiento destilado de TheDebugDuck (videos 11, 23, 24, 26, 27, 28, 29, 33, 34) y corregido donde el video simplifica. El objetivo no es recitar patrones sino **elegir el mínimo mecanismo que haga imposible el estado incorrecto**, y dejarlo operable (métricas, alertas, runbook).

## Cómo usar esta skill

1. Identifica el **tipo de riesgo** del diseño o incidente con la matriz de abajo.
2. Lee **solo** la referencia del patrón implicado (tabla de índice). Cada una trae síntoma, mecanismo, solución con pseudocódigo, trade-offs, anti-patrones, preguntas de revisión y precisiones técnicas.
3. Entrega la recomendación con el formato de salida del final. Si el repositorio tiene proceso de ADR o registro de hallazgos, la decisión va a un ADR y lo que no se cierre en el cambio, al registro de hallazgos.

## Índice de referencias

| Tema | Archivo | Léelo cuando… |
|---|---|---|
| Reserva de recurso escaso multi-región, locks, CAP | `references/11-reservas-globales.md` | stock/asiento/habitación vendidos desde varios nodos o regiones; alguien propone Redlock |
| Consistencia eventual, lag de réplica, read-your-writes | `references/23-consistencia-eventual.md` | "el dato cambia al refrescar", réplicas de lectura, reportes que no cuadran |
| Dead Letter Queue, poison messages, redrive | `references/24-dead-letter-queue.md` | colas atascadas, mensajes que fallan siempre, diseño de consumidores |
| CQRS, proyecciones, read models | `references/26-cqrs.md` | separar lecturas/escrituras, vistas materializadas, replay |
| Saga, compensaciones, pivot, orquestación vs coreografía | `references/27-saga.md` | procesos de negocio que cruzan ≥2 servicios con dinero o inventario |
| Transactional Outbox, dual write, CDC | `references/28-outbox.md` | cualquier "guardar en BD y publicar en broker" |
| Webhooks entrantes, Inbox, firma HMAC | `references/29-webhooks-duplicados.md` | recibir eventos de Stripe/GitHub/Shopify/etc. |
| Race conditions, lost update, atomicidad | `references/33-race-conditions.md` | read-modify-write, contadores, inventario, "dos clics al mismo tiempo" |
| Idempotencia, Idempotency-Key, dobles cobros | `references/34-idempotencia.md` | POST con efectos, pagos, reintentos del cliente |

## Principios no negociables (y por qué)

- **Asume entrega at-least-once en todas partes.** Red, broker, webhooks, redrive y el doble clic del usuario reentregan. "Exactly-once" de extremo a extremo no existe; lo que existe es *efectivamente una vez* = at-least-once + consumidor idempotente.
- **La clave de idempotencia nace en el origen del intento lógico**, no en cada reintento ni en el servidor. Si se regenera por reintento, no deduplica nada.
- **Nunca dual write.** Cambiar estado y avisar al mundo debe ser atómico (Outbox o CDC). Aplica también al estado de un orquestador de sagas y al offset de un proyector CQRS.
- **La marca de "ya procesado" se confirma en la misma transacción que el efecto.** Insertar el ID y luego procesar pierde eventos si el proceso cae en medio; procesar y luego insertar duplica.
- **Recurso escaso ⇒ un único punto de serialización**: restricción de BD (UNIQUE/EXCLUDE), dueño único por clave (región "hogar") o lock con consenso y *fencing token*. Un `SELECT` previo para "ver si existe" no protege nada: la restricción es la que evita la carrera.
- **No hay rollback global entre servicios.** Transacciones locales + compensaciones de negocio idempotentes + estado durable + *pivot* explícito (antes del pivot se compensa; después, solo se reintenta hacia adelante).
- **La consistencia eventual es un contrato operable, no una excusa**: lag medido, SLA por consumidor, alerta, lecturas versionadas/as-of, read-your-writes para el autor y UX que muestra frescura.
- **Aísla el fallo en lugar de propagarlo**: DLQ con umbral, ack rápido + cola, reintentos con techo y backoff, backpressure.
- **Correlación extremo a extremo** (order/command/message/event ID). Los fallos son del flujo; los dashboards por servicio mienten por omisión.
- **Patrón sin operación es deuda.** Cada patrón exige su métrica: edad del pendiente más antiguo del outbox, lag del proyector, profundidad DLQ > 0, sagas atascadas en COMPENSATING.
- **Decide la política bajo fallo antes del incidente**: por operación de negocio, ¿rechazar, encolar o aceptar y reparar? (CAP/PACELC aplicado, con el coste aceptado por negocio).

## Matriz "si ves X → considera Y"

| Si ves… | Considera… | Evita… |
|---|---|---|
| `repo.save(); broker.publish()` en el mismo handler (o al revés) | Transactional Outbox + relay con `FOR UPDATE SKIP LOCKED`; o CDC (Debezium Outbox Router) si hay plataforma madura | publicar dentro del request crítico |
| Proceso de negocio que cruza ≥2 servicios con dinero/stock | Saga con compensaciones, estado durable y pivot | cadena HTTP en serie desde el gateway; 2PC entre servicios heterogéneos |
| Saga de 2–3 participantes, flujo lineal y estable | Coreografía por eventos | coreografía cuando on-call necesita "ver" el flujo |
| Saga larga, con ramas, timeouts humanos o auditoría | Orquestación (Temporal/Cadence, Step Functions) | orquestador con estado en memoria |
| Atomicidad entre 2 recursos XA, mismo DC, transacción corta | 2PC aceptable (caso raro) | 2PC con brokers, SaaS, HTTP o entre regiones |
| Recurso escaso vendido desde varias regiones | dueño único por recurso + restricción de BD; lock con consenso (etcd/ZooKeeper) y fencing solo si es imprescindible | multi-master con escritura local; Redlock como garantía de corrección |
| `SELECT` de disponibilidad seguido de `UPDATE` | `UPDATE ... SET stock = stock - 1 WHERE id=? AND stock > 0` (atómico condicional), `FOR UPDATE`, o versión optimista | locks en memoria del proceso cuando hay varias réplicas |
| Cliente móvil / doble clic reintenta un POST con efectos | `Idempotency-Key` del cliente + respuesta almacenada + 409 ante concurrencia y 422 ante la misma clave con otro cuerpo | clave generada por el servidor o por reintento |
| Invariante sobre varias filas (cupo, "máximo N por usuario") | SERIALIZABLE con reintento, o lock de la fila padre + restricción | `SELECT COUNT(*)` y luego `INSERT` |
| Consumidor de broker o receptor de webhook | Inbox / tabla de dedupe con `UNIQUE(event_id)` en la misma transacción que el efecto | `SELECT` previo para "ver si existe" |
| Mensaje que falla siempre con la misma traza | DLQ con umbral + alerta > 0 + redrive tras fix y reproducción en staging | reintento infinito; purgar la DLQ; reiniciar pods |
| Kafka / FIFO atascado en un offset o grupo | retry topics + DLQ topic; política explícita sobre el orden por clave | saltar mensajes sin registrar |
| El usuario no ve lo que acaba de guardar | read-your-writes: ventana al primario o token LSN/versión mínima | "refresca hasta que aparezca" |
| Valores que alternan al refrescar | lecturas monótonas: réplica fija por sesión o versión mínima | round-robin entre réplicas con lag distinto |
| Lecturas ≫ escrituras, formas muy distintas y contención medida | CQRS en un bounded context, tras agotar índices, réplicas y caché | CQRS en un CRUD pequeño |
| Reportes de equipos que no cuadran | snapshots as-of, versión en read models, métrica de frescura | totales que mezclan versiones |
| Endpoint de webhook con timeouts y ráfagas | ack 2xx inmediato + cola + workers con backpressure | procesar todo dentro del request |
| Lock con TTL en procesos que pueden pausarse (GC, VM) | fencing token validado por el almacenamiento | confiar solo en el TTL |

## Recetas de combinación

- **Pipeline "efectivamente una vez":** Outbox (productor) → broker at-least-once → consumidor con Inbox/dedupe → reintentos con backoff y techo → DLQ con alerta > 0 → redrive tras fix. El redrive es seguro *solo* porque el consumidor es idempotente.
- **Saga robusta:** orquestador con estado durable; cada comando sale por Outbox; cada participante deduplica por `saga_id + paso`; compensaciones idempotentes; pasos no compensables (email, notificación) después del pivot; métrica de sagas en COMPENSATING.
- **Reserva de recurso escaso:** Idempotency-Key del cliente → retención tentativa con TTL (*semantic lock*) → serialización (restricción o lock con fencing) → cobro (pivot) → confirmación → notificación reintentable. Compensaciones: liberar retención, reembolsar.
- **CQRS operable:** write model emite por Outbox/CDC → proyector idempotente (versión por agregado + offset en la misma transacción) → read model versionado con as-of → read-your-writes para el autor → SLA de lag y pruebas de replay.
- **Webhooks entrantes:** firma HMAC sobre el cuerpo crudo → `UNIQUE(event_id)` → 202 → worker → DLQ; reconciliación periódica contra la API del proveedor como red de seguridad.

La idempotencia es el pegamento: habilita reintentos, redrive, replay de proyecciones, compensaciones repetidas y webhooks duplicados. Si un diseño no dice dónde vive la idempotencia, el diseño está incompleto.

## Preguntas de revisión (usa las que apliquen)

1. ¿Hay algún punto donde se escriba en BD y se publique sin atomicidad?
2. ¿Quién genera la clave de idempotencia, cuánto se retiene y qué responde ante dos peticiones concurrentes con la misma clave?
3. ¿Dónde está la restricción que hace imposible el estado incorrecto aunque falle el lock o el código?
4. ¿Cuál es el pivot del flujo? ¿Qué pasos son compensables y cuáles solo reintentables? ¿Dónde se persiste el estado de la saga?
5. Bajo partición, ¿esta operación es CP (rechaza) o AP (acepta y reconcilia)? ¿Negocio aceptó ese coste por escrito?
6. ¿Qué lag tolera cada consumidor/pantalla y dónde está la alerta? ¿Cómo se garantiza read-your-writes?
7. ¿Cada cola tiene DLQ, umbral documentado, dueño de la alerta y runbook de redrive?
8. ¿Se puede seguir un ID de correlación desde el request hasta el efecto final en todos los servicios?
9. ¿Qué pasa si el relay/worker publica y cae antes de marcar como enviado?

## Precisiones que los videos simplifican (no las repitas)

- Un **único primario con UNIQUE/`FOR UPDATE` sí evita la doble venta global**; su coste es latencia inter-región y dependencia de la disponibilidad de esa región. La carrera solo existe si cada región decide localmente.
- **Redlock no emite tokens monótonos**: por sí solo no da fencing. etcd (revision) o ZooKeeper (zxid) sí. Distingue lock "por eficiencia" de lock "por corrección" (Kleppmann).
- **2PC/XA existe**; se descarta entre servicios por bloqueo del coordinador, latencia y falta de soporte en brokers y APIs HTTP, no porque sea imposible.
- **CQRS no exige bases separadas, eventos ni consistencia eventual.** Réplica de lectura ≠ CQRS.
- **Un poison message en una cola estándar (SQS standard) no bloquea toda la cola**; desperdicia capacidad. El bloqueo head-of-line ocurre con orden estricto (partición Kafka, SQS FIFO, sesiones de Service Bus).
- **GitHub no reintenta automáticamente webhooks fallidos**; se reenvían manual o vía API. Stripe sí reintenta (hasta ~3 días) y tolera ~5 min de desfase en la firma.
- **Las transacciones de Kafka (EOS) no abarcan tu base de datos**; no sustituyen al Outbox.
- Las sagas no tienen aislamiento (ACD sin I): usa contramedidas (semantic lock, actualizaciones conmutativas, relectura de valor).
- REPEATABLE READ no da la misma garantía en todos los motores: PostgreSQL aborta el lost update (40001); MySQL/InnoDB no lo detecta (hace falta `FOR UPDATE` o UPDATE condicional). Abrir una transacción con el nivel por defecto no evita el read-modify-write.
- `Idempotency-Key` es un borrador IETF, no un RFC. La idempotencia de PUT/DELETE (RFC 9110) es del efecto, no de la respuesta, y no protege de escrituras concurrentes distintas (usa `If-Match`/versión).

## Formato de salida

Cuando recomiendes algo de este dominio, entrega:

```
Decisión: <patrón/mecanismo mínimo>, en una línea.
Estado imposible que garantiza: <qué ya no puede pasar y qué lo impone (restricción, transacción, token)>.
Mecanismo: <3–6 pasos o pseudocódigo>.
Trade-offs aceptados: <latencia, complejidad, consistencia eventual, crecimiento de tablas>.
Operación: <métricas + umbral de alerta + runbook>.
Cuándo NO: <condición en la que este patrón sobra>.
Fuente: <referencia(s) y video(s) usados>.
```
