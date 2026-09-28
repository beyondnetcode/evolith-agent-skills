# Catálogo de skills

<!-- Generado por scripts/build_catalog.py a partir del frontmatter. No editar a mano. -->

10 skills en 8 categorías. Cada skill funciona sola; `metadata.relacionadas` indica con cuáles se combina.

## [Arquitectura](arquitectura/README.md)

Decisiones estructurales: estilos y topologías, consistencia entre componentes y revisión de riesgos de diseño.

| Skill | Qué resuelve | Versión |
|---|---|---|
| [`consistencia-distribuida`](arquitectura/consistencia-distribuida/SKILL.md) | Criterio de arquitecto para consistencia y mensajería en sistemas distribuidos — Outbox, Inbox/deduplicación, idempotencia, Saga (orquestación vs coreografía), CQRS, Dead Letter Queue, webhooks, consistencia eventual, read-your-writes, race conditions,… | 1.0.0 |
| [`estilos-arquitectonicos`](arquitectura/estilos-arquitectonicos/SKILL.md) | Criterio de arquitecto para elegir estilos y topologías — monolito modular vs microservicios, microfrontends (iframes, Module Federation), API Gateway y BFF, fan-out on write vs on read para feeds y seguidores, modelo de actores (Erlang/BEAM) para millones… | 1.0.0 |
| [`radar-arquitectura`](arquitectura/radar-arquitectura/SKILL.md) | Punto de entrada del arquitecto para diagnosticar incidentes de producción y revisar diseños, PRs o repositorios en busca de riesgos arquitectónicos, con el método de TheDebugDuck (síntoma → rastro → mecanismo → solución en capas → verificación). Incluye… | 1.0.0 |

## [Datos](datos/README.md)

Modelado, persistencia, rendimiento de bases de datos y elección o migración de motores.

| Skill | Qué resuelve | Versión |
|---|---|---|
| [`datos-persistencia`](datos/datos-persistencia/SKILL.md) | Criterio de arquitecto para persistencia y rendimiento de datos — paginación OFFSET vs keyset/cursor, elección de identificadores (bigint, UUIDv4, UUIDv7, Snowflake, ID público opaco), índices y coste de escritura, ORM bien usado (N+1, explosión… | 1.0.0 |

## [Operación](operacion/README.md)

Resiliencia, capacidad, despliegue y comportamiento del software en producción.

| Skill | Qué resuelve | Versión |
|---|---|---|
| [`resiliencia-operacion`](operacion/resiliencia-operacion/SKILL.md) | Criterio de arquitecto para resiliencia, capacidad y operación en producción — circuit breaker, timeouts, reintentos con backoff y jitter, bulkheads, rate limiting (token/leaky bucket), load balancing, health checks, cache stampede, filas virtuales para… | 1.0.0 |

## [APIs y contratos](apis/README.md)

Contratos de integración: evolución y versionado, semántica HTTP, formatos de fecha y datos.

| Skill | Qué resuelve | Versión |
|---|---|---|
| [`contratos-api`](apis/contratos-api/SKILL.md) | Criterio para diseñar, evolucionar y revisar contratos de API HTTP — breaking changes (incluidos los semánticos que responden 200 OK), versionado por URL, header, query o media type, expand/contract y tolerant reader, deprecación y sunset (headers… | 1.0.0 |

## [Seguridad](seguridad/README.md)

Seguridad de aplicaciones: autenticación, sesiones y tokens, validación de entradas y archivos.

| Skill | Qué resuelve | Versión |
|---|---|---|
| [`seguridad-aplicaciones`](seguridad/seguridad-aplicaciones/SKILL.md) | Criterio de diseño seguro para aplicaciones — validación de archivos subidos (magic bytes, Content-Type decidido por el servidor, nosniff, attachment, dominio sandbox, cuarentena, políglotas, SVG/HTML/Office/PDF) y autenticación con tokens (JWT de vida… | 1.0.0 |

## [Código](codigo/README.md)

Diseño de código: principios, abstracciones justificadas y complejidad algorítmica.

| Skill | Qué resuelve | Versión |
|---|---|---|
| [`diseno-de-codigo`](codigo/diseno-de-codigo/SKILL.md) | Criterio para diseñar y revisar código barato de cambiar — SOLID (SRP por actor, OCP, LSP por contratos, ISP, DIP) aplicado con evidencia, abstracción justificada frente a sobreingeniería (YAGNI, regla de tres, singletons, interfaces con una sola… | 1.0.0 |

## [IA](ia/README.md)

Diseño de sistemas y agentes con LLMs: contexto, tokens, memoria y costes.

| Skill | Qué resuelve | Versión |
|---|---|---|
| [`sistemas-con-ia`](ia/sistemas-con-ia/SKILL.md) | Criterio de arquitecto para diseñar sistemas y agentes con LLMs tratando contexto y tokens como recursos finitos y caros — ventana de contexto, estado y memoria de corto y largo plazo, RAG y recuperación, carga progresiva, compactación, recorte de… | 1.0.0 |

## [Comunicación](comunicacion/README.md)

Comunicar decisiones técnicas: ADRs, postmortems, propuestas y explicaciones para cualquier audiencia.

| Skill | Qué resuelve | Versión |
|---|---|---|
| [`comunicar-decisiones`](comunicacion/comunicar-decisiones/SKILL.md) | Técnica narrativa de TheDebugDuck para explicar decisiones y riesgos de arquitectura — incidente concreto como gancho, "todo está verde pero algo falla", modo detective siguiendo un ID, metáfora visual cotidiana, mecanismo real, solución en capas,… | 1.0.0 |
