# Arquitectura

<!-- Generado por scripts/build_catalog.py a partir del frontmatter. No editar a mano. -->

Decisiones estructurales: estilos y topologías, consistencia entre componentes y revisión de riesgos de diseño.

| Skill | Qué resuelve | Relacionadas |
|---|---|---|
| [`consistencia-distribuida`](consistencia-distribuida/SKILL.md) | Criterio de arquitecto para consistencia y mensajería en sistemas distribuidos — Outbox, Inbox/deduplicación, idempotencia, Saga (orquestación vs coreografía), CQRS, Dead Letter Queue, webhooks, consistencia eventual, read-your-writes, race conditions,… | `datos-persistencia`, `resiliencia-operacion`, `radar-arquitectura` |
| [`estilos-arquitectonicos`](estilos-arquitectonicos/SKILL.md) | Criterio de arquitecto para elegir estilos y topologías — monolito modular vs microservicios, microfrontends (iframes, Module Federation), API Gateway y BFF, fan-out on write vs on read para feeds y seguidores, modelo de actores (Erlang/BEAM) para millones… | `consistencia-distribuida`, `resiliencia-operacion`, `radar-arquitectura` |
| [`radar-arquitectura`](radar-arquitectura/SKILL.md) | Punto de entrada del arquitecto para diagnosticar incidentes de producción y revisar diseños, PRs o repositorios en busca de riesgos arquitectónicos, con el método de TheDebugDuck (síntoma → rastro → mecanismo → solución en capas → verificación). Incluye… | `datos-persistencia`, `consistencia-distribuida`, `resiliencia-operacion`, `estilos-arquitectonicos`, `contratos-api`, `seguridad-aplicaciones`, `diseno-de-codigo`, `sistemas-con-ia`, `comunicar-decisiones` |

Volver al [catálogo](../README.md).
