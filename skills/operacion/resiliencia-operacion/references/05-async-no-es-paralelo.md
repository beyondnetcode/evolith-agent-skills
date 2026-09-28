# [05] Tu async no es paralelo: El error que deja tu Checkout en 8 segundos

> Fuente: TheDebugDuck — https://youtu.be/97p_mrF6_bA · notas parafraseadas; «(complemento)» = conocimiento añadido o corrección.

- **Síntoma en producción:**
  - `confirmOrder` tarda más de 8 s y el botón de compra se queda girando; el usuario recarga y la pasarela reintenta el webhook por falta de respuesta, así que los procesos se acumulan.
  - CPU y memoria normales: no hay `sleep` ni lock visible.
  - Variante "arreglada" con `Promise.all` masivo: caídas intermitentes a mitad de procesos, 504, conexiones en error, "too many open files". También fallan login y pagos, que no tienen relación con el batch: un auto-DoS.
- **Causa raíz (mecanismo):**
  - `async` solo marca que la función puede suspenderse esperando I/O; no clona hilos. `await` dentro de un `for` suspende esa función hasta que responde la llamada actual (el event loop sigue atendiendo a otros), así que la latencia total es N × RTT: 200 × 40 ms = 8 s. El cuello de botella es la red en serie, no la CPU.
  - Paralelismo sin cota (`Promise.all`, `Task.WhenAll`, `asyncio.gather` sobre un arreglo dinámico) abre N conexiones a la vez. El destino tiene recursos finitos: pool de conexiones, sockets y una BD con p. ej. 20 sesiones. En el origen se agotan el pool HTTP/BD propio y los descriptores de archivo del SO. Si ese pool o host lo comparte el tráfico interactivo, el batch deja sin recursos a pagos y login.
  - Virtual threads (Java) y goroutines (Go) caen en la misma trampa: hilos baratos no abaratan el recurso de destino. Con 10.000 hilos y 20 conexiones, 9.980 quedan bloqueados.
- **Metáfora visual del video:** farmacia con un solo farmacéutico que va al depósito y vuelve antes de llamar al siguiente (fila india). Con 10.000 personas gritándole a la vez colapsa; la solución es un mostrador con 5 puestos donde entra uno cuando sale otro.
- **Estrategias / solución:**
  1. **Primero agrupar (batch):** una sola consulta `WHERE sku IN (...)` o un endpoint bulk: un RTT y una evaluación de índice.
  2. **Si no hay batch** (ERP legado): concurrencia acotada con semáforo (p-limit en Node, `SemaphoreSlim` en .NET, `asyncio.Semaphore` en Python), de 5 a 10 llamadas en vuelo; cuando una termina entra la siguiente.
  3. **Secuencial a propósito** cuando el paso 2 depende del 1, o en escrituras donde un fallo debe detener todo para no dejar datos corruptos.
  4. **Paralelo sin límite** solo para un conjunto fijo y pequeño (3–5) de llamadas independientes a destinos con capacidad conocida.
  ```text
  # 1) batch
  stock = inventory.getMany(skus)                    # 1 viaje (partir en chunks si la lista es grande)
  # 2) concurrencia acotada
  sem = Semaphore(8)
  results = awaitAll(skus.map(s -> sem.run(() -> inventory.check(s, timeout=500ms))))
  ```
  - Resultado del video: de 8 s a menos de 1 s sin tumbar el pool del destino.
  - (complemento) Separar pools de conexiones (bulkhead) entre jobs batch y tráfico interactivo; poner timeout por llamada y deadline total. Los webhooks de pasarela deben responder con un ACK rápido (2xx/202), procesar en asíncrono y ser idempotentes.
- **Trade-offs y cuándo NO aplicar:**
  - Batch requiere soporte del destino. (complemento) Hay límites de parámetros (SQL Server ~2100, PostgreSQL 65535 binds) y payloads grandes, así que conviene trocear en chunks.
  - El semáforo obliga a elegir un número. (complemento) Por la ley de Little, concurrencia ≈ throughput × latencia; el límite global que acepta el destino debe repartirse entre las instancias llamadoras, porque el semáforo es por proceso.
  - En paralelo, los fallos parciales son más difíciles (`Promise.all` falla al primer rechazo; `allSettled` o compensaciones), igual que la cancelación y el orden de efectos.
  - No paralelizar escrituras dependientes ni pasos transaccionales.
- **Heurísticas y umbrales:**
  - Aproximadamente 40 ms por RTT (DNS + TLS + procesamiento + regreso). 200 llamadas en serie = 8 s; 1000 = 40 s.
  - Concurrencia acotada de 5–10; una BD destino de ejemplo con 20 sesiones.
  - Regla: si no sabes si llegan 5 o 5000 elementos, nunca uses paralelo ilimitado.
  - Orden de decisión: batch → límite de concurrencia según la capacidad del destino → secuencial si hay dependencia.
  - Cita: "Async libera el hilo de ejecución, no lo multiplica."
- **Anti-patrones / señales de alerta:**
  - `for (...) { await http/db(...) }` sobre ítems independientes (N+1 remoto).
  - `Promise.all(arr.map(call))` / `Task.WhenAll` / `gather` sobre colecciones de tamaño no acotado.
  - Mismo pool HTTP o de BD para batch y para requests de usuario.
  - Asumir que virtual threads o goroutines hacen gratis la concurrencia hacia recursos externos.
  - Tests unitarios con 3 elementos como única validación; código generado por IA que replica ejemplos de documentación (`await` en bucle, `Promise.all` simple) sin revisión de recursos.
  - Handler de webhook que hace trabajo largo antes de responder.
- **Preguntas de revisión arquitectónica:**
  1. ¿Esta operación puede resolverse en un solo viaje (bulk, `IN`, endpoint de lote)?
  2. ¿Cuál es la cardinalidad máxima realista de la colección que se itera?
  3. ¿Qué concurrencia soporta el destino (pool, rate limit, sesiones) y cómo se reparte entre réplicas?
  4. ¿Batch e interactivo comparten pool, host o límite de FDs?
  5. ¿Qué ocurre ante fallos parciales y cuál es el deadline total de la operación?
  6. ¿Los reintentos del llamador (pasarela, usuario) son idempotentes?
- **Caso real / empresa citada:** ninguno; checkout y ERP ilustrativos.
- **Precisión técnica:**
  - "Con 1000 productos la espera sube exponencialmente" es incorrecto: crece linealmente (1000 × 40 ms = 40 s).
  - "Paralelo y limitado para 3–5 peticiones" es un error de ASR/redacción: el caso de 3–5 llamadas pequeñas es *paralelo sin límite*; el semáforo corresponde al tercer escenario.
  - "El SO arroja 504" es impreciso. (complemento) El SO devuelve EMFILE o agota puertos efímeros (TIME_WAIT); el 504 lo emite un gateway o proxy aguas arriba por timeout.
  - (complemento) Con keep-alive y pool de conexiones, DNS y TLS se amortizan: el RTT por llamada suele ser menor que 40 ms. El problema en serie persiste igual.
  - Java no tiene la palabra clave `async`: el equivalente es `CompletableFuture` o virtual threads. FastAPI es el framework; la primitiva es `asyncio`.
