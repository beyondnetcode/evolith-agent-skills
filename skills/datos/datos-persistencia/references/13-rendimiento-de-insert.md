# [13] El error con Bases de Datos que destruye el rendimiento de tus INSERT

> Fuente: TheDebugDuck — https://youtu.be/-QIMNVAE2c0 · notas parafraseadas; «(complemento)» = conocimiento añadido o corrección.

- **Síntoma en producción:**
  - El reporte pasa de 10 s a < 100 ms tras crear 5 índices. Dos semanas después, cada INSERT tarda ~300 ms y la cola de escritura no baja.
  - En días de alta transaccionalidad (cientos de pedidos/min) se agrava.
  - CPU tranquila, disco al límite.
- **Causa raíz (mecanismo):**
  - Cada índice secundario es otro B-tree que mantener. INSERT = escribir la fila + insertar en cada índice: 5 índices → 6 estructuras tocadas; 100 pedidos → 500 actualizaciones de índice + 100 filas.
  - Cada inserción en un índice implica descender el árbol, posiblemente leer una página fría, posiblemente dividirla y generar registros WAL/redo; las páginas sucias se escriben después.
  - Índices de baja cardinalidad (ciudad con 8 valores sobre 2 M filas ⇒ ~250 000 filas por valor) no discriminan: el optimizador prefiere seq scan, pero el índice sigue ocupando RAM (buffer pool) y disco y encareciendo cada escritura.
  - MVCC de PostgreSQL (caso Uber): un UPDATE crea una nueva versión de la fila en otra ubicación física, y todos los índices deben apuntar a ella aunque su columna no cambie (salvo HOT). En InnoDB los índices secundarios apuntan a la PK: actualizar una columna no indexada no toca los secundarios.
- **Metáfora visual del video:** archiveros: cada índice es un archivero que reordena sus fichas con cada pedido; en el pico llegan todos juntos a cinco archiveros.
- **Estrategias / solución:**
  1. Antes de `CREATE INDEX`: `EXPLAIN ANALYZE` de la query real. Si sigue leyendo casi toda la tabla, el índice no discrimina.
  2. Revisar histograma y estadísticas de la columna (distribución de valores).
  3. Índice compuesto alineado con WHERE + ORDER BY en lugar de varios sueltos (Tumblr: `(blog_id, post_type, created_at)`); primero las columnas de igualdad, luego rango/orden.
  4. Evaluar el coste de escritura: "¿cuántos árboles toca cada insert?" (el video lo usa como pregunta de cierre).
  5. (complemento) Índices parciales, cubrientes (`INCLUDE`), borrar los no usados, `fillfactor` < 100 para favorecer HOT updates en PostgreSQL, `CREATE INDEX CONCURRENTLY`.
  6. (complemento) Si el reporte es analítico: réplica de lectura, read model o almacén columnar en vez de indexar la tabla OLTP.
  ```sql
  -- 1. Plan real, con buffers
  EXPLAIN (ANALYZE, BUFFERS) SELECT ... FROM orders WHERE user_id = $1 ORDER BY created_at DESC LIMIT 50;
  -- 2. Distribución de la columna candidata (PostgreSQL)
  SELECT attname, n_distinct, most_common_vals, most_common_freqs
  FROM pg_stats WHERE tablename = 'orders' AND attname IN ('city','status','user_id');
  -- 3. Un compuesto en lugar de índices sueltos
  CREATE INDEX CONCURRENTLY ix_orders_user_created ON orders (user_id, created_at DESC);
  -- 4. (complemento) Parcial para estados de baja cardinalidad
  CREATE INDEX CONCURRENTLY ix_orders_pending ON orders (created_at) WHERE status = 'pending';
  -- 5. (complemento) Candidatos a borrar
  SELECT relname, indexrelname, idx_scan FROM pg_stat_user_indexes WHERE idx_scan = 0;
  -- SQL Server: sys.dm_db_index_usage_stats (user_updates >> user_seeks + user_scans)
  ```
- **Trade-offs y cuándo NO aplicar:**
  - Los índices aceleran lecturas y penalizan escrituras, RAM y disco.
  - Un compuesto sólo sirve por su prefijo izquierdo: `(a,b,c)` no filtra por `b` sola, salvo skip scan.
  - Cambiar de motor por write amplification (Uber) tiene sus propios costes, y PostgreSQL lo mitiga con HOT.
  - La regla de "pocos índices" no aplica a tablas de mucha lectura y escritura rara (catálogos, históricos cerrados).
- **Heurísticas y umbrales:**
  - N índices → N+1 escrituras lógicas por INSERT.
  - 8 valores distintos / 2 M filas = selectividad inútil. Útil = el filtro reduce drásticamente el rango (`user_id` sí, `ciudad` no).
  - (complemento) Un índice B-tree no cubriente suele elegirse sólo si el predicado devuelve menos de ~5–10 % de la tabla.
  - (complemento) Vigilar la relación `user_updates` vs `user_seeks`.
- **Anti-patrones / señales de alerta:**
  - "Un índice por cada columna del WHERE".
  - Optimizar midiendo sólo el SELECT.
  - Índices sobre booleanos, estados o ciudades sin condición parcial.
  - Índices duplicados o prefijos redundantes (`(a)` junto a `(a,b)`).
  - Índices creados sin `EXPLAIN`.
  - No mirar la latencia de escritura tras añadir índices.
  - Muchos índices en tablas con UPDATE frecuente de estado en PostgreSQL (updates no-HOT).
- **Preguntas de revisión arquitectónica:**
  1. ¿Qué queries usan este índice (plan real), con qué frecuencia y frente a qué ritmo de escritura?
  2. ¿Cuál es la selectividad y la distribución de la columna?
  3. ¿Puede un compuesto (o parcial/cubriente) reemplazar varios sueltos?
  4. ¿Coste de escritura en pico = inserts/updates por segundo × nº de índices?
  5. ¿Hay UPDATE frecuentes de columnas no indexadas? ¿Se aprovechan HOT/fillfactor?
  6. ¿Este reporte debería vivir en otro almacén (réplica, OLAP, read model)?
- **Caso real / empresa citada:**
  - Tumblr: MySQL repartido en varios servidores; índice compuesto por blog, tipo de post y fecha.
  - Uber (post de 2016, "Why Uber Engineering Switched from Postgres to MySQL"): write amplification por índices + MVCC; migraron datos de viajes a Schemaless sobre MySQL/InnoDB.
- **Precisión técnica:**
  - "300 000 ms por registro" = ASR por 300 ms. Aun así, 300 ms por insert es dramatización: mantener 5 índices cuesta de microsegundos a pocos ms con las páginas en RAM. 300 ms indica fallos de caché, disco saturado, locks o fsync lentos.
  - "El disco confirma 6 veces por registro": impreciso. El WAL/redo se escribe en secuencia y se sincroniza (fsync) una vez por COMMIT, con group commit entre transacciones; las páginas de índice se escriben más tarde (checkpoint/background writer). El coste real: volumen de WAL, full-page images, lecturas aleatorias de páginas no cacheadas y write-back.
  - "Un índice de baja cardinalidad nunca ayuda": depende. En PostgreSQL, con distribución sesgada y un valor raro, sí se usa; un parcial o compuesto suele ser mejor. PostgreSQL 18, Oracle y MySQL ≥ 8.0.13 tienen skip scan para compuestos con prefijo de baja cardinalidad. (complemento)
  - Uber/PostgreSQL: los HOT updates (desde 8.3) evitan tocar índices si no cambia ninguna columna indexada y cabe en la página. El problema de Uber fueron muchos updates no-HOT más la replicación física de todo ese WAL. "Cambia cada 2 s" es narrativo.
  - (complemento) En InnoDB el coste se traslada a las lecturas por índice secundario (doble lookup vía PK).
  - El índice exacto de Tumblr es el que cita el video; no está verificado.
