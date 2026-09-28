# [33] Race Conditions explicado: 1 unidad, 2 ventas

> Fuente: TheDebugDuck — https://youtu.be/mEc5a36Mg3Q · notas parafraseadas; «(complemento)» = conocimiento añadido o corrección.
> Estado: elaborado a partir del título y el temario público del video; la transcripción no estuvo disponible (bloqueo de YouTube, 2026-09-28). Lo que no figura en el temario es «(complemento)». Pendiente de contrastar con la transcripción.

- **Síntoma en producción:** queda 1 unidad y salen 2 confirmaciones de compra. Todo funciona hasta que dos usuarios hacen clic al mismo tiempo, y los logs dicen que todo salió bien: dos 200, ningún error. Casi nunca aparece en desarrollo. (complemento) El stock termina en 0, no en −1, así que ningún dashboard lo marca; lo descubre el almacén al buscar la segunda unidad. En local hay un usuario, la BD responde en microsegundos, corre una sola instancia y las pruebas son secuenciales, así que la ventana entre leer y escribir es demasiado corta. En producción la red, el pool y el GC la ensanchan a milisegundos, y los reintentos y el doble clic crean concurrencia del usuario consigo mismo.
- **Causa raíz (mecanismo):** **read-modify-write** no atómico: leer (`stock = 1`), decidir en la app (`> 0`) y escribir el valor calculado (`stock = 0`). Dos peticiones intercaladas leen lo mismo, las dos deciden "hay" y la segunda escritura pisa a la primera (**lost update**). En sistemas distribuidos empeora. (complemento) Una transacción no lo evita por sí sola: en el nivel por defecto de PostgreSQL y SQL Server (READ COMMITTED) y de MySQL (REPEATABLE READ), un `SELECT` simple no bloquea la fila. Con varias réplicas, un lock o mutex en memoria solo protege a su proceso: N réplicas son N candados distintos. Existe una variante sin fila común, el **write skew**: dos transacciones leen el mismo conjunto ("quedan 9 de 10 plazas"), insertan filas distintas y juntas rompen el invariante.
- **Metáfora visual (complemento, propia; la del video no está disponible):** una pizarra frente a una máquina expendedora. Con la pizarra, dos vendedores leen "queda 1", venden, borran y escriben "0": la pizarra queda coherente y se vendieron dos. La máquina comprueba y entrega en un solo movimiento, así que la última lata cae una sola vez. ⚠️ La metáfora no cubre el write skew (dos máquinas de productos distintos cuyo total importa). Tampoco dice que en la BD la "máquina" existe solo si la comprobación va en el mismo `UPDATE`, con lock o con restricción; abrir una transacción no basta.
- **Estrategias / solución:** el temario nombra locks, mutex, transacciones SQL y operaciones atómicas. El detalle por motor es (complemento).
  1. **UPDATE atómico condicional.** Es lo preferido para stock y contadores: la condición va en el `WHERE` y el código comprueba las filas afectadas.
     ```sql
     -- ❌ read-modify-write
     SELECT stock FROM producto WHERE id = :id;                    -- las dos peticiones leen 1
     UPDATE producto SET stock = :stock_calculado WHERE id = :id;   -- las dos escriben 0

     -- ✅ atómico condicional
     UPDATE producto SET stock = stock - :n
      WHERE id = :id AND stock >= :n;      -- 0 filas afectadas → "agotado", sin efecto
     ```
     En PostgreSQL READ COMMITTED, el segundo `UPDATE` espera el lock de fila, **vuelve a evaluar el `WHERE`** sobre la versión confirmada y no afecta filas. InnoDB y SQL Server también actualizan sobre la versión más reciente.
  2. **Bloqueo pesimista.** Úsalo cuando la decisión necesita lógica de la app sobre la fila: `SELECT … FOR UPDATE` dentro de una transacción corta (en SQL Server, `WITH (UPDLOCK, ROWLOCK)`). Toma los locks en orden de ID para evitar deadlocks, fija un `lock_timeout` explícito y nunca hagas una llamada HTTP con el lock tomado.
  3. **Bloqueo optimista con versión.** Úsalo si hay tiempo de usuario entre leer y escribir, o si la contención es baja: `UPDATE … SET …, version = version + 1 WHERE id = :id AND version = :v`. Si afecta 0 filas hay conflicto: relee y reintenta con tope, o responde 409. En JPA, `@Version` lanza `OptimisticLockException`.
  4. **Aislamiento más fuerte para invariantes de varias filas.** Usa `SERIALIZABLE` (SSI en PostgreSQL) y reintenta la transacción completa ante SQLSTATE `40001`. La alternativa es materializar el conflicto: bloquea una fila padre (`SELECT … FROM evento WHERE id = :e FOR UPDATE`) antes de contar.
  5. **Restricción declarativa como última línea de defensa:** `CHECK (stock >= 0)`, `UNIQUE (evento_id, asiento)`, o `EXCLUDE` para rangos (ver [11]). Si el código falla, la BD rechaza la escritura, y ese error se traduce a "agotado".
  6. **Fuera de la BD.** En Redis, `DECRBY` es atómico, pero "leer, comparar y restar" necesita un script Lua o `WATCH`. Un lock distribuido sin fencing no garantiza corrección (ver [11]).
  7. **Detectar bugs de concurrencia** (temario; las técnicas son complemento):
     - Prueba de integración: lanza 2–50 conexiones reales (Testcontainers, no H2) a la vez con una barrera (`CountDownLatch`, o `Promise.all` sobre conexiones distintas). Repite cientos de veces y comprueba el invariante (`vendidas ≤ stock_inicial`, `stock ≥ 0`), no el código HTTP.
     - Para ensanchar la ventana en pruebas, inyecta latencia entre la lectura y la escritura (`pg_sleep`, un breakpoint).
     - Prueba de carga concentrada en **un** SKU (k6/Gatling), no repartida entre muchos.
     - En producción: consultas de invariantes y de reconciliación, alertas por violaciones de `CHECK`/`UNIQUE`, tasa de `40001` y de deadlocks, y dos éxitos sobre el mismo recurso con correlation IDs distintos.
- **Trade-offs y cuándo NO aplicar:** (complemento)
  - `FOR UPDATE` serializa la fila caliente. Con transacciones de 10 ms, el techo teórico ronda 100 operaciones/s por SKU, y cada espera retiene una conexión del pool (ver `datos-persistencia` [09]).
  - El bloqueo optimista desperdicia trabajo con contención alta.
  - `SERIALIZABLE` exige reintentos y aborta más.
  - El `UPDATE` condicional solo sirve si la decisión cabe en un `WHERE` sobre una fila.
  - Para un SKU muy caliente (un drop), ninguna variante escala sin cambiar el modelo: inventario repartido en N cubos, reserva con TTL o fila virtual (`resiliencia-operacion` [21]).
  - Sobra todo esto si el recurso no es escaso y no hay invariante en juego, por ejemplo un contador de vistas aproximado.
- **Heurísticas y umbrales:** (complemento)
  - Elige el mecanismo según la decisión:

    | Si la decisión… | Usa… |
    |---|---|
    | cabe en un `WHERE` | `UPDATE` condicional |
    | necesita lógica de la app sobre una fila | `FOR UPDATE` en transacción corta |
    | tiene tiempo de usuario en medio | versión (bloqueo optimista) |
    | abarca varias filas | `SERIALIZABLE` o lock de la fila padre |

  - Detrás de cualquiera de ellos, siempre una restricción.
  - Comprueba **siempre** las filas afectadas.
  - Reintenta `40001` y los deadlocks como máximo 3 veces, con backoff y jitter.
- **Anti-patrones / señales de alerta:**
  - `if (stock > 0) { stock--; save(); }`. En JPA, el dirty checking escribe el valor absoluto y produce el lost update.
  - `synchronized`, mutex o `lock` en memoria con más de una réplica.
  - Creer que Node.js está a salvo por ser monohilo: cada `await` entre leer y escribir es un punto de intercalado (complemento).
  - `SELECT COUNT(*)` seguido de `INSERT` sin restricción.
  - Poner `@Transactional` como "arreglo" sin cambiar la consulta.
  - Registrar "venta OK" sin mirar las filas afectadas.
  - Probar con H2 o mocks.
  - Mantener un lock pesimista mientras se llama a la pasarela de pago.
- **Preguntas de revisión arquitectónica:**
  1. ¿Qué operaciones hacen read-modify-write sobre un recurso escaso o un contador? ¿La decisión se toma en la app o en el `WHERE`?
  2. ¿Qué restricción de BD hace imposible el estado incorrecto aunque el código falle?
  3. ¿Qué nivel de aislamiento usa realmente la conexión y qué anomalías permite en *este* motor?
  4. ¿Se comprueban las filas afectadas? ¿Qué ve el usuario cuando son 0?
  5. ¿Hay algún lock en memoria que se asume global con varias réplicas o con autoscaling?
  6. ¿Existe una prueba concurrente contra el motor real que falle si se quita la protección?
- **Caso real / referencias (complemento):**
  - Casos reales:
    - Flexcoin (2014): miles de transferencias internas simultáneas movieron fondos antes de que se actualizaran los saldos, y el exchange cerró.
    - Starbucks (2015): transferencias concurrentes entre tarjetas regalo duplicaban saldo (reportado por Egor Homakov).
    - James Kettle (PortSwigger), "Smashing the state machine" (2023): el *single-packet attack*.
  - Fuentes primarias:
    - PostgreSQL 18, "Transaction Isolation": https://www.postgresql.org/docs/current/transaction-iso.html
    - MySQL 8.4, "Transaction Isolation Levels": https://dev.mysql.com/doc/refman/8.4/en/innodb-transaction-isolation-levels.html
    - SQL Server, `SET TRANSACTION ISOLATION LEVEL`: https://learn.microsoft.com/sql/t-sql/statements/set-transaction-isolation-level-transact-sql
    - Kleppmann, *DDIA*, cap. 7.
- **Precisión técnica:**
  - **PostgreSQL, según su documentación** (complemento):
    - READ UNCOMMITTED se comporta como READ COMMITTED.
    - READ COMMITTED permite lecturas no repetibles, fantasmas y anomalías de serialización.
    - REPEATABLE READ (snapshot isolation) evita también los fantasmas, pero permite anomalías de serialización (write skew). Ante un lost update aborta con `40001` "could not serialize access due to concurrent update".
    - SERIALIZABLE (SSI) evita todas estas anomalías a cambio de reintentos.
  - **MySQL/InnoDB** (complemento):
    - En REPEATABLE READ **no** detecta el lost update: el `SELECT` simple lee del snapshot, y el `UPDATE` lee y bloquea lo último confirmado. Hacen falta `FOR UPDATE` o el UPDATE condicional.
    - SERIALIZABLE convierte los `SELECT` en `FOR SHARE` cuando autocommit está desactivado, y cambia lost updates por deadlocks.
    - MariaDB ≥ 11.8 activa `innodb_snapshot_isolation` por defecto y devuelve el error 1020 ante el conflicto.
  - **SQL Server** (complemento):
    - El nivel por defecto es READ COMMITTED con locks; en Azure SQL Database, READ_COMMITTED_SNAPSHOT viene activado por defecto.
    - REPEATABLE READ mantiene locks compartidos hasta el final y suele acabar en deadlock por conversión.
    - SNAPSHOT aborta con el error 3960 por conflicto de actualización.
  - El mismo nombre de nivel no da la misma garantía: REPEATABLE READ significa cosas distintas en PostgreSQL, MySQL y SQL Server (complemento).
  - Race condition ≠ data race. Go `-race` y ThreadSanitizer detectan accesos concurrentes a memoria; un lost update en la BD es una race condition sin data race y no lo ven (complemento).
  - La idempotencia ([34]) y el control de concurrencia se complementan: la clave evita repetir el *mismo* intento, y el control de concurrencia evita que intentos *distintos* se pisen (complemento).
