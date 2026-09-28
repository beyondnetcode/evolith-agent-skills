# [04] La MENTIRA del Heap vs. RSS: Por qué tu pod muere con OOMKilled

> Fuente: TheDebugDuck — https://youtu.be/Y4ykSwM71bA · notas parafraseadas; «(complemento)» = conocimiento añadido o corrección.

- **Síntoma en producción:**
  - Alerta nocturna "servicio de pagos no disponible"; el dashboard de memoria (heap) marca ~40 %.
  - Eventos del clúster: `Reason: OOMKilled`, `exit code 137`. Logs de la app sin excepción ni stack trace; la última línea es una request normal y luego silencio.
  - Kubernetes reinicia el pod, vuelve el tráfico, se llena otra vez → `CrashLoopBackOff`. En desarrollo nunca se reproduce.
- **Causa raíz (mecanismo):**
  - **Dos contabilidades distintas.** *Heap* = memoria gestionada por el runtime (objetos, arrays, strings). *RSS* = páginas físicas que el kernel asignó al proceso. El límite del contenedor (cgroup) se aplica sobre la memoria real del grupo, no sobre el heap. La diferencia incluye buffers nativos, librerías C/addons (sharp, bcrypt), stacks de hilos, código JIT compilado, buffers de red.
  - **El GC libera "hacia dentro", no hacia el SO.** Marca objetos como libres y baja el contador del heap, pero conserva las páginas (fragmentadas) para reutilizarlas: devolverlas y pedirlas de nuevo es caro. El heap baja; el RSS no.
  - **El runtime no conoce el techo.** Un contenedor no es una VM: es un proceso con un techo impuesto por cgroups (v1/v2 se leen distinto). Si el runtime dimensiona el heap mirando la RAM del host (p. ej. 32 GB vía `/proc/meminfo`), el GC "cree que sobra espacio" y difiere la recolección (recolectar cuesta CPU).
  - **Corte sin aviso.** Al alcanzar el límite del cgroup, el OOM killer del kernel envía SIGKILL (128+9 = 137): no hay warning, excepción capturable ni cierre ordenado de conexiones.
  - **Segundo mecanismo: retención real (leaks lógicos)**, aun con un runtime que sí conoce el límite: (1) archivo subido leído entero a un buffer (PDF de 100 MB) y luego referenciado desde la orden, un log o una caché "por si acaso"; (2) un listener registrado en el bus de eventos por cada cobro y nunca removido — cada closure retiene id, usuario y a veces el PDF (1000 cobros = 1000 closures); (3) un singleton con un array de "últimas compras" que solo hace push. El GC ve referencias vivas y no puede liberar.
- **Metáfora visual del video:** ascensor con letrero "máx. 512 kg": el heap son las bolsas del súper; el RSS es el sensor de peso (bolsas + mochila + carrito); vaciar bolsas (GC) no saca el carrito del ascensor. El cgroup es el letrero del ascensor, no la capacidad del edificio.
- **Estrategias / solución:**
  1. **Diagnosticar con la métrica del kernel:** `docker stats` (uso vs límite), `process.memoryUsage()` comparando `rss` con `heapUsed`, y dentro del contenedor `memory.current`/`memory.stat` (cgroup v2). Si el uso sube tras un pico y no baja, hay retención.
  2. **Hacer que el runtime conozca el límite, dejando margen off-heap** (en el comando de arranque de la misma imagen, no en un documento aparte):
     ```yaml
     # Kubernetes (reescrito)
     resources:
       requests: { memory: "512Mi" }
       limits:   { memory: "512Mi" }
     env:
       - { name: NODE_OPTIONS,       value: "--max-old-space-size=384" }   # Node: ~70-80 % del límite
       - { name: JAVA_TOOL_OPTIONS,  value: "-XX:MaxRAMPercentage=75" }    # JVM moderna (lee cgroup)
       - { name: GOMEMLIMIT,         value: "400MiB" }                     # Go >= 1.19: límite blando para el GC
     # PHP-FPM: pm.max_children * memory_limit (+ overhead) <= límite del contenedor
     ```
  3. **Dejar de sostener basura:**
     ```text
     upload:   req.stream() -> pipe -> storage.uploadStream(key)   # trozos de KB, nunca readFile/arrayBuffer completo
     eventos:  bus.once('charge.confirmed', h)  |  try { ... } finally { bus.off('charge.confirmed', h) }
     historial: RingBuffer(max=100) en proceso, o leerlo de BD/Redis cuando el tablero lo pida
     ```
     Arreglar solo uno de los tres (p. ej. el PDF) solo ralentiza el crecimiento: el 137 vuelve.
  4. **Reproducir antes de desplegar:** `docker run --memory=512m` con los flags del runtime, archivos del tamaño real de producción y ráfagas de requests, con `docker stats` abierto.
  5. **Alertar sobre la memoria del contenedor** (working set vs límite), no solo sobre el heap al 80 %.
- **Trade-offs y cuándo NO aplicar:**
  - Subir el límite (512 Mi → 1 Gi) sin corregir runtime ni retención solo compra tiempo: el 137 aparece más tarde con 1 GB.
  - Un heap máximo demasiado bajo aumenta la frecuencia de GC (CPU, latencia) y produce "heap out of memory" del runtime; (complemento) ese fallo al menos es visible y diagnosticable, a diferencia del SIGKILL.
  - Streaming complica el manejo de errores parciales, reintentos y backpressure; mover estado a Redis añade latencia y una dependencia.
  - (complemento) `requests < limits` de memoria permite overcommit del nodo: más densidad, pero riesgo de desalojo por presión del nodo; para servicios críticos, `requests = limits`.
- **Heurísticas y umbrales:**
  - Heap ≈ 70–80 % del límite del contenedor (512 MiB → ~400 MiB).
  - Exit 137 = SIGKILL (128+9).
  - PHP-FPM: 8 workers × 128 MB = 1 GB > 512 MB: el límite es de todo el contenedor, no de cada proceso.
  - Con streaming, un archivo de 1 GB cabe en un contenedor de 512 MB porque nunca está entero en RAM.
  - Cita: "estás simplemente comprando minutos" (sobre solo subir la RAM del pod).
- **Anti-patrones / señales de alerta:**
  - Manifiesto o Dockerfile con límite de memoria y `CMD node server.js` sin `--max-old-space-size`/`NODE_OPTIONS`; JVM antigua sin soporte de contenedores; Go sin `GOMEMLIMIT`.
  - `readFile`, `arrayBuffer()` o `Buffer.concat` de uploads o descargas completas en handlers.
  - `emitter.on(...)` dentro de un handler de request sin `off`/`once`; closures que capturan objetos grandes.
  - Arrays/Maps a nivel de módulo o singletons sin tope ni TTL; cachés in-process ilimitadas.
  - Alertas y dashboards basados solo en el heap; la "solución" del ticket es subir `limits`.
  - `docker-compose` de desarrollo sin límite de memoria; pruebas con payloads de 2 MB y 10 requests por minuto.
- **Preguntas de revisión arquitectónica:**
  1. ¿El runtime conoce el límite del contenedor y cuánto margen off-heap queda (nativo, hilos, JIT)?
  2. ¿Qué métrica dispara la alerta de memoria: heap o working set del contenedor?
  3. ¿Algún flujo carga archivos o respuestas completas en memoria? ¿Cuál es el tamaño máximo realista?
  4. ¿Qué estado vive en el proceso y crece con el tráfico (listeners, singletons, cachés)? ¿Tiene tope o TTL?
  5. ¿Las pruebas de carga corren con el mismo límite, la misma imagen y payloads reales?
  6. Con varios procesos por contenedor (FPM, workers, cluster), ¿la suma de sus máximos cabe en el límite?
- **Caso real / empresa citada:** ninguno; escenario ilustrativo de un servicio de pagos.
- **Precisión técnica:**
  - "Docker y Kubernetes miden RSS" es una simplificación. (complemento) El cgroup contabiliza `memory.current` (memoria anónima + page cache + memoria de kernel); el OOM se dispara cuando no puede reclamar por debajo de `memory.max`. Kubelet usa el *working set* (uso − `inactive_file`) para el desalojo, y `docker stats` también descuenta la caché inactiva. Todo esto se aproxima al RSS, pero no es idéntico.
  - "El lenguaje le pregunta al host" depende de la versión. (complemento) La JVM lee el cgroup desde JDK 10 (backport a 8u191); el soporte de cgroup v2 llegó en JDK 15, 11.0.16 y 8u372 (el video lo resume como "Java 8 y 10"). Go no mira el cgroup para el GC sin `GOMEMLIMIT`. Algunas versiones recientes de Node consideran el límite del cgroup para el heap por defecto, pero no reservan margen off-heap: el flag explícito sigue siendo lo seguro.
  - "El GC casi nunca devuelve memoria al SO" varía por runtime. (complemento) Go devuelve páginas con su scavenger y G1 puede hacer uncommit periódico (JDK 12+). La fragmentación de glibc malloc (arenas por hilo) también infla el RSS; se mitiga con `MALLOC_ARENA_MAX` o jemalloc.
  - Un 137 no siempre es OOM. (complemento) Cualquier SIGKILL da 137, incluido el que llega tras agotarse el `terminationGracePeriodSeconds`. Hay que confirmar `Reason: OOMKilled`. Con cgroup v2 y Kubernetes ≥1.28, el OOM puede matar todos los procesos del contenedor (`memory.oom.group`).
