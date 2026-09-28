---
name: resiliencia-operacion
description: Criterio de arquitecto para resiliencia, capacidad y operación en producción — circuit breaker, timeouts, reintentos con backoff y jitter, bulkheads, rate limiting (token/leaky bucket), load balancing, health checks, cache stampede, filas virtuales para picos, despliegues sin downtime (rolling, blue/green, canary, expand/contract), memoria en contenedores (OOMKilled, heap vs RSS), concurrencia async acotada y ReDoS. Úsala siempre que un diseño, ADR, PR, manifiesto de Kubernetes o incidente trate de caídas bajo carga, picos de tráfico, dependencias lentas, pods reiniciados, latencias que crecen, despliegues riesgosos o "subimos servidores y sigue cayendo", aunque el usuario no nombre el patrón.
license: MIT
metadata:
  categoria: operacion
  version: "1.0.0"
  idioma: es
  fuentes: "TheDebugDuck: 04, 05, 10, 19, 20, 21, 30, 31, 38"
  relacionadas: "consistencia-distribuida, seguridad-aplicaciones, radar-arquitectura"
---

# Resiliencia, capacidad y operación

Conocimiento destilado de TheDebugDuck (videos 04, 05, 10, 19, 20, 21, 30, 31, 38) y corregido donde el video simplifica. Idea central: **todo recurso es finito; si no pones tú el límite, lo pone otro de golpe** (el kernel, el pool, el proveedor, la CPU). El arquitecto decide dónde está cada límite, quién lo aplica y qué ve el usuario cuando se alcanza.

## Cómo usar esta skill

1. Clasifica el problema con la matriz (síntoma → mecanismo probable).
2. Lee **solo** la referencia implicada; trae mecanismo, configuración de ejemplo, umbrales, anti-patrones y correcciones de postmortems reales.
3. Recomienda con el formato de salida. Si hay proceso de ADR o registro de hallazgos en el repositorio, úsalo.

## Índice de referencias

| Tema | Archivo | Léelo cuando… |
|---|---|---|
| OOMKilled, heap vs RSS, límites de contenedor | `references/04-heap-vs-rss-oomkilled.md` | pods con exit 137, dimensionar `limits`, JVM/Node/Go/PHP en contenedores |
| Async ≠ paralelo, `await` en bucle, `Promise.all` sin límite | `references/05-async-no-es-paralelo.md` | latencia que crece con el tamaño del input; fan-out de llamadas remotas |
| ReDoS, backtracking, incidentes Cloudflare/Stack Overflow | `references/10-regex-redos.md` | regex sobre input de usuario, reglas WAF, validaciones |
| Load balancing, health checks, sticky sessions | `references/19-load-balancing.md` | un backend saturado y otros ociosos, escalado horizontal, readiness |
| Despliegue sin downtime: rolling, blue/green, canary, flags | `references/20-despliegues-sin-downtime.md` | estrategia de release, migraciones de esquema, rollback |
| Filas virtuales / waiting room | `references/21-filas-virtuales.md` | preventas, drops, picos sincronizados previsibles |
| Cache stampede, thundering herd, jitter, single-flight | `references/30-cache-stampede.md` | picos de misses, TTL, warm-up tras deploy |
| Circuit breaker, bulkhead, fallback | `references/31-circuit-breaker.md` | dependencia lenta que arrastra al resto |
| Rate limiting: token bucket, leaky bucket, 429 | `references/38-rate-limiting.md` | proteger APIs, cuotas por cliente, límites distribuidos |

## Principios (y por qué)

1. **Acota explícitamente cada recurso**: memoria del runtime por debajo del límite del contenedor, semáforos de concurrencia, timeouts en toda llamada y en toda regex, tasas de admisión. Un límite propio falla con un mensaje; uno ajeno falla con SIGKILL, EMFILE o CPU al 100 %.
2. **Mide con la métrica de quien aplica la política.** El kernel mata por working set/RSS, no por heap; el LB necesita colas y errores por backend, no CPU promedio; el canary necesita conversión y p99, no CPU; la caché necesita ráfagas de miss.
3. **Decide aguas arriba.** Rechazar en el edge (fila, rate limit), fallar rápido (breaker), agrupar antes de iterar (batch) y validar longitud antes de la regex es barato; decidir tarde consume los recursos que querías proteger.
4. **La sincronía crea picos.** TTL alineados, reintentos simultáneos, clics a la misma hora, cutovers de golpe, reglas globales instantáneas. Se desincroniza con jitter, sorteo, tandas, escalones y single-flight.
5. **Acota el radio de impacto de todo cambio, incluida la configuración.** Canary, flags y rollout escalonado aplican también a reglas WAF y archivos de config (Cloudflare 2019).
6. **Dev ≠ prod.** Prueba con el mismo límite de memoria, la misma cardinalidad (5 vs 5000), payloads reales, inputs adversariales y ráfagas.
7. **Falla rápido y visible.** Nada de 200 vacíos ni degradación silenciosa.
8. **El rollback rápido y probado es un requisito de diseño**: exige compatibilidad hacia atrás (expand/contract) y separar *deploy* de *release*.
9. **Estado fuera del proceso** (sesión en Redis, historial en BD) para escalar horizontalmente y evitar memoria que crece sin control.
10. **El código generado por IA reproduce patrones de tutorial** (`await` en bucle, `Promise.all` ilimitado, regex copiadas): revisa con criterios de recursos, no de sintaxis.

## Matriz "si ves X → considera Y"

| Si ves… | Mecanismo probable | Considera… |
|---|---|---|
| `OOMKilled` / exit 137 con heap "normal" | el cgroup cuenta todo el proceso (off-heap, buffers, hilos, fragmentación de malloc) | heap al 70–80 % del límite, margen off-heap, streaming, buscar retenciones; alertar sobre working set; confirmar `Reason: OOMKilled` (137 = cualquier SIGKILL) |
| Latencia que crece linealmente con el input y CPU baja | `await` en bucle o N+1 remoto (≈RTT × N) | batch (`IN`, bulk) primero; luego concurrencia acotada 5–10 según la capacidad del destino |
| Login o pagos caen cuando corre un batch | pool de conexiones o descriptores compartido agotado | bulkhead (pools separados batch/interactivo), concurrencia acotada, rate limit hacia el destino |
| CPU 100 % tras cambiar config o regex, sin más tráfico | backtracking superlineal (ReDoS) | kill switch/rollback, motor lineal (RE2, Rust regex), timeout, límite de longitud, rollout escalonado de reglas |
| Un backend saturado y otros ociosos | balanceo por conexión (L4) con HTTP/2/gRPC/keep-alive, sticky o IP hash tras NAT | least-conn/P2C, balanceo L7 por request, reciclar conexiones, sticky solo si hace falta |
| 502 a réplicas muertas o todo el pool retirado a la vez | health checks mal diseñados (apuntan a la home, hacen lógica pesada) | readiness ligera y separada de liveness; outlier detection con tope de expulsión |
| 500 y 200 alternados durante un deploy | dos versiones incompatibles conviven en rolling | expand/contract de esquema y contrato, flags, blue/green; graceful shutdown |
| Pico sincronizado previsible (preventa, drop) | demanda ≫ capacidad del checkout | fila virtual en edge + admisión adaptativa (señal: p95 y errores del checkout) + pase firmado + reserva con TTL + anti-bot |
| Pico de misses y QPS a la BD sin deploy | stampede de hot key o expiración masiva | single-flight, stale-while-revalidate, jitter de TTL ±10–20 %, warm-up, lease/lock por clave; cachear negativos |
| Latencia alta justo tras deploy o escalado | caché o JIT en frío | warm-up, rampas de tráfico, slow start en el LB |
| Una dependencia lenta propaga 500 a todo | hilos/conexiones retenidos esperando | timeout por intento + circuit breaker + bulkhead + fallback |
| Tráfico de reintentos que crece durante el incidente | reintentos sincronizados que amplifican | backoff exponencial + jitter, retry budget, reintentar solo operaciones idempotentes y respetar el breaker |
| "Cobro hecho, pantalla en blanco" | timeout posterior a un efecto lateral | idempotency key (ver `consistencia-distribuida`) |
| Abuso o picos por cliente | sin límite de admisión por identidad | rate limiting por cliente/cuenta con estado compartido atómico (p. ej. script Lua en Redis) y política fail-open/fail-closed explícita por ruta; 429 con `Retry-After`; token bucket si se toleran ráfagas, leaky bucket si se necesita flujo constante |

## Recetas de combinación

- **Llamada saliente (de fuera hacia dentro):** fallback → timeout total → retry (backoff + jitter, idempotente, con presupuesto) → circuit breaker → timeout por intento → bulkhead (pool o semáforo por dependencia) → llamada. El breaker corta la insistencia, el bulkhead limita el daño interno, el timeout libera recursos.
- **Pico de entrada:** CDN/edge (estático + waiting room) → admisión adaptativa → rate limiting por cliente → LB con health checks → reserva de inventario con TTL → pago idempotente con breaker hacia la pasarela.
- **Caché bajo carga:** single-flight (local) + lease/lock (global) + SWR + jitter o XFetch + warm-up antes de exponer tráfico + retries con backoff hacia la BD + métricas de miss por familia de claves.
- **Despliegue seguro:** readiness + graceful shutdown + expand/contract + feature flags + canary 1 → 5 → 25 → 100 % con gates técnicos y de negocio (p. ej. errores > 1 %, p99 > 400 ms, caída de conversión ⇒ rollback automático) + shadow para cambios de motor interno.
- **Concurrencia hacia recursos finitos:** batch → semáforo dimensionado con la capacidad del destino **repartida entre réplicas** → pools separados → breaker si el destino se degrada.
- **Memoria en contenedores:** `limits` realistas + flags del runtime (heap < límite; `GOMEMLIMIT` en Go) + streaming + estado fuera del proceso + alertas sobre working set + pruebas de carga con el mismo límite.

## Preguntas de revisión

1. Para cada dependencia: ¿timeout, política de reintento, breaker, bulkhead y fallback definidos? ¿Qué ve el usuario cuando se abre el breaker?
2. ¿Cuál es el límite de concurrencia hacia cada recurso finito y cómo se reparte entre réplicas?
3. ¿El límite de memoria del runtime deja margen off-heap? ¿La alerta mira working set o heap?
4. ¿Qué regex procesan input no confiable y con qué motor, límite de longitud y timeout?
5. ¿Los health checks son ligeros y distinguen readiness de liveness? ¿Qué pasa si todos fallan a la vez?
6. ¿Qué cambio de esquema o contrato hace imposible convivir dos versiones? ¿Cómo es el rollback y se ha probado?
7. ¿Cuál es el plan ante un pico sincronizado conocido (preventa, campaña) y su capacidad declarada honesta?
8. ¿Dónde puede sincronizarse la carga (TTL, cron, reintentos) y cómo se añade jitter?
9. ¿La configuración (WAF, flags, reglas) se despliega de forma escalonada con kill switch y dueño?

## Precisiones que los videos simplifican (no las repitas)

- "Kubernetes mide RSS" es aproximado: el cgroup contabiliza `memory.current` (anónima + page cache + kernel); kubelet desaloja por *working set*. Un 137 no siempre es OOM.
- JVM respeta cgroups desde JDK 10 (backport 8u191); cgroup v2 desde JDK 15/11.0.16/8u372. Go ignora el cgroup para el GC sin `GOMEMLIMIT`.
- Stack Overflow 2016 fue **cuadrático** (regex de recorte de espacios ante ~20.000 espacios) y el health check del LB apuntaba a la home, lo que sacó todos los servidores; se arregló reescribiendo el código. Cloudflare 2019 fue **polinómico**, agravado por haber retirado una protección de CPU y por propagar reglas globalmente sin escalonar.
- `await` en serie crece **linealmente**, no exponencialmente. El 504 lo emite un proxy por timeout; el SO devuelve EMFILE o agota puertos efímeros.
- Un circuit breaker es **local al cliente**: no da aire al downstream si otros clientes siguen golpeando; hace falta load shedding o rate limiting en el servidor. La outlier detection del mesh expulsa hosts, no es un breaker de servicio.
- Blue/green solo da "rollback en segundos" si los datos escritos por green siguen siendo legibles por blue. Un cutover por DNS no es atómico (TTL y cachés de resolvers).
- Una fila virtual no sustituye la protección en el origen: el checkout debe validar el pase y aplicar su propio rate limit.
- Un limitador en memoria por réplica deja pasar L × réplicas. NGINX `limit_req` responde 503 por defecto (configura `limit_req_status 429`). 429 = cuota del cliente; 503 = sobrecarga del servidor. Las cabeceras `RateLimit`/`RateLimit-Policy` siguen siendo borrador IETF.
- Distingue *stampede* (hot key caduca), *avalanche* (expiración masiva o caída del nodo de caché) y *penetration* (claves inexistentes: cachear negativos o filtro Bloom).

## Formato de salida

```
Decisión: <mecanismo y dónde vive el límite>, en una línea.
Límite y quién lo aplica: <valor inicial + cómo se calibra>.
Mecanismo: <3–6 pasos o configuración mínima>.
Qué ve el usuario al alcanzar el límite: <429 + Retry-After, fila, fallback, error explícito>.
Trade-offs aceptados: <latencia, coste, complejidad operativa>.
Operación: <métricas, umbral de alerta, gate de despliegue, runbook/kill switch>.
Cuándo NO: <condición en la que sobra>.
Fuente: <referencia(s) y video(s)>.
```
