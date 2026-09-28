# [15] La arquitectura detrás de cuentas con millones de seguidores

> Fuente: TheDebugDuck — https://youtu.be/fCf6_aVkz9w · notas parafraseadas; «(complemento)» = conocimiento añadido o corrección.

- **Síntoma en producción:** un amigo ya vio el tweet y a ti tu feed sigue cargando; respuestas visibles antes que el tweet original; cuando una mega-cuenta publica en hora pico, las colas de reparto se atrasan, la CPU queda saturada, Redis sube RAM y el resto del sitio se ralentiza. Objetivo interno de Twitter: repartir un tweet grande en <5 s, a veces incumplido.
- **Causa raíz (mecanismo):**
  - **Fan-out on read** (original): el feed se armaba al abrir la app con un SELECT con JOINs sobre las cuentas seguidas, ordenado por fecha. Publicar era barato; leer no escalaba (millones recalculando lo mismo).
  - **Fan-out on write**: al publicar, API → cola → workers en paralelo que insertan el ID del tweet en el home timeline de cada **seguidor** (listas en clústeres Redis, más reciente arriba). Leer = leer una lista precalculada. Encaja con carga **read-heavy** (lecturas decenas o cientos de veces > escrituras).
  - **Celebrity problem**: un autor con decenas de millones de seguidores = decenas de millones de inserts (replicados en varios nodos) por un solo tweet. Las bandejas se actualizan en distintos momentos → desfase entre timelines (una "race condition de infraestructura": ves la respuesta antes que el original).
- **Metáfora visual del video:** buzones: dejar la carta en cada buzón al enviarla (fan-out on write) vs fotocopiar la carta para todo un país; las mega-cuentas pasan a una "vitrina" central.
- **Estrategias / solución:** **timeline mixto (híbrido)**: router en el write path por umbral de seguidores (umbral no revelado).
  ```
  onTweet(author, id):
    if followers(author) < UMBRAL: enqueue(fanout, id)   # workers: push + trim en home:<seguidor>
    else: celebStore.append(author, id)                   # 1 escritura ("vitrina")
  readTimeline(user):
    base  = redis.range("home:"+user)                     # precalculado
    celeb = [celebStore.recent(c) for c in celebsFollowed(user)]  # fan-out on read
    return mergeByTime(base, celeb)
  ```
  - Para el pico de lecturas sobre la "vitrina" (final deportiva, elecciones): **request coalescing** y **rate limiting** para evitar el **thundering herd** (el mismo GET millones de veces en el mismo segundo).
  - (complemento) Caché caliente replicada de tweets recientes de celebridades; *singleflight* por clave; jitter en expiraciones; fan-out solo a usuarios **activos** (Twitter lo hacía con usuarios activos recientes); limitar el timeline a ~800 IDs; en lectura, ocultar respuestas cuyo tweet padre aún no es visible (o traer el padre).
- **Trade-offs y cuándo NO aplicar:** fan-out on write compra lecturas O(1) con escrituras O(seguidores), RAM y replicación; con distribución de seguidores muy sesgada falla en la cola larga. Fan-out on read es barato al escribir y caro al leer. El híbrido traslada el riesgo al read path (thundering herd) y añade merge por usuario, pero casi nadie sigue a cientos de celebridades. Para sistemas pequeños o sin sesgo de seguidores, fan-out on read con índices y caché basta (complemento).
- **Heurísticas y umbrales:** diseñar un feed empezando por **cuántos seguidores tiene quien publica**, no por cuántos servidores; ratio lecturas/escrituras (read-heavy de 10× a 100×); SLO de reparto <5 s; umbral de "celebridad" como parámetro (no publicado). (complemento, charla "Timelines at Scale", Raffi Krikorian, ~2012) ~300K QPS de lectura de timelines frente a ~5–12K tweets/s; timelines de ~800 entradas replicadas ×3; el fan-out de cuentas tipo Lady Gaga (~30 M seguidores) podía tardar minutos.
- **Anti-patrones / señales de alerta:**
  - Feed calculado con JOIN + ORDER BY en cada apertura a gran escala.
  - Fan-out síncrono dentro de la request de publicación.
  - Tratar igual a todos los autores sin considerar la distribución de seguidores.
  - Un recurso "hot" (vitrina) sin coalescing, caché ni rate limit.
  - Ausencia de métricas de lag de la cola de fan-out y de SLO de reparto.
- **Preguntas de revisión arquitectónica:**
  1. ¿Cuál es el ratio lectura/escritura y la distribución (cola larga) de seguidores?
  2. ¿Qué pasa cuando publica el autor del percentil 99,99?
  3. ¿Dónde está el umbral push/pull y cómo se ajusta?
  4. ¿Qué protege el read path ante un pico sincronizado (evento masivo)?
  5. ¿Qué garantías de orden/causalidad necesita el producto (respuesta antes del original)?
  6. ¿Se mide el lag de fan-out contra un SLO?
- **Caso real / empresa citada:** Twitter (home timeline en Redis, *celebrity problem*, *mixed timeline*); cuentas del tamaño de Lady Gaga y Barack Obama citadas en charlas públicas.
- **Precisión técnica:**
  - Error del video: "si sigues a 100 personas son 100 listas". En fan-out on write, el número de escrituras depende de los **seguidores del autor**, no de a cuántos sigues tú; si el autor tiene 100 seguidores, son 100 listas.
  - "Decenas de millones de escrituras en milisegundos" es exagerado; el propio video luego dice que el objetivo era <5 s y a veces no se cumplía.
  - La inconsistencia entre timelines no es una race condition en sentido estricto sino **falta de orden causal** en un sistema eventualmente consistente (complemento).
  - Twitter usaba estructuras Redis personalizadas, no un simple `LPUSH` (complemento).
  - ASR: "Kia publica" = "quien publica"; "right path" = write path; "Reid" = read.
