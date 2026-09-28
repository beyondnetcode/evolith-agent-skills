# [17] Discord vs. Trillones de mensajes: ¿Por qué falló Cassandra?

> Fuente: TheDebugDuck — https://youtu.be/_LTWThujNwk · notas parafraseadas; «(complemento)» = conocimiento añadido o corrección.

- **Síntoma en producción:**
  - Carga lenta del historial antiguo (el cliente se queda cargando) y latencia impredecible.
  - Con Cassandra: picos de latencia en todo el clúster por un único canal caliente; pausas de GC; repairs que no terminan; lecturas lentas por tombstones.
  - Coste operativo creciente (12 → 177 nodos) y guardias "apagando incendios" sin saber si el culpable era el GC, un nodo o un repair.
- **Causa raíz (mecanismo):**
  - MongoDB (un solo replica set, índice `(channel_id, created_at)`): en nov-2015 (~100 M mensajes) datos + índice dejan de caber en RAM → las lecturas de historial van a disco → latencia impredecible; escribir sigue siendo barato.
  - Cassandra (LSM, append-only; partición `(channel_id, bucket)`, clustering por `message_id` Snowflake): escrituras baratas, lecturas más caras (memtable + varios SSTables).
  - Partición caliente: un canal enorme con `@everyone` concentra las lecturas en las réplicas de una partición. Con lecturas por QUORUM, el nodo retrasado arrastra la latencia del anillo.
  - JVM: pausas de garbage collection congelan el nodo; tuning continuo de heap y GC.
  - Mantenimiento: compactaciones atrasadas (el "gossip dance": sacar el nodo del anillo para compactar sin tráfico y reincorporarlo) y repairs cada vez más lentos con trillones de filas.
  - Borrar = tombstones que persisten hasta la compactación; las lecturas de rango arrastran tumbas (CPU y disco en datos muertos). El migrador se atascó en 99,9999 % por rangos con tombstones masivos; tras compactarlos terminó en segundos.
- **Metáfora visual del video:** libreta rápida en el mostrador (MongoDB) → anillo/ejército de archivadores idénticos (Cassandra) → los mismos archivadores reconstruidos en C++ con menos de la mitad de máquinas (ScyllaDB). Almacén donde la mesa de trabajo es la RAM y el sótano, el disco.
- **Estrategias / solución:**
  1. Arranque deliberadamente simple (MongoDB replica set sin sharding), sabiendo que es provisional.
  2. Modelo de partición que acote su tamaño: `((channel_id, bucket), message_id)`, con bucket = ventana temporal fija.
  3. Capa de servicios de datos (Rust, gRPC) entre la API y la BD: *request coalescing* (1 000 lecturas idénticas → 1 consulta) y enrutamiento consistente por `channel_id` (mismo canal → mismas instancias, lo que maximiza el coalescing).
  4. Motor sin GC y shard-per-core (ScyllaDB, compatible con el protocolo de Cassandra): 177 → 72 nodos, latencia más estable, repairs más rápidos.
  5. Migración en caliente: dual write + backfill con un migrador propio en Rust con checkpoints en SQLite; 3,2 M mensajes/s, 9 días frente a 3 meses estimados; compactar los rangos con tombstones para cerrar.
  6. Migrar primero los clusters menores para ganar experiencia antes del crítico.
  ```sql
  -- CQL (Cassandra/ScyllaDB)
  CREATE TABLE messages (
    channel_id bigint,
    bucket     int,          -- ventana temporal derivada del timestamp del Snowflake (Discord: 10 días)
    message_id bigint,       -- Snowflake: ordenable por tiempo
    author_id  bigint,
    content    text,
    PRIMARY KEY ((channel_id, bucket), message_id)
  ) WITH CLUSTERING ORDER BY (message_id DESC);
  ```
  ```text
  // Request coalescing (singleflight) en la capa de datos
  inflight: map<key, Future>
  get(key):
    if key in inflight: return await inflight[key]
    f = consultarBD(key); inflight[key] = f
    try: return await f  finally: inflight.remove(key)
  // + enrutamiento por hash(channel_id) para que peticiones iguales caigan en la misma instancia
  ```
- **Trade-offs y cuándo NO aplicar:**
  - MongoDB con un solo replica set: rápido de construir, techo de RAM.
  - Cassandra: escala lineal y tolerancia a fallos a cambio de modelar por consulta, particiones calientes, tombstones y operación de JVM.
  - ScyllaDB: menos nodos y sin GC, pero exige la misma disciplina de modelado.
  - La capa de datos intermedia es otro componente a operar, pero habilita coalescing, enrutamiento y migraciones.
  - Buckets más pequeños → más particiones por cada lectura de historial.
  - (complemento) Cuándo NO: a escala pequeña o mediana, un relacional con particionado por tiempo suele bastar; el wide-column sólo se justifica con patrones de acceso conocidos y volumen masivo.
- **Heurísticas y umbrales:**
  - El working set (datos calientes + índices) debe caber en RAM.
  - Hitos: nov-2015, 100 M mensajes; 2017, 12 nodos; 2022, 177 nodos y trillones de filas; ScyllaDB, 72 nodos; migración a 3,2 M msg/s en 9 días (vs 3 meses); atasco en 99,9999 %.
  - (complemento) Discord usó buckets de 10 días. Cassandra: particiones < ~100 MB; `tombstone_warn_threshold` 1 000 / `failure` 100 000; `gc_grace_seconds` = 10 días por defecto.
- **Anti-patrones / señales de alerta:**
  - Partición por entidad sin límite temporal (crece sin fin).
  - Borrados masivos o colas sobre Cassandra.
  - Lecturas QUORUM sin mitigar particiones calientes.
  - Ignorar el tamaño del índice frente a la RAM en MongoDB.
  - Migraciones big-bang con parada.
  - Migradores sin checkpoints ni reanudación.
  - Acoplar la app directamente al motor, sin una capa de acceso que permita cambiarlo.
- **Preguntas de revisión arquitectónica:**
  1. ¿Cuál es el working set y cuándo dejará de caber en RAM?
  2. ¿La clave de partición acota el tamaño y reparte la carga? ¿Qué pasa con la entidad más caliente (canal con `@everyone`, cuenta celebridad)?
  3. ¿Hay deduplicación/coalescing de lecturas idénticas concurrentes?
  4. ¿Qué patrón de borrado/TTL tiene el modelo y cómo afecta a tombstones y compactación?
  5. ¿Plan de migración en caliente: dual write, backfill con checkpoints, validación, rollback?
  6. ¿Qué coste operativo (GC, repairs, compactación) asume el equipo y está dimensionado?
- **Caso real / empresa citada:** Discord ("How Discord Stores Billions of Messages", 2017; "How Discord Stores Trillions of Messages", 2023).
- **Precisión técnica:**
  - ASR: "Mongoi" = MongoDB; "Skila divi / Sila / Esquila" = ScyllaDB; "Channel ID más mesa" = `channel_id` + bucket; "gosip dance" = gossip dance; "rost" = Rust; "Sequalite" = SQLite; "@evone" = `@everyone`; "quóum" = quorum.
  - "Java no suelta memoria solo": simplificación. El problema son las pausas stop-the-world del GC con heaps grandes; ZGC/Shenandoah las reducen, pero Discord eligió eliminar la JVM.
  - "Cada núcleo maneja su shard": correcto (arquitectura Seastar shard-per-core).
  - (complemento) Resultados publicados por Discord: p99 de lectura de 40–125 ms (Cassandra) a ~15 ms (ScyllaDB); p99 de inserción de 5–70 ms a ~5 ms estables.
  - "Mongo → Cassandra en una semana": cifra del video; la migración se completó a inicios de 2017.
