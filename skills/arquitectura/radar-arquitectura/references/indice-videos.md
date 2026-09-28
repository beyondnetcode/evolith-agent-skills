# Índice de los 48 videos de TheDebugDuck

Cada fila: número (usado en los nombres de referencia `NN-tema.md`), título abreviado, skill donde vive, lección en una línea y estado de la fuente. **T** = analizado desde la transcripción; **D** = elaborado desde el título y el temario público (transcripción bloqueada el 2026-09-28; pendiente de contrastar).

| # | Video | Skill | Lección | Fuente |
|---|---|---|---|---|
| 01 | [Paginar con OFFSET en tablas de millones](https://youtu.be/Es25hxA4A64) | `datos-persistencia` | Una página profunda cuesta lo que descarta; usa keyset con cursor opaco. | T |
| 02 | [Validar archivos](https://youtu.be/olhSxQL8GYc) | `seguridad-aplicaciones` | Nombre y MIME los decide quien envía; inspecciona bytes y controla cómo se sirve. | T |
| 03 | [UUIDs y rendimiento de la BD](https://youtu.be/KiuZT8XYYdw) | `datos-persistencia` | El tipo de ID se elige por topología, visibilidad y generación; UUIDv4 fragmenta un B-tree. | T |
| 04 | [Heap vs RSS: OOMKilled](https://youtu.be/Y4ykSwM71bA) | `resiliencia-operacion` | El kernel mata por memoria total del proceso; heap al 70–80 % del límite. | T |
| 05 | [Tu async no es paralelo](https://youtu.be/97p_mrF6_bA) | `resiliencia-operacion` | `await` en bucle suma RTTs; batch primero, luego concurrencia acotada. | T |
| 06 | [Tu ORM no es lento](https://youtu.be/sOsCAIbhxOY) | `datos-persistencia` | ORM con sesión para escribir agregados; proyecciones para leer. | T |
| 07 | [Código "limpio" que arruina el proyecto](https://youtu.be/NTA6Nt2TSNw) | `diseno-de-codigo` | Abstrae solo con ≥2 variantes reales; si hace falta un tour guiado, sobra una capa. | T |
| 08 | [Microservicios desde el día 1](https://youtu.be/JgrsAyefLFU) | `estilos-arquitectonicos` | Monolito modular hasta que el equipo o la carga lo exijan. | T |
| 09 | [BD para miles de usuarios (pool)](https://youtu.be/UJnsiQk11Dc) | `datos-persistencia` | Pool pequeño y con timeout supera a uno grande; 504 con BD tranquila = fuga de conexiones. | T |
| 10 | [La regex que tumbó medio Internet](https://youtu.be/G_nth-0hbLA) | `resiliencia-operacion` | Motor lineal, timeout, límite de longitud y rollout escalonado también para config. | T |
| 11 | [Reservas globales](https://youtu.be/O9w-cFf21lg) | `consistencia-distribuida` | Recurso escaso = un punto de serialización + idempotencia + saga. | T |
| 12 | [Error de diseño con JWT](https://youtu.be/DjwejUgsu5I) | `seguridad-aplicaciones` | Access corto, refresh revocable, cookie HttpOnly: diseña la revocación primero. | T |
| 13 | [Rendimiento de INSERT](https://youtu.be/-QIMNVAE2c0) | `datos-persistencia` | Cada índice cobra en cada escritura; mide selectividad antes de crearlo. | T |
| 14 | [Spotify: microfrontends con iframes](https://youtu.be/fQbzSQosVh8) | `estilos-arquitectonicos` | ¿Separar el despliegue o el código? No es lo mismo. | T |
| 15 | [Cuentas con millones de seguidores](https://youtu.be/fCf6_aVkz9w) | `estilos-arquitectonicos` | Fan-out híbrido: push para la mayoría, pull para celebridades. | T |
| 16 | [IDs de Instagram (Snowflake)](https://youtu.be/-8WFjecvWQU) | `datos-persistencia` | 64 bits = tiempo + shard + secuencia, sin coordinador central. | T |
| 17 | [Discord: por qué falló Cassandra](https://youtu.be/_LTWThujNwk) | `datos-persistencia` | Working set en RAM, particiones calientes, tombstones; migrar con capa de acceso. | T |
| 18 | [WhatsApp y Erlang](https://youtu.be/RpKzma-EDG0) | `estilos-arquitectonicos` | Procesos aislados, mensajes y supervisores para millones de conexiones. | T |
| 19 | [Load balancing](https://youtu.be/o0kv2-GOBdU) | `resiliencia-operacion` | Capacidad = suma de réplicas sanas; health checks y algoritmo correcto. | T |
| 20 | [Actualizar en producción sin que se note](https://youtu.be/0QsGouoEy-k) | `resiliencia-operacion` | Rolling/blue-green/canary con gates y expand/contract; deploy ≠ release. | T |
| 21 | [Filas virtuales](https://youtu.be/dPBVU-JnYzs) | `resiliencia-operacion` | La fila convierte un golpe en un chorro; admisión adaptativa. | T |
| 22 | [Polling, WebSocket y SSE](https://youtu.be/D2-BNfHcD8M) | `estilos-arquitectonicos` | Transporte según dirección y frecuencia; heartbeat y reconexión desde el día 1. | T |
| 23 | [Consistencia eventual](https://youtu.be/v3I_C5UwpcI) | `consistencia-distribuida` | Mide el lag, garantiza read-your-writes y muestra frescura. | T |
| 24 | [Dead Letter Queue](https://youtu.be/A9EsyymseL8) | `consistencia-distribuida` | DLQ con umbral, alerta > 0 y redrive tras fix. | T |
| 25 | [El peligro del UPDATE](https://youtu.be/7nVmbbiszqY) | `datos-persistencia` | Si hay que demostrar qué pasó, log de eventos o auditoría, no sobrescritura. | T |
| 26 | [CQRS](https://youtu.be/srn3gx_Ot0k) | `consistencia-distribuida` | Separa modelos solo con contención medida; proyector idempotente y lag con SLA. | T |
| 27 | [Saga Pattern](https://youtu.be/Gbm64asnDsI) | `consistencia-distribuida` | Transacciones locales + compensaciones + pivot + estado durable. | T |
| 28 | [Outbox Pattern](https://youtu.be/aWUpXYlypYA) | `consistencia-distribuida` | Guardar y publicar en la misma transacción; consumidor idempotente. | T |
| 29 | [Webhooks que duplican eventos](https://youtu.be/fF4O4Jqkc0g) | `consistencia-distribuida` | Ack rápido + cola + dedupe por event_id + firma sobre cuerpo crudo. | T |
| 30 | [Cache stampede](https://youtu.be/YIMF4w7PFpM) | `resiliencia-operacion` | Jitter, single-flight y stale-while-revalidate contra la sincronía. | T |
| 31 | [Circuit breaker](https://youtu.be/krvH-jiE1m0) | `resiliencia-operacion` | Timeout + breaker + bulkhead + fallback; el breaker es local al cliente. | T |
| 32 | [API versioning: 200 OK pero el contrato cambió](https://youtu.be/hJiCokA2Sps) | `contratos-api` | Todo cambio incompatible se versiona, se depreca con aviso y se retira con fecha. | D |
| 33 | [Race conditions: 1 unidad, 2 ventas](https://youtu.be/mEc5a36Mg3Q) | `consistencia-distribuida` | Read-modify-write pierde actualizaciones; atomicidad o restricción en la BD. | D |
| 34 | [Idempotencia contra dobles cobros](https://youtu.be/DGSsZ1PWlr0) | `consistencia-distribuida` | Clave del cliente por intento lógico + respuesta almacenada. | D |
| 35 | [¿Por qué todo está en UTC?](https://youtu.be/YHHhS37JABg) | `contratos-api` | Instantes en UTC; eventos futuros con hora local + zona IANA. | D |
| 36 | [N+1 queries](https://youtu.be/T3zUdZGe7mk) | `datos-persistencia` | Una query por fila es O(N); fetch join, EntityGraph, batch o proyección. | D |
| 37 | [Códigos HTTP](https://youtu.be/o9WXg3gq64c) | `contratos-api` | El código de estado es contrato: clientes, LB y métricas dependen de él. | D |
| 38 | [Rate limiting](https://youtu.be/LfyObrcgvT8) | `resiliencia-operacion` | Token bucket para ráfagas, leaky bucket para flujo; 429 con Retry-After. | D |
| 39 | [Complejidad algorítmica (Big O)](https://youtu.be/vVrI4bQMZhE) | `diseno-de-codigo` | Lo que funciona con 100 elementos puede no funcionar con 1 millón. | D |
| 40 | [SOLID en 10 minutos](https://youtu.be/0XBA8X4qvEA) | `diseno-de-codigo` | SOLID reduce el coste del cambio; úsalo con criterio, no por dogma. | D |
| 41 | [SOLID: DIP](https://youtu.be/TEuVwJDmmnc) | `diseno-de-codigo` | El dominio define la abstracción; la infraestructura la implementa. | D |
| 42 | [SOLID: ISP](https://youtu.be/NhivsfJ2GkE) | `diseno-de-codigo` | Interfaces pequeñas definidas por quien las usa. | D |
| 43 | [SOLID: LSP](https://youtu.be/DAlfu9_h6FE) | `diseno-de-codigo` | Un subtipo cumple el contrato de comportamiento, no solo la firma. | D |
| 44 | [SOLID: OCP](https://youtu.be/m_suSqqpBG4) | `diseno-de-codigo` | Extiende por variantes reales en vez de crecer un `if`/`switch`. | D |
| 45 | [SOLID: SRP](https://youtu.be/1pXHglGZY9A) | `diseno-de-codigo` | Una razón (un actor) para cambiar por módulo. | D |
| 46 | [¿Qué es un API Gateway?](https://youtu.be/cxN_vkyZuto) | `estilos-arquitectonicos` | Preocupaciones transversales en el borde; sin lógica de negocio. | D |
| 47 | [El contexto en agentes de IA](https://youtu.be/B5hqbG59kAQ) | `sistemas-con-ia` | El contexto es memoria de trabajo finita: se presupuesta y se carga por capas. | D |
| 48 | [Tokens en IA](https://youtu.be/NYRsNFvHciI) | `sistemas-con-ia` | Los tokens miden límite y coste; no son palabras. | D |
