# [09] El secreto para que tu Base de Datos soporte miles de usuarios

> Fuente: TheDebugDuck — https://youtu.be/UJnsiQk11Dc · notas parafraseadas; «(complemento)» = conocimiento añadido o corrección.

- **Síntoma en producción:**
  - Pico de 1 000 usuarios: lluvia de 504 Gateway Timeout con la CPU de la BD al ~2 %, RAM y disco sin alertas. Los hilos web siguen vivos, pero bloqueados esperando una conexión.
  - Con pools gigantes: la BD se satura de sesiones concurrentes y se congela.
  - Con fugas: tras N errores quedan N conexiones colgadas; en la petición N+1 el pool está vacío → connection timeout en la app → 504 en el balanceador.
- **Causa raíz (mecanismo):**
  - Abrir una conexión es caro: handshake TCP (varios RTT), negociación TLS, autenticación y reserva de memoria de sesión (PostgreSQL crea un proceso por conexión). De ahí el pool de conexiones preabiertas y reutilizables.
  - La concurrencia útil de la BD la fijan sus núcleos y dispositivos de I/O, no los usuarios. Con más sesiones activas que núcleos llegan el context switching, la contención de locks/latches y el cache thrashing: el throughput cae.
  - El pool es un cuello de botella deliberado que protege la BD: la cola se forma en la app (barata), no dentro del motor.
  - Retención de conexiones: liberarlas sólo en el camino feliz (excepción o `return` temprano = fuga); transacción abierta durante una llamada HTTP externa (2 s de conexión retenida sin trabajo útil); pedir una 2ª conexión dentro de un método que ya tiene una (deadlock del pool).
  - Escala horizontal: pods × pool por pod (50 × 20 = 1 000) supera la capacidad de la BD.
- **Metáfora visual del video:** valet parking: las plazas son las conexiones; un encargado con 1 000 llaves no aparca más rápido. Mesero con 50 mesas a la vez: todos comen más tarde que si atendiera 5 con fluidez.
- **Estrategias / solución:**
  1. Dimensionar con la fórmula de HikariCP / wiki de PostgreSQL: `conexiones ≈ (núcleos_BD × 2) + discos efectivos` (8 núcleos + 1 SSD ≈ 17). Es el total repartido entre instancias; después, medir bajo carga y ajustar.
  2. Timeout corto para obtener conexión del pool (2–3 s): fail fast, liberar hilos, disparar métricas.
  3. Detección de fugas activa: alerta si una conexión pasa más de 5–10 s fuera del pool (indica la línea que la abrió).
  4. Liberación garantizada: try-with-resources / `using` / `finally` / `release()` en todos los caminos.
  5. Nunca mantener una transacción abierta durante una llamada a una API externa; nunca pedir una conexión anidada.
  6. Muchas réplicas: sumar las conexiones totales y usar un proxy de conexiones (PgBouncer, ProxySQL; (complemento) RDS Proxy, Supavisor) que multiplexe miles de clientes sobre pocas conexiones reales.
  7. Ante timeouts, preguntar por qué se retienen tanto las conexiones, no subir `maxPoolSize`.
  ```yaml
  # HikariCP (valores orientativos)
  maximumPoolSize: 17            # (2 × núcleos del servidor BD) + discos, dividido entre instancias
  connectionTimeout: 2500        # ms; el default de Hikari es 30000
  leakDetectionThreshold: 8000   # ms; deshabilitado por defecto, mínimo 2000
  ---
  # PgBouncer delante de PostgreSQL (complemento)
  pool_mode: transaction
  default_pool_size: 20          # conexiones reales por (db, usuario)
  max_client_conn: 5000          # conexiones lógicas desde los pods
  ```
- **Trade-offs y cuándo NO aplicar:**
  - Pool pequeño = cola en la app. (complemento) Con consultas largas o esperas de I/O de alta latencia (almacenamiento en red, locks), el óptimo puede ser mayor: la fórmula es un punto de partida.
  - Timeout corto = más errores visibles en picos, preferibles al colapso; combinar con backpressure/429.
  - (complemento) PgBouncer en modo transacción rompe características de sesión: `SET`, advisory locks de sesión, `LISTEN/NOTIFY`, tablas temporales (y prepared statements en versiones < 1.21). Añade un salto de red y otro componente a operar.
  - (complemento) Separar pools por tipo de carga (API vs workers) consume conexiones, pero aísla fallos.
- **Heurísticas y umbrales:**
  - `(2 × cores) + discos`; 8 cores + SSD → ~17.
  - Timeout de adquisición 2–3 s; detección de fugas 5–10 s.
  - 50 pods × 20 = 1 000 conexiones → proxy.
  - En pruebas de estrés, un pool de 10 procesa más req/s que uno de 200.
  - Diagnóstico: CPU de BD baja + 504 = agotamiento o fuga del pool, no saturación de la BD.
  - (complemento) Evitar el deadlock de pool: si cada hilo necesita C conexiones simultáneas, pool ≥ hilos × (C − 1) + 1.
- **Anti-patrones / señales de alerta:**
  - Pool dimensionado por nº de hilos o de usuarios.
  - Subir `maxPoolSize` ante cada timeout.
  - `connectionTimeout` por defecto (30 s) o infinito.
  - Liberar la conexión sólo en el happy path.
  - Llamadas HTTP o a colas dentro de `@Transactional`.
  - Abrir y cerrar conexión por request sin pool.
  - Autoscaling de pods sin tope de conexiones totales.
  - Sin métricas de pool (activas, idle, pendientes, tiempo de espera).
- **Preguntas de revisión arquitectónica:**
  1. ¿Conexiones totales = instancias máximas × pool, frente a `max_connections` y núcleos de la BD?
  2. ¿Cuánto tiempo se retiene cada conexión y qué ocurre mientras (I/O externo, lógica de negocio)?
  3. ¿Timeout de adquisición y detección de fugas configurados? ¿Se exportan las métricas del pool?
  4. ¿Hay llamadas remotas dentro de transacciones?
  5. Con escala horizontal/serverless: ¿se necesita proxy de conexiones? ¿Qué features de sesión rompe?
  6. ¿Workers batch y API comparten pool?
- **Caso real / empresa citada:** documentación de HikariCP ("About Pool Sizing") y wiki de PostgreSQL; no se cita empresa.
- **Precisión técnica:**
  - La primera mención, "núcleos + discos", es incorrecta (o error de ASR). La fórmula es `(núcleos × 2) + spindles efectivos` (el propio video la corrige al final). Los núcleos son los del servidor de BD, no los de la app, y Hikari la presenta como punto de partida.
  - "Errores 54" = 504.
  - "Un pool pequeño siempre gana": cierto en OLTP de consultas cortas limitado por CPU; no es universal.
  - (complemento) Por motor: PostgreSQL usa un proceso por conexión (memoria alta; `max_connections` = 100 por defecto); MySQL un hilo por conexión (thread pool en Percona/MariaDB/Enterprise); en SQL Server el pool ADO.NET trae `Max Pool Size=100` por cadena de conexión.
