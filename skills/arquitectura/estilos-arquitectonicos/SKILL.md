---
name: estilos-arquitectonicos
description: Criterio de arquitecto para elegir estilos y topologías — monolito modular vs microservicios, microfrontends (iframes, Module Federation), API Gateway y BFF, fan-out on write vs on read para feeds y seguidores, modelo de actores (Erlang/BEAM) para millones de conexiones, y tiempo real (polling, long polling, SSE, WebSocket) — con casos reales (Spotify, Twitter/Instagram, WhatsApp, Prime Video, Uber). Úsala siempre que se discuta cómo partir o no un sistema, si "migrar a microservicios", cómo servir un feed o timeline, cómo empujar datos en vivo al navegador, cómo exponer servicios a clientes, o cómo diseñar un sistema estilo red social o chat, aunque el usuario no use estos términos.
license: MIT
metadata:
  categoria: arquitectura
  version: "1.0.0"
  idioma: es
  fuentes: "TheDebugDuck: 08, 14, 15, 18, 22, 46"
  relacionadas: "consistencia-distribuida, resiliencia-operacion, radar-arquitectura"
---

# Estilos arquitectónicos y diseño de sistemas reales

Conocimiento destilado de TheDebugDuck (videos 08, 14, 15, 18, 22, 46) con correcciones. Tesis del canal: **la complejidad solo se justifica con un dolor presente y medible**, y los híbridos pragmáticos que tratan aparte los casos extremos le ganan a las arquitecturas puras.

## Cómo usar esta skill

1. Antes de proponer un estilo, obtén los **drivers**: tamaño y número de equipos, fase del producto, perfil de carga (lecturas/escrituras, distribución, picos), madurez operativa (CI, logs, tracing) y el dolor concreto de hoy.
2. Cruza con la matriz y los criterios de complejidad justificada.
3. Lee la referencia del caso que más se parece; cada una trae mecanismo, umbrales, anti-patrones y correcciones del caso real.
4. Entrega la decisión con el formato de salida, preferentemente como ADR con alternativas descartadas y condición de revisión.

## Índice de referencias

| Tema | Archivo | Léelo cuando… |
|---|---|---|
| Monolito modular vs microservicios, Conway, Prime Video | `references/08-monolito-vs-microservicios.md` | "¿partimos en microservicios?", extracción de módulos, fronteras |
| Microfrontends, iframes, Module Federation (Spotify) | `references/14-microfrontends-iframes-spotify.md` | varios equipos en una misma UI, despliegue independiente de frontend |
| Fan-out on write vs on read, celebridades (Twitter/Instagram) | `references/15-fan-out-seguidores.md` | feeds, timelines, notificaciones a seguidores |
| Actores, supervisión, millones de conexiones (WhatsApp/Erlang) | `references/18-whatsapp-erlang.md` | chat, presencia, conexiones persistentes masivas, aislamiento de fallos |
| Polling vs long polling vs SSE vs WebSocket | `references/22-polling-websocket-sse.md` | dashboards en vivo, notificaciones, colaboración, chat |
| API Gateway, BFF, responsabilidades del borde | `references/46-api-gateway.md` | exponer microservicios a clientes, auth en el borde, agregación |

## Criterios de complejidad justificada

Acepta un estilo más complejo solo si se cumplen **todos**:

1. **El problema existe hoy** (contención de equipos medida, carga que no cabe, SLO incumplido), no "por si mañana".
2. **Se agotó la opción simple** con datos (índices, caché, tuning, monolito modular con fronteras, polling bien hecho).
3. **Se paga el coste operativo completo**: CI estable, logs, tracing, alertas, on-call. Sin esa base, distribuir multiplica el dolor.
4. **La complejidad se localiza en el outlier** (una cuenta celebridad, un módulo con carga 10×, un runtime distinto), no se aplica a todo el sistema.
5. **Se des-riesga antes de comprometerse**: spike con fecha y criterio de éxito (Spotify: 3 meses); prefiere decisiones reversibles.
6. **Un tercero sigue el flujo en una guardia sin tour guiado.** Cada salto de red o de indirección es un coste explícito.

## Matriz "si ves X → considera Y"

| Si ves… | Considera… |
|---|---|
| Equipo ≤ 20, producto sin validar, microservicios "para escalar" | Monolito modular con fronteras impuestas por herramientas (módulos, reglas de dependencia, DTO en fronteras); extraer después |
| > 50 devs, varios equipos bloqueados en el mismo despliegue | Servicios alineados a equipos/dominios; la zona 20–50 se decide con métricas de contención (conflictos de merge, releases congelados, lead time) |
| Un módulo con carga 10× o runtime distinto (ML, video) | Extraer solo ese módulo |
| Lentitud atribuida "al monolito" | Perfilar primero: índices, algoritmos, N+1. Distribuir no baja la latencia |
| Transacción de negocio que cruzaría bases de servicios | Mantener ACID local o saga + outbox + idempotencia (ver `consistencia-distribuida`) |
| Feed read-heavy con seguidores distribuidos uniformemente | Fan-out on write (timelines precalculados) |
| Distribución de seguidores con cola larga (celebridades) | Híbrido push/pull por umbral de seguidores + coalescing en el read path |
| Recurso caliente leído por millones a la vez | Request coalescing, caché replicada, rate limit, jitter |
| Dashboard actualizado por minuto y cacheable | Polling con ETag/304 + backoff exponencial con tope |
| Push unidireccional servidor → navegador (métricas, logs, notificaciones) | SSE con `Last-Event-ID`; vigilar límite de conexiones en HTTP/1.1 y buffering de proxies |
| Interacción bidireccional de baja latencia (chat, colaboración, juego) | WebSocket + heartbeat (< timeout de inactividad del LB, p. ej. 30 s frente a 60 s) + reconexión con backoff + pub/sub entre nodos |
| Evento de un SaaS hacia tu backend | Webhook entrante (y luego SSE/WS/polling hacia el usuario) |
| Millones de conexiones persistentes con fallos locales frecuentes | Actores/procesos ligeros + supervisores (BEAM, Akka, Orleans) |
| Muchos equipos en la misma UI con stacks divergentes | ¿Separar el **despliegue** o el **código**? Evalúa un codebase + API de plataforma, o Module Federation con singletons compartidos y pruebas de composición |
| Clientes que llaman a N servicios y agregan en el móvil | API Gateway para preocupaciones transversales; BFF por tipo de cliente si las necesidades divergen |
| Gateway con reglas de negocio o que encadena llamadas con efectos | Gateway delgado; lógica en los servicios y orquestación en una saga (ver `consistencia-distribuida`) |

## Principios recurrentes

- **Conway manda**: microservicios y microfrontends resuelven problemas de organización, no de velocidad de CPU. Usa la maniobra inversa de Conway (diseñar equipos para la arquitectura deseada).
- **La física no se negocia**: llamada en memoria (ns) vs red (ms); coste por conexión (hilo vs proceso ligero); coste por request de polling.
- **Mueve el trabajo al path correcto** según el perfil de carga: write path vs read path, verificación local vs consulta central, siempre con el ratio y la distribución en la mano.
- **Trata distinto a los outliers** (celebridades, módulos calientes, picos sincronizados) en vez de diseñar todo para el peor caso.
- **Aísla estado y fallos**: actores sin memoria compartida + supervisores; fronteras de módulo con DTO; nada de singletons mutables globales.
- **Diseña la falla antes del incidente**: reconexión y heartbeat, "let it crash" con supervisión, compensaciones.

## Preguntas de revisión

1. ¿Qué dolor medible de hoy resuelve este estilo y qué opción simple se descartó con qué datos?
2. ¿Cómo se mapean servicios o microfrontends a equipos? ¿Quién es dueño de cada frontera?
3. ¿Qué operaciones de negocio cruzan fronteras y cómo se mantiene la consistencia?
4. ¿Cuál es la distribución de la carga (no solo el promedio): seguidores por autor, conexiones por nodo, lecturas/escrituras?
5. ¿Qué pasa con las conexiones persistentes en un deploy, un corte de red o un timeout del LB?
6. ¿Qué responsabilidades tiene el gateway y cuáles no debe tener (lógica de negocio)?
7. ¿Cuál es la condición de revisión de esta decisión (umbral que obligaría a cambiarla)?

## Precisiones que los videos simplifican (no las repitas)

- Microservicios no bajan la latencia, pero pueden mejorar el throughput (escalar solo el punto caliente) y la frecuencia de despliegue independiente.
- Prime Video no "volvió al monolito" como plataforma: un servicio de monitoreo pasó de Step Functions + S3 a un proceso, bajando ~90 % su coste; sigue escalando horizontalmente.
- En fan-out on write, las escrituras dependen de los **seguidores del autor**, no de a cuántas cuentas sigues.
- Grafana Live usa **WebSocket** (Centrifuge), no SSE. Falta a menudo **long polling** como punto intermedio.
- Actores eliminan races de memoria, no races de orden de mensajes ni deadlocks por llamadas síncronas mutuas. Concurrencia ≠ paralelismo.
- WhatsApp: ~32 ingenieros/~450 M usuarios en 2014; 50/900 M es de 2015; ~2 M conexiones/servidor es de 2012.
- Gateway ≠ load balancer ≠ service mesh (tráfico norte-sur frente a este-oeste). Autenticar en el borde no es autorizar: la autorización por objeto sigue en cada servicio.
- Spotify no adoptó Module Federation: convergió a un único codebase React. Shadow DOM no aísla JS global y deja pasar propiedades heredadas.

## Formato de salida

```
Decisión: <estilo/topología>, en una línea.
Drivers: <equipo, fase, carga, madurez operativa, dolor medido>.
Alternativas descartadas: <opción → por qué no, con dato>.
Dónde se localiza la complejidad: <outlier o frontera concreta>.
Coste operativo que se asume: <CI, observabilidad, on-call, consistencia>.
Condición de revisión: <umbral que obligaría a reconsiderar>.
Fuente: <referencia(s) y video(s)>.
```
