# [31] Circuit Breaker explicado fácil (el salvavidas de las APIs)

> Fuente: TheDebugDuck — https://youtu.be/krvH-jiE1m0 · notas parafraseadas; «(complemento)» = conocimiento añadido o corrección.

- **Síntoma en producción:** un servicio dependiente empieza a tardar segundos mientras el tráfico sigue entrando y los clientes insisten. Los timeouts se acumulan, las colas crecen, los pools de hilos y conexiones se saturan, y todos ven 500 aunque solo un backend esté mal: un fallo en cascada.
- **Causa raíz (mecanismo):**
  - Sin breaker, cada request espera el timeout completo; los reintentos agresivos multiplican la carga sobre un nodo que ya no responde.
  - Los recursos del proceso (hilos, conexiones) quedan retenidos por llamadas colgadas, y los componentes sanos fallan por inanición.
  - El problema deja de ser el backend enfermo y pasa a ser la propagación del síntoma.
- **Metáfora visual del video:** el breaker o fusible eléctrico abre el circuito ante un pico para no quemar el cableado. No repara el nodo caído, pero evita que arrastre al resto.
- **Estrategias / solución:**
  - **Envoltorio sobre la llamada saliente** (HTTP, RPC) que registra éxitos y fallos y decide el modo: dejar pasar, rechazar al instante, o dejar pasar solo algunas llamadas de prueba.
  - **Estados:**
    - Closed: tráfico normal; se cuentan fallos relevantes (timeout, 5xx).
    - Open: fallo rápido o fallback, sin tocar la red.
    - Half-Open: tras `waitDuration`, se permiten N probes. Si tienen éxito, pasa a Closed; si fallan, vuelve a Open.
  - **Umbral:** fallos consecutivos (fáciles de razonar, sensibles al ruido) o porcentaje de errores en una ventana (más fino, más difícil de calibrar). Empezar conservador y ajustar con métricas.
  - **Combinación:**
    - Timeout: limita cuánto esperas por una llamada.
    - Breaker: decide si siquiera intentas.
    - Retries: con backoff y jitter; deben consultar el breaker y, si está abierto, degradar o encolar.
    - Bulkhead: aísla pools para que el daño no crezca dentro del proceso.
  - **Dónde ponerlo:** cliente o SDK, middleware antes de las dependencias, API gateway por ruta, o service mesh (outlier detection). Si se combinan capas, deben ser coherentes y observables.
  - **Librerías:** Polly (.NET), Resilience4j y Spring Cloud Circuit Breaker (JVM); expulsión de endpoints en el mesh.
  - **Instrumentar:** transiciones de estado, rechazos en Open, latencias antes y después. Alertar si sube el ratio de rechazo y Half-Open no logra estabilizar.
  ```yaml
  # Resilience4j (reescrito)
  resilience4j.circuitbreaker.instances.inventory:
    slidingWindowType: TIME_BASED
    slidingWindowSize: 30                 # segundos
    minimumNumberOfCalls: 20              # evita abrir por ruido con poco tráfico
    failureRateThreshold: 50              # %
    slowCallDurationThreshold: 2s
    slowCallRateThreshold: 80             # %
    waitDurationInOpenState: 15s          # ≈ tiempo típico de recuperación del downstream
    permittedNumberOfCallsInHalfOpenState: 5
    ignoreExceptions: [ com.acme.ClientError4xx ]   # (complemento) 4xx no es fallo del downstream
  ---
  # Istio: equivalente de red (expulsa hosts, no todo el servicio)
  trafficPolicy:
    connectionPool: { http: { http1MaxPendingRequests: 100, maxRequestsPerConnection: 10 } }  # bulkhead
    outlierDetection: { consecutive5xxErrors: 5, interval: 10s, baseEjectionTime: 30s, maxEjectionPercent: 50 }
  ```
  ```text
  # (complemento) Orden típico del pipeline, de fuera hacia dentro (p. ej. handler estándar de .NET):
  rate limiter → timeout total → retry(backoff exponencial + jitter, solo idempotentes) → circuit breaker → timeout por intento → llamada
  # El retry queda fuera del breaker: cada intento cuenta, y con el breaker abierto el retry deja de insistir.
  ```
- **Trade-offs y cuándo NO aplicar:**
  - El breaker es por instancia: los estados divergen entre réplicas y cada una "aprende" sola.
  - Umbrales bajos producen flapping. En Open se rechazan también requests que habrían funcionado; si solo falla un endpoint, conviene un breaker por endpoint o host.
  - Sin fallback con sentido de negocio, Open es solo un error más rápido.
  - Varias capas (SDK + gateway + mesh) pueden contradecirse.
  - (complemento) No aporta en llamadas raras o de muy bajo volumen (no hay estadística) ni sustituye a la idempotencia en operaciones con efectos.
- **Heurísticas y umbrales:**
  - Empezar conservador y calibrar con datos de staging y producción.
  - `waitDuration` coherente con el tiempo típico de recuperación de la dependencia (corto → oscila; largo → tarda en volver).
  - Probes acotadas en Half-Open; timeouts cortos y realistas.
  - Cita: "No arregla el nodo caído, pero evita que arrastre a todos."
- **Anti-patrones / señales de alerta:**
  - Umbrales tan bajos que oscilan con tráfico normal.
  - Half-Open sin límite de probes, que genera otra tormenta.
  - Breaker sin timeout: las primeras llamadas igual se cuelgan.
  - Instancias con estados divergentes cuando el diseño asumía coherencia.
  - Ocultar el fallo con 200 OK vacíos sin telemetría.
  - Reintentos sin backoff o jitter que ignoran el estado del breaker.
  - (complemento) Contar 4xx o errores de validación como fallos del downstream.
- **Preguntas de revisión arquitectónica:**
  1. ¿Qué dependencias son críticas y cuál es el timeout por intento y total de cada una?
  2. ¿Qué cuenta como fallo (timeout, 5xx, llamada lenta) y qué no (4xx)?
  3. ¿Tipo de ventana, umbral, mínimo de llamadas, `waitDuration` y probes en Half-Open?
  4. ¿Qué fallback o degradación de negocio hay en Open (caché, valor por defecto, encolar)?
  5. ¿Los reintentos son idempotentes, con backoff y jitter, y respetan el breaker? ¿Hay bulkhead por dependencia?
  6. ¿En qué capa vive el breaker y cómo se evita la duplicación o contradicción? ¿Qué métricas y alertas lo acompañan?
- **Caso real / empresa citada:** ninguno concreto; librerías Polly, Resilience4j, Spring Cloud Circuit Breaker y outlier detection de service mesh.
- **Precisión técnica:**
  - Correcciones de ASR: "Pun Net" = .NET; "per/Pieré" = peer; "ATI" = APIs.
  - "Darle aire al downstream" solo se cumple parcialmente. (complemento) El breaker es local al cliente: si otros clientes siguen golpeando, el downstream no se recupera. Hace falta load shedding o rate limiting del lado del servidor.
  - (complemento) La outlier detection del mesh no es un breaker de servicio: expulsa hosts individuales del balanceo. Con todos los hosts enfermos, `maxEjectionPercent` evita vaciar el pool, y el tráfico sigue llegando.
  - (complemento) El número de probes en Half-Open depende de la librería (Resilience4j es configurable; Polly v8 deja pasar una). Origen del patrón: *Release It!* (Nygard) y Netflix Hystrix, hoy en mantenimiento y sustituido por Resilience4j.
