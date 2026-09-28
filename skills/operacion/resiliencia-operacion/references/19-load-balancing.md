# [19] Por qué tu app se cae aunque metas servidores más grandes (Load Balancing)

> Fuente: TheDebugDuck — https://youtu.be/o0kv2-GOBdU · notas parafraseadas; «(complemento)» = conocimiento añadido o corrección.

- **Síntoma en producción:**
  - Pico de Cyber Monday: los logs muestran que casi todo el tráfico cae en un mismo backend, mientras el LB no marca error y los health checks siguen en verde.
  - Tickets de soporte: checkout que no termina, "cobro hecho y pantalla en blanco".
  - En la instancia sobrecargada crecen la cola y la memoria, los hilos esperan recursos y aparecen 504. Los 502 surgen cuando el LB envía tráfico a un backend caído.
- **Causa raíz (mecanismo):**
  - Una sola instancia o un reparto desigual. Escalar vertical tiene techo físico y deja un punto único de fallo.
  - Round robin reparte por turno ignorando la carga real, así que con requests heterogéneas una réplica se satura y otras quedan ociosas.
  - La afinidad (sticky) concentra usuarios pesados en una réplica. Las conexiones largas (WebSocket, streams) se cortan si se reenrutan.
  - Un LB único y olvidado se convierte en el nuevo cuello de botella y SPOF.
- **Metáfora visual del video:** la torre de control del aeropuerto no ejecuta la lógica, asigna pistas; la capacidad total es la suma de las pistas, no el tamaño de una. Sin torre, todos aterrizan en la misma pista.
- **Estrategias / solución:**
  1. **Escalar horizontal:** N réplicas idénticas (Deployment con `replicas: 3`, o procesos detrás de NGINX).
  2. **Health checks** (`GET /health`, sonda TCP) que sacan backends malos del pool hasta que se recuperan.
  3. **Elegir el algoritmo según el perfil de tráfico:**
     - Round robin: requests cortas y homogéneas.
     - Least connections: requests largas (uploads, reportes, WebSockets).
     - Weighted: hardware heterogéneo (p. ej. 70/30 según mediciones).
     - IP hash o sticky por cookie: estado local o conexiones largas.
  4. **Sacar el estado del servidor** (sesión en Redis) para que cualquier réplica sirva; sticky solo donde sea imprescindible.
  5. **L4 vs L7:**
     - L4 (NLB): IP y puerto, TCP directo, baja latencia (gaming, proxy a BD).
     - L7 (ALB, reverse proxy): host, path y headers; permite enrutar `/api` a un pool, estáticos a otro y v2 a un servicio nuevo.
  6. **Alta disponibilidad del propio LB:** par activo-pasivo, varias zonas, LB gestionado del cloud, failover entre orígenes.
  7. **Observar por backend:** colas y errores por réplica, no CPU promedio.
  ```nginx
  # (reescrito)
  upstream api {
      least_conn;                                              # o ip_hash; para afinidad
      server 10.0.0.11 weight=7 max_fails=3 fail_timeout=10s;  # nodo grande
      server 10.0.0.12 weight=3 max_fails=3 fail_timeout=10s;  # nodo chico
  }
  server { location /api/ { proxy_pass http://api; } }
  ```
  - Mapa de capas del video: Edge/CDN (estático) → LB (reparte) → rate limiting (cuánto pasa) → lógica → datos. El circuit breaker [31] protege llamadas salientes; el LB protege la entrada.
- **Trade-offs y cuándo NO aplicar:**
  - Sticky desbalancea y pierde sesiones si la réplica muere.
  - Pesos mal calibrados queman el nodo débil.
  - L7 da flexibilidad a cambio de latencia y CPU (terminación TLS, parsing); L4 es rápido pero ciego al contenido.
  - Duplicar el LB cuesta dinero; no hace falta un data center duplicado el primer día, pero sí saber qué pasa si el LB cae.
  - (complemento) Least connections no ve el coste por request: con requests de coste muy variable, rinden mejor least outstanding requests, power-of-two-choices o EWMA de latencia.
- **Heurísticas y umbrales:**
  - Más de 1 réplica (3 es lo típico) y health checks que expulsan del pool.
  - Round robin para APIs cortas, least connections para conexiones largas, sticky solo si hace falta, pesos calibrados con mediciones (ejemplo 70/30).
  - Cita: "Sticky, solo si lo necesitas."
- **Anti-patrones / señales de alerta:**
  - Una sola instancia en producción; "escalar" solo subiendo RAM o CPU.
  - LB sin health checks, o con health check trivial que siempre devuelve 200 aunque la réplica esté saturada o sin dependencias.
  - Sesión o carrito en memoria del servidor sin afinidad ni store externo.
  - Round robin puro con WebSockets o streams largos; LB autogestionado único sin failover.
  - Dashboards de CPU promedio sin desglose por backend.
  - (complemento) Health check acoplado a lógica pesada, como la home que renderiza contenido (caso Stack Overflow en [10]): un fallo de negocio retira todo el pool.
- **Preguntas de revisión arquitectónica:**
  1. ¿Cuántas réplicas y en cuántas zonas? ¿Qué pasa si cae una zona o el propio LB?
  2. ¿Qué verifica el health check (liveness vs readiness), con qué intervalo y umbral? ¿Puede retirar todo el pool a la vez?
  3. ¿Dónde vive el estado de sesión? ¿Se necesita afinidad y cómo se degrada si la réplica muere?
  4. ¿El algoritmo corresponde al perfil de requests (duración, coste, conexiones persistentes)?
  5. ¿L4 o L7 y por qué? ¿Se necesita enrutar por path o header, o hacer canary?
  6. ¿Se miden colas, latencia y errores por backend?
- **Caso real / empresa citada:** documentación pública de AWS (ELB/ALB/NLB, target groups, stickiness por cookie), NGINX (`upstream`, `ip_hash`) y Cloudflare Load Balancing (failover entre orígenes). No hay incidentes concretos.
- **Precisión técnica:**
  - "Health checks verdes y todo cae en un backend" tiene causas probables no mencionadas. (complemento) Un LB L4 balancea por *conexión*: con HTTP/2, gRPC o keep-alive largos, pocas conexiones persistentes concentran todo el tráfico en una réplica. Se resuelve con balanceo L7 por request o reciclando conexiones. IP hash detrás de NAT/CGNAT también concentra muchos usuarios en un backend.
  - (complemento) En NGINX open source los health checks son pasivos (`max_fails`/`fail_timeout`); los activos y `slow_start` son de NGINX Plus. En Kubernetes, la `readinessProbe` saca el pod de los Endpoints y la `livenessProbe` lo reinicia: no deben confundirse.
  - (complemento) "Cobro hecho y pantalla en blanco" indica un timeout posterior a un efecto lateral: exige idempotencia del cobro y de los reintentos del cliente.
