# [16] Cómo Instagram genera 1.000.000 de IDs por segundo sin colisiones (Snowflake + Postgres)

> Fuente: TheDebugDuck — https://youtu.be/-8WFjecvWQU · notas parafraseadas; «(complemento)» = conocimiento añadido o corrección.

- **Síntoma en producción:**
  - (narrativo) Fotos fechadas el 1/1/1970 por un timestamp 0 dentro del ID.
  - En general: la secuencia central se vuelve el límite al crecer (2012, 14 M usuarios).
  - UUID aleatorio como PK en PostgreSQL → I/O aleatorio en el índice.
  - Relojes desincronizados → IDs repetidos y violaciones de PK.
- **Causa raíz (mecanismo):**
  - Una secuencia en un único nodo es un punto único de coordinación. Con los datos repartidos entre servidores/shards hacen falta IDs globalmente únicos sin coordinador.
  - UUID aleatorio resuelve la coordinación pero rompe la localidad del B-tree y no aporta orden temporal (misma mecánica que [03]).
  - Esquema Snowflake: el ID codifica tiempo + origen + secuencia → unicidad por construcción (dos shards nunca comparten los bits de shard; dentro de un shard y ms, el contador desempata).
  - Depende del reloj: si retrocede (salto de NTP), el generador puede reemitir combinaciones ya usadas.
  - Con el tiempo en los bits altos, las inserciones van al final del B-tree (hit ratio alto) y ordenar por ID ≈ ordenar por tiempo.
- **Metáfora visual del video:** fábrica de matrículas: un empleado con un sello numerador (secuencia) → la fila dobla la cuadra; códigos aleatorios (UUID) → sin orden; "placa inteligente" de 64 bits estampada por 1 000 mesas independientes calibradas al milisegundo.
- **Estrategias / solución:**
  - Layout de 64 bits: 41 bits de ms desde una época propia (2011; ~69 años de rango → ~2080) | 13 bits de shard lógico (8 192) | 10 bits de secuencia (1 024 IDs/ms/shard ≈ 1 M IDs/s por shard).
  - Generación dentro de la BD: función PL/pgSQL como `DEFAULT` de la PK, con una secuencia por tabla y shard lógico (`nextval % 1024`) → sin servicio externo ni coordinación entre shards.
  - Shards lógicos (miles) mapeados a menos servidores físicos: escalar = mover shards lógicos, sin tocar la lógica del ID.
  - Relojes: NTP (error < 1 ms en la nube) + guardia monotónica: si `now < last_ts`, esperar (o fallar) hasta alcanzarlo; si se agota el contador en el ms, esperar al siguiente.
  - Multi-región: rangos de shard ID disjuntos por región.
  - `ORDER BY id DESC` como orden cronológico (aproximado) del feed, sin columna de fecha adicional.
  ```text
  EPOCH = <ms de una fecha fija de 2011>
  id = ((now_ms - EPOCH) << 23) | (shard_id << 10) | (seq % 1024)

  // Guardia monotónica (estilo Snowflake; en proceso con estado)
  now = reloj_ms()
  if now < last_ts:
      if last_ts - now > MAX_SKEW: fallar y alertar
      esperar hasta now >= last_ts
  if now == last_ts: seq = (seq + 1) & 1023; if seq == 0: esperar al siguiente ms
  else: seq = 0
  last_ts = now
  ```
  (complemento) En la función SQL, usar `clock_timestamp()` y no `now()`, que devuelve el inicio de la transacción.
- **Trade-offs y cuándo NO aplicar:**
  - Sólo compensa con sharding real o generación masiva distribuida. Si basta el autoincrement, no tocarlo (conclusión explícita del video).
  - 41 bits de tiempo = fecha de caducidad (~69 años desde la época).
  - Entre shards el orden es aproximado (resolución de ms + desfase de relojes): no usarlo para causalidad.
  - Revela el instante de creación y el shard.
  - 64 bits > 2^53 → string en JSON.
  - Asignar IDs de shard/worker es un problema operativo; los 10 bits de secuencia limitan las ráfagas por ms.
- **Heurísticas y umbrales:**
  - 41 + 13 + 10 = 64 bits; 1 024 IDs/ms/shard; 8 192 shards; 2^41 ms ≈ 69,7 años.
  - NTP < 1 ms.
  - Instagram: 14 M usuarios en 2012 y > 2 000 M MAU hoy.
  - (complemento) Twitter Snowflake: 1 bit de signo + 41 de tiempo + 10 de máquina + 12 de secuencia.
- **Anti-patrones / señales de alerta:**
  - IDs basados en timestamp sin guardia contra retroceso del reloj.
  - (complemento) IDs de worker/shard asignados a mano sin garantía de unicidad (dos pods con el mismo worker ID en autoscaling).
  - Confiar en un orden global exacto por ID entre nodos.
  - (complemento) Upsert (`ON CONFLICT DO UPDATE`) sobre una PK generada: convierte una colisión en sobrescritura silenciosa.
  - Enviar el ID a JavaScript como número.
  - Adoptarlo con un único PostgreSQL.
- **Preguntas de revisión arquitectónica:**
  1. ¿Hay realmente múltiples generadores sin coordinador? ¿Por qué no basta identity/secuencia?
  2. ¿Cómo se asignan los IDs de shard/worker y cómo se garantiza su unicidad, también con autoscaling?
  3. ¿Qué pasa si el reloj retrocede: esperar, fallar, alertar?
  4. ¿Qué época y cuántos bits de tiempo? ¿Cuándo se agotan?
  5. ¿El orden por ID tiene semántica de negocio o sólo de UX?
  6. ¿Cómo viaja el ID a clientes JS?
- **Caso real / empresa citada:** Instagram 2012 ("Sharding & IDs at Instagram"); Twitter Snowflake (2010).
- **Precisión técnica:**
  - El bug de "1970" no está documentado públicamente (que se sepa); tratarlo como recurso narrativo.
  - Motivación real: Instagram no abandonó la secuencia porque "un empleado" fuera lento. Shardeó sus datos en miles de shards lógicos sobre varios servidores PostgreSQL y necesitaba IDs de 64 bits, únicos y ordenables sin servicio central (descartó ticket servers estilo Flickr y UUIDs).
  - UUID en Instagram: lo evaluó y lo descartó por 128 bits y falta de orden temporal; no documentó una "tormenta de I/O" en producción.
  - "La función PL/pgSQL guarda en memoria el último timestamp y espera": no es lo que publicó Instagram. Su función combina tiempo y `nextval() % 1024` sin estado entre sesiones; la guardia contra retroceso es propia de Snowflake (Twitter rechaza generar si el reloj retrocede). La secuencia monotónica reduce la probabilidad de colisión incluso con retroceso: sólo choca si `seq % 1024` coincide en un ms repetido.
  - "La colisión sobrescribe sin que nadie lo note": en una BD relacional una PK duplicada falla con error; sólo hay sobrescritura silenciosa con upsert o en almacenes last-write-wins (Cassandra).
  - "Generar el ID en Python cuesta dos viajes de red": impreciso, generarlo en la app no requiere red. La ventaja real de hacerlo en la BD es no depender del reloj ni del estado de cada app server y ligar el shard ID al esquema.
  - "Hasta 1 000 shards lógicos": el post habla de varios miles; los 13 bits permiten 8 192.
  - Los rangos de shard por región son plausibles, pero no figuran en la fuente original.
