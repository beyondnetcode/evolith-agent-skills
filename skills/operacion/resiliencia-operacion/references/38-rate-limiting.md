# [38] ¿Por qué tu API se cae? (Rate Limiting explicado fácil)

> Fuente: TheDebugDuck — https://youtu.be/LfyObrcgvT8 · notas parafraseadas; «(complemento)» = conocimiento añadido o corrección.
> Estado: elaborado a partir del título y el temario público del video; la transcripción no estuvo disponible (bloqueo de YouTube, 2026-09-28). Lo que no figura en el temario es «(complemento)». Pendiente de contrastar con la transcripción.

- **Síntoma en producción:**
  - La API se cae.
  - (complemento) Un solo cliente acapara CPU, pool y conexiones compartidas: un script con un bucle de reintentos, una integración mal configurada, un scraper o un bot. Todos reciben 5xx; el autoscaling sube pods y traslada la presión a la BD.
  - (complemento) Variante de factura: un endpoint que llama a un tercero de pago (SMS, IA, mapas) multiplica el coste.
  - Variante "de la demo local a producción" (temario; detalle complemento):
    - El limitador probado en local deja pasar 6 veces lo previsto con 6 réplicas.
    - El contador se reinicia en cada deploy.
    - Detrás del balanceador, todos los usuarios comparten la IP del proxy.
- **Causa raíz (mecanismo):**
  - Se admite tráfico sin límite por identidad: el recurso es finito y se lo lleva el primero que llega. Los reintentos sin backoff lo amplifican.
  - En un sistema distribuido (complemento):
    - Un contador en memoria de cada proceso da un límite efectivo de L × réplicas, que además cambia con el autoscaling. Es el caso típico del limitador por defecto en Node.js/TypeScript, el stack del ejemplo: `express-rate-limit` usa un store en memoria.
    - Un contador compartido no atómico (`GET` → comparar → `SET`) se pasa del límite bajo concurrencia ([33] en `consistencia-distribuida`).
    - `INCR` y `EXPIRE` en dos llamadas: si el proceso cae entre ambas, la clave queda sin TTL y el cliente queda bloqueado para siempre.
- **Metáfora visual (complemento, propia; la del video no está disponible):** un portero de discoteca con pulseras.
  - Le llegan X pulseras por minuto a una caja con capacidad para B. Puede entregar de golpe las que tenía guardadas (la ráfaga), pero nunca más de las que caben en la caja: eso es el token bucket.
  - El leaky bucket es un embudo que gotea a ritmo fijo y se desborda cuando se llena.
  - ⚠️ Límite: en producción hay N porteros con N cajas (límite × N), salvo que compartan una caja central (Redis). Compartirla añade un viaje de red y una dependencia que puede caerse (fail-open o fail-closed).
- **Estrategias / solución:**
  1. **Vocabulario** (temario):
     - RPS: la tasa sostenida.
     - Burst: la ráfaga tolerada por encima de la tasa; en token bucket, la capacidad del cubo.
     - Quota: el volumen por periodo largo (día o mes), a menudo contractual o de facturación.
     - (complemento) Para endpoints caros conviene además un límite de concurrencia (peticiones en vuelo).
  2. **Algoritmos y cuándo usar cada uno** (token y leaky bucket: temario; ventanas: complemento):

     | Algoritmo | Cómo funciona | Cuándo usarlo | Coste / límite |
     |---|---|---|---|
     | **Token bucket** | capacidad b, recarga de r fichas/s; cada petición consume 1 ficha (o su coste); sin fichas → 429 | APIs públicas; es el que usan AWS API Gateway y Stripe | tolera ráfagas hasta b con media r; el estado son 2 números |
     | **Leaky bucket (cola)** | admite peticiones y las despacha a ritmo constante; lo que desborda se rechaza | hacia un destino con RPS estricto (proveedor de SMS, API de terceros) | suaviza la salida a costa de latencia y memoria |
     | **Ventana fija** | un `INCR` por clave y minuto | límites simples | permite hasta 2× en el borde de la ventana |
     | **Ventana deslizante (log)** | registra cada petición (sorted set) | cuando hace falta exactitud | memoria O(peticiones) |
     | **Ventana deslizante (contador)** | `previo × (1 − t/ventana) + actual` | escala masiva con poco estado | aproximada: Cloudflare midió 0,003 % de decisiones erróneas sobre 400 M de peticiones |

     NGINX `limit_req` es un leaky bucket: `burst` encola y `nodelay` despacha la ráfaga sin esperar.
  3. **Responder bien** (temario; detalle complemento):
     - `429 Too Many Requests` (RFC 6585) con `Retry-After` en segundos o fecha HTTP (RFC 9110 §10.2.3).
     - Un cuerpo que explique el límite, como pide RFC 6585, en `application/problem+json` (RFC 9457).
     - Opcional: `RateLimit-Policy: "default";q=100;w=60` y `RateLimit: "default";r=12;t=30` (borrador IETF).
     - 429 = se agotó la cuota de *este* cliente; 503 = el servidor está sobrecargado (load shedding).
  4. **Límite distribuido con Redis** (complemento):
     - Leer, recargar y descontar van juntos en un script Lua, que es atómico porque Redis no atiende otra cosa mientras corre.
     - En Cluster, todas las claves del script deben caer en el mismo slot (hash tag `{tenant42}`).
     - El reloj de Redis (`TIME`) evita el desfase entre réplicas.
     ```lua
     -- token bucket (reescrito). KEYS[1] = "rl:{tenant42}:POST:/pagos"; ARGV = capacidad, recarga_por_s, coste
     local cap, rate, cost = tonumber(ARGV[1]), tonumber(ARGV[2]), tonumber(ARGV[3])
     local t = redis.call('TIME'); local now = t[1] + t[2] / 1e6
     local s = redis.call('HMGET', KEYS[1], 'tokens', 'ts')
     local tokens = math.min(cap, (tonumber(s[1]) or cap) + (now - (tonumber(s[2]) or now)) * rate)
     local ok = tokens >= cost
     if ok then tokens = tokens - cost end
     redis.call('HSET', KEYS[1], 'tokens', tokens, 'ts', now)
     redis.call('PEXPIRE', KEYS[1], math.ceil(cap / rate * 1000))    -- limpia cubos inactivos
     return { ok and 1 or 0, ok and 0 or math.ceil((cost - tokens) / rate) }   -- permitido, Retry-After (s)
     ```
  5. **Clave del límite (por clave o tenant)** (complemento):
     - Prioridad: API key, tenant o usuario autenticado antes que la IP. La IP agrupa a muchos detrás de NAT/CGNAT y en IPv6 rota. Si se usa, tómala del proxy de confianza, nunca de un `X-Forwarded-For` que envía el cliente.
     - Coste por ruta: por ejemplo, una búsqueda consume 5 fichas.
     - Capas: ráfaga por segundo + cuota diaria + tope global.
  6. **En el gateway o en el servicio** (complemento):
     - El gateway o edge rechaza barato y temprano (IP, API key, anti-abuso) y protege la infraestructura ([46] en `estilos-arquitectonicos`).
     - El servicio aplica los límites que dependen del negocio: tenant, plan, operación, coste.
     - Suelen coexistir. Envoy separa un límite local (token bucket por instancia, primer escudo) de uno global (servicio de rate limit sobre Redis).
  7. **Fail-open o fail-closed** si el almacén del limitador falla o tarda (con timeout de pocos ms) (complemento):
     - Fail-open, con un limitador local de respaldo (≈ L/N por réplica) y una alerta, para la API general. Stripe pide que un fallo del limitador no tumbe la API; `rate-limiter-flexible` trae un limitador de respaldo.
     - Fail-closed donde el límite es un control de seguridad o de coste: login/OTP, envío de SMS, APIs de pago.
  8. **Cliente** (complemento): respeta `Retry-After`, aplica backoff exponencial con jitter y un presupuesto de reintentos ([30], [31]), y reintenta un `POST` solo con clave de idempotencia ([34] en `consistencia-distribuida`).
  9. **Operación** (complemento): un modo "dark launch" que solo registra antes de rechazar (Stripe); métricas de 429 por clave y ruta; el top de clientes limitados; límites en configuración, con kill switch.
- **Trade-offs y cuándo NO aplicar:** (complemento)
  - Redis añade un viaje de red por petición y un punto de fallo. El limitador local es barato pero aproximado.
  - El leaky bucket como cola añade latencia. La ventana deslizante con log consume memoria.
  - La suma de los límites por cliente puede superar la capacidad total: hace falta además load shedding o un límite de concurrencia global.
  - No sirve para un pico legítimo y sincronizado de usuarios (preventa): ahí va una fila virtual ([21]).
  - Tampoco para un productor interno único: ahí va backpressure o una cola.
- **Heurísticas y umbrales:** (complemento)
  - Punto de partida: token bucket por API key.
  - b ≈ la ráfaga legítima observada (p99 de peticiones por segundo del cliente); r ≈ la capacidad asignada a su plan.
  - `Retry-After` = el tiempo hasta disponer del coste de la petición.
  - Timeout del almacén del limitador de un dígito en ms, con una política de fallo explícita.
  - Dark launch de 1–2 semanas antes de rechazar tráfico real.
- **Anti-patrones / señales de alerta:**
  - Un limitador en memoria con varias réplicas que se cree global.
  - `INCR` + `EXPIRE` en llamadas separadas.
  - `GET`/`SET` sin atomicidad.
  - Limitar por la IP del socket detrás del LB (todos comparten una IP), o fiarse del `X-Forwarded-For` del cliente.
  - Devolver 500 o 503 por cuota. NGINX `limit_req` responde 503 por defecto: configura `limit_req_status 429` (complemento).
  - Un 429 sin `Retry-After`.
  - Clientes que reintentan al instante.
  - Contar después de haber hecho el trabajo caro.
  - Límites cableados en el código.
  - Tratar la cuota como un SLA.
- **Preguntas de revisión arquitectónica:**
  1. ¿Cuál es la clave del límite (API key, tenant, usuario, IP) y cómo se obtiene de forma confiable?
  2. ¿Dónde vive cada límite (gateway o servicio)? ¿Cuál protege la infraestructura y cuál la equidad entre clientes?
  3. ¿El límite es global entre réplicas? ¿Cómo cambia con el autoscaling y tras un deploy?
  4. Si Redis no responde, ¿fail-open o fail-closed, y por qué para esta ruta?
  5. ¿Qué recibe el cliente (429, `Retry-After`, cuerpo) y cómo reintenta?
  6. ¿Se distinguen RPS, burst y quota? ¿Hay protección de capacidad global además del límite por cliente?
- **Caso real / referencias (complemento):**
  - Stripe, "Scaling your API with rate limiters" (Paul Tarjan, 2017): token bucket en Redis, un limitador de concurrencia y dos *load shedders*, dark launch y fallar de forma segura. https://stripe.com/blog/rate-limiters
  - Cloudflare (2017), ventana deslizante aproximada: https://blog.cloudflare.com/counting-things-a-lot-of-different-things/
  - AWS API Gateway: token bucket por cuenta y región, 429, límites *best-effort*. https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-request-throttling.html
  - NGINX, `ngx_http_limit_req_module`.
  - Redis, "Scripting with Lua": https://redis.io/docs/latest/develop/programmability/eval-intro/
  - RFC 6585 §4 y RFC 9110 §10.2.3.
  - draft-ietf-httpapi-ratelimit-headers-11 (mayo de 2026).
  - Marc Brooker, "Exponential Backoff And Jitter" (AWS Architecture Blog, 2015).
- **Precisión técnica:**
  - El leaky bucket como medidor (GCRA) equivale a un token bucket. La diferencia práctica está entre *policing* (rechazar) y *shaping* (encolar y despachar a ritmo fijo) (complemento).
  - `Retry-After` se define en RFC 9110 (segundos o fecha HTTP). RFC 6585 permite enviarlo con el 429 y prohíbe que una caché almacene esa respuesta (complemento).
  - `RateLimit-Policy`/`RateLimit` son un borrador activo (‑11), no un estándar (complemento):
    - Versiones anteriores usaban `RateLimit-Limit/-Remaining/-Reset`, y muchas APIs siguen con `X-RateLimit-*`.
    - El borrador prohíbe al cliente tratar la cuota disponible como una garantía, y `Retry-After` prevalece.
  - Los límites de AWS API Gateway son objetivos *best-effort*, no techos garantizados: no bastan como control de seguridad ni de coste (complemento).
  - Rate limiting por cliente ≠ load shedding (protege la capacidad global) ≠ circuit breaker (local al cliente, [31]) (complemento).
  - Llamar a `TIME` dentro de un script de Redis es seguro porque desde Redis 5 se replican los efectos del script, y desde la 7.0 es el único modo (complemento).
