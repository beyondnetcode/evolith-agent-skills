# [22] ¿Cómo actualizar tu app en vivo sin F5? Polling, WebSocket y SSE explicados

> Fuente: TheDebugDuck — https://youtu.be/D2-BNfHcD8M · notas parafraseadas; «(complemento)» = conocimiento añadido o corrección.

- **Síntoma en producción:** 3 a. m.: el dashboard de monitoreo muestra cero alertas críticas, todo verde, "última actualización hace 4 minutos", mientras PagerDuty y Slack ya acumulan 47 alertas reales. El tablero no miente a propósito: no recibió el dato (transporte mal elegido o conexión caída en silencio).
- **Causa raíz (mecanismo):** alguien tiene que mover el dato: el cliente pregunta (pull) o el servidor empuja (push).
  - **Polling**: punto ciego entre consultas; sin límites (cada 500 ms) dispara QPS, factura cloud y 429.
  - **WebSocket**: conexión persistente bidireccional (handshake `Upgrade`); proxies/balanceadores cortan conexiones inactivas si no hay heartbeat → cierre silencioso y tablero congelado.
  - **SSE**: HTTP normal, `Content-Type: text/event-stream`, `EventSource` en el cliente; unidireccional servidor→cliente, reconexión automática del navegador.
- **Metáfora visual del video:** tres "cables": preguntar una y otra vez (polling), llamada telefónica abierta en ambos sentidos (WebSocket), radio en directo (SSE).
- **Estrategias / solución:** elegir por **dirección del dato y quién lo empuja**, no por moda.
  - Árbol: ¿bidireccional/baja latencia? → WebSocket. ¿Solo push del servidor sobre HTTP normal? → SSE. ¿Baja frecuencia, cacheable, sin conexión permanente (KPI por minuto)? → polling con backoff. Si hay duda: empezar simple, medir, subir de "cable" solo cuando el lag duela.
    ```
    # Polling bien hecho
    poll():
      r = fetch(url, headers: If-None-Match: etag)
      if r.status == 304: delay = min(delay*2, MAX)       # backoff exponencial con tope
      else: render(r.body); etag = r.etag; delay = BASE
      schedule(poll, delay + jitter)                        # (complemento) jitter; pausar en pestaña oculta
    # SSE
    es = new EventSource(url); es.onmessage = e => update(JSON.parse(e.data))   # handler idempotente, sin bloquear el hilo principal
    # WebSocket
    ws.onopen → subscribe; ws.onmessage → render; ping cada ~30 s; onclose → reconectar con backoff + resuscribir
    ```
  - Webhook ≠ WebSocket/SSE: webhook es servidor→servidor (un SaaS hace POST a tu API); luego aún necesitas polling/SSE/WS para que el humano lo vea en vivo.
  - (complemento) Mostrar indicador de "dato obsoleto" cuando `now - lastUpdate > umbral` o se pierde el heartbeat (un dashboard de guardia nunca debe mostrar verde con dato viejo sin avisarlo); SSE con `id:` + `Last-Event-ID` para reanudar sin perder eventos; `retry:` para ajustar reconexión.
- **Trade-offs y cuándo NO aplicar:** polling: simple, predecible, fácil de depurar y amigable con proxies/caché, pero con punto ciego y coste por request. WebSocket: potente pero con proxies más complicados, heartbeat, reintentos y estado de conexión. SSE: amigable con proxies y con autoreconexión, pero solo una dirección (callejón sin salida para chat). (complemento) SSE sobre HTTP/1.1 sufre el límite de ~6 conexiones por origen en el navegador (HTTP/2 lo mitiga); `EventSource` no permite cabeceras personalizadas (auth por cookie); proxies con buffering (nginx) rompen el stream si no se desactiva; escalar WebSocket/SSE horizontalmente requiere pub/sub (Redis, NATS) entre nodos y considerar sticky sessions.
- **Heurísticas y umbrales:** polling cada 500 ms = anti-patrón; KPI por minuto → polling basta; heartbeat/ping cada ~30 s; medir requests y conexiones abiertas; diseñar reconexión y heartbeat **antes** del incidente. (complemento) Timeouts de inactividad típicos: ALB de AWS 60 s, `proxy_read_timeout` de nginx 60 s → heartbeat < timeout.
- **Anti-patrones / señales de alerta (las 4 trampas del video):**
  1. `setInterval` agresivo sin backoff ni ETag → 429 y factura.
  2. WebSocket para notificaciones unidireccionales → complejidad de más.
  3. SSE para chat bidireccional → callejón sin salida.
  4. Sin reconexión ni heartbeat → tablero congelado.
  - Extra: confundir webhook con push al navegador; dashboard sin indicador de frescura.
- **Preguntas de revisión arquitectónica:**
  1. ¿Hacia dónde va el dato y quién lo inicia (cliente, servidor, ambos)?
  2. ¿Qué latencia de actualización necesita el negocio y cuál es el coste de un punto ciego?
  3. ¿Cómo detecta el cliente una conexión muerta y cómo se lo comunica al usuario?
  4. ¿Qué infraestructura intermedia (proxies, LB, CDN) hay y cuáles son sus timeouts/buffering?
  5. ¿Cómo se reanuda tras reconectar sin perder ni duplicar eventos (idempotencia)?
  6. ¿Cuántas conexiones concurrentes o QPS genera el diseño a escala y cuánto cuesta?
- **Caso real / empresa citada:** Slack (mensajería en vivo, WebSocket); Grafana Live (series temporales al dashboard); PagerDuty/Slack en el escenario de incidente.
- **Precisión técnica:**
  - Grafana Live **usa WebSocket** (librería Centrifuge), no SSE; sirve como ejemplo conceptual de push unidireccional, pero el transporte citado es incorrecto (complemento).
  - Falta **long polling** como punto intermedio (histórico y aún útil detrás de proxies restrictivos) (complemento).
  - "SSE: el navegador reintenta" es correcto, pero la reanudación sin pérdida depende de que el servidor soporte `Last-Event-ID` (complemento).
  - ASR: "ifn match" = If-None-Match; "text/eventgunstam" = text/event-stream; "Hardbeat/Pink" = heartbeat/ping; "en potencia" = idempotente.
