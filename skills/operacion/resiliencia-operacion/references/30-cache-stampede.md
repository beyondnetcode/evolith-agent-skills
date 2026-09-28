# [30] ¿Qué es Cache Stampede y por qué rompe sistemas?

> Fuente: TheDebugDuck — https://youtu.be/YIMF4w7PFpM · notas parafraseadas; «(complemento)» = conocimiento añadido o corrección.

- **Síntoma en producción:**
  - Dashboard verde y sin deploy, pero la latencia se dispara de golpe.
  - CPU de la BD al rojo, colas crecientes, conexiones al límite y percentiles extremos.
  - Pico de misses alineado con un salto de QPS al backend; timeouts visibles y reintentos que amplifican.
  - Parece que "todo está roto", pero solo murió una clave caliente en el peor minuto.
- **Causa raíz (mecanismo):**
  - Expiración sincronizada: muchas claves escritas a la vez con el mismo TTL caducan juntas, o caduca una *hot key*.
  - N workers ven el mismo miss simultáneo y cada uno recalcula sin coordinación, pagando N veces el mismo coste.
  - La caché fría (clúster nuevo, deploy, flush) produce el mismo efecto a escala.
  - Los reintentos agresivos echan combustible.
- **Metáfora visual del video:** estampida por una puerta angosta (thundering herd / dog-pile). Barras de TTL alineadas que se desploman juntas; el jitter convierte el bombardeo en llovizna.
- **Estrategias / solución:**
  1. **Request coalescing / single-flight:** ante un miss, un líder recalcula y el resto espera el resultado en vuelo (Instagram cachea la *promesa*, no solo el valor). Hacen falta un timeout para los que esperan y un plan B si el líder falla.
  2. **Stale-while-revalidate:** servir el valor algo viejo mientras se regenera en segundo plano. Se implementa con dos marcas de tiempo (soft y hard TTL); en HTTP/CDN con `Cache-Control: max-age=60, stale-while-revalidate=300`.
  3. **Romper la sincronía:** jitter en el TTL o expiración temprana probabilística.
  4. **Warm-up** de las claves más pedidas antes de exponer tráfico (jobs, scripts, snapshots, réplicas) y rampas en lanzamientos.
  5. **Lease o lock por clave** (leases de Memcached, `SET NX PX` en Redis) o una cola dedicada al refresh, con idempotencia y sin corrupción si el refresh falla a medias.
  6. **Reintentos con backoff** y límites.
  7. **Observabilidad:** spans etiquetados con la clave lógica (si es seguro), bursts de miss correlacionados con el fan-out a la BD, alertas sobre derivadas.
  ```text
  inflight = {}
  get(key):
    e = cache.get(key)
    if e and now < e.soft_exp: return e.v
    if e and now < e.hard_exp: refresh_async_once(key); return e.v          # SWR
    if key in inflight: return await timeout(inflight[key], 2s) or fallback # seguidor
    p = load_from_db(key); inflight[key] = p                                # líder
    try:   v = await p
    finally: del inflight[key]
    ttl = base_ttl * uniform(0.9, 1.1)                                      # jitter ±10 %
    cache.set(key, v, soft=ttl, hard=ttl*5)
    return v

  # Coordinación entre instancias
  if redis.SET("lock:"+key, owner, NX, PX=5000): recompute(); set(); release_if_owner()
  else: sleep(backoff + jitter); reread() or serve_stale()

  # Expiración temprana probabilística (XFetch) — (complemento)
  if now - delta * beta * ln(random()) >= expiry: recompute()   # delta = coste de recomputar, beta≈1
  ```
- **Trade-offs y cuándo NO aplicar:**
  - Single-flight en memoria solo coalesce dentro de una instancia (N réplicas = N recomputaciones); el lock distribuido lo hace global, pero añade latencia, riesgo de lock huérfano o expirado y una dependencia más.
  - SWR sirve datos viejos: no apto para saldos, stock en tiempo real o precios contractuales.
  - Con el jitter, la frescura es desigual entre claves.
  - Una promesa compartida propaga el error a todos los que esperan. (complemento) No cachear rechazos, o cachear negativos muy poco tiempo.
  - El warm-up consume tiempo y recursos y requiere saber qué será caliente.
- **Heurísticas y umbrales:**
  - Checklist del video:
    - ¿TTL alineados en masa? → jitter o SWR.
    - ¿Arranque en frío tras cada deploy? → warm-up y rampas.
    - ¿Miss coordinado? → single-flight.
    - ¿Reintentos que pueden volverse tormenta? → backoff y límites.
  - Warm-up "honesto" de las ~10 claves que mandan en tu métrica.
  - (complemento) Jitter de ±10–20 %.
  - (complemento) Hard TTL de varias veces el soft TTL.
- **Anti-patrones / señales de alerta:**
  - El mismo TTL global para todo porque es rápido de configurar.
  - Flush agresivo o reinicios masivos sin plan de relleno.
  - Exponer un clúster o nodo de caché nuevo en frío al tráfico real.
  - Varios workers recomputando la misma clave; seguidores sin timeout.
  - Reintentos sin backoff; ausencia de métricas de hit/miss por clave o por familia.
- **Preguntas de revisión arquitectónica:**
  1. ¿Cuáles son las claves calientes y cuánto cuesta recomputarlas (tiempo, queries, fan-out)?
  2. ¿Las expiraciones pueden alinearse (carga masiva, mismo TTL, warm-up simultáneo)?
  3. ¿La coordinación del miss es local o global? ¿Qué pasa si el líder falla o tarda?
  4. ¿Qué nivel de desactualización tolera el negocio para cada dato (SWR sí o no)?
  5. ¿Hay plan de calentamiento tras deploy, escalado o flush? ¿Quién puede vaciar la caché y cuándo?
  6. ¿Los reintentos tienen backoff, jitter y presupuesto?
- **Caso real / empresa citada:**
  - Instagram: cluster nuevo con caché vacía → thundering herd → caché de promesas compartidas.
  - Meta/Facebook: Memcached a gran escala con mcrouter y gobernanza.
  - Netflix: EVCache con copia y precalentamiento de datos al escalar o mover clústeres.
- **Precisión técnica:**
  - Correcciones de ASR: "cash stamped" = cache stampede, "Docpile" = dog-pile, "MC Router" = mcrouter, "lis" = leases.
  - (complemento) Los leases de Memcached vienen del paper *Scaling Memcache at Facebook* (NSDI 2013) y resuelven thundering herd y sets obsoletos. XFetch viene de Vattani et al. (VLDB 2015).
  - "Millones de entradas con el mismo TTL caen juntas" solo ocurre si se escribieron casi a la vez (carga masiva, warm-up o arranque). Con escrituras repartidas en el tiempo, el riesgo principal es la hot key individual.
  - (complemento) Conviene distinguir tres casos: *stampede/breakdown* (una hot key caduca), *avalanche* (expiración masiva o caída del nodo de caché) y *penetration* (claves inexistentes que siempre dan miss). Este último se mitiga cacheando negativos o con un filtro Bloom.
