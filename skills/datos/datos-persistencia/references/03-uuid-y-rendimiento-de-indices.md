# [03] El error con UUIDs que destruye el rendimiento de tu Base de Datos

> Fuente: TheDebugDuck — https://youtu.be/KiuZT8XYYdw · notas parafraseadas; «(complemento)» = conocimiento añadido o corrección.

- **Síntoma en producción:**
  - ~3 meses después del lanzamiento, los INSERT de pedidos se vuelven lentos; disco leyendo y escribiendo sin parar; el índice PK crece más rápido que los datos y deja de caber en RAM → tormenta de I/O aleatorio.
  - Con IDs secuenciales expuestos: IDOR (cambiar `/pedidos/1847` por `1846`) y fuga de métricas de negocio (dos compras con IDs 1847 y 1910 revelan 63 ventas en ese intervalo).
  - Con IDs de 64 bits en JSON: dos entidades distintas con el mismo ID en el navegador (redondeo).
  - En BD distribuidas con IDs secuenciales: un nodo al 100 % de escrituras (hotspot) y el resto ocioso.
- **Causa raíz (mecanismo):**
  - B-tree con clave monótona: la inserción siempre va a la hoja más a la derecha, que está caliente en RAM; los splits son "por el final" y baratos. (complemento) PostgreSQL ≥ 11 cachea la hoja derecha (fastpath); InnoDB detecta inserción secuencial y llena páginas ~15/16.
  - UUIDv4 aleatorio: cada inserción cae en una hoja arbitraria → leer página fría del disco, split 50/50 (páginas medio vacías → índice más grande y menos cacheable), reescribir. El working set pasa a ser el índice completo; al superar la RAM el hit ratio se desploma.
  - (complemento) PostgreSQL con `full_page_writes`: la primera modificación de cada página tras un checkpoint escribe la página completa en el WAL; inserciones aleatorias tocan miles de páginas distintas → el volumen de WAL y de replicación se multiplica.
  - InnoDB: la tabla ES el índice agrupado por PK → un UUID aleatorio fragmenta la propia tabla, y cada índice secundario almacena la PK (16 bytes, o 36+ si es `CHAR(36)`), inflando todos los índices.
  - BD distribuidas por rangos (CockroachDB, TiDB, Spanner): las claves secuenciales concentran todas las escrituras nuevas en el último rango → un único nodo/leaseholder hace todo el trabajo.
  - JavaScript: `Number` sólo representa enteros exactos hasta 2^53 − 1; un ID de 64 bits se redondea al parsear JSON.
- **Metáfora visual del video:** taquillas de un centro de paquetes: serial = abrir la siguiente puerta libre al final del pasillo (rápido, pero el número revela el volumen); UUIDv4 = código aleatorio que obliga a buscar huecos por todo el edificio; UUIDv7 = código inadivinable, pero las puertas de hoy se llenan en orden.
- **Estrategias / solución:**
  1. Separar la PK interna (optimizada para el motor) del ID público (contrato y seguridad). Frase clave: "La llave primaria existe para optimizar el índice."
  2. Relacional de un solo nodo con IDs internos: `bigint` identity (8 bytes).
  3. Generación descentralizada (el cliente o el microservicio crea el ID antes de insertar) + motor B-tree: UUIDv7 (48 bits iniciales = timestamp Unix en ms; RFC 9562, 2024).
  4. BD distribuida por rangos: UUIDv4 u otras claves que dispersen la carga. (complemento) CockroachDB `gen_random_uuid()` o índices hash-sharded; Spanner UUIDv4 o secuencias bit-reversed; TiDB `AUTO_RANDOM`.
  5. IDs de 64 bits hacia navegadores: serializar como string (Twitter añadió `id_str`).
  6. Migración de tipo de PK en tabla grande: nunca reescritura en caliente. Columna paralela → backfill por lotes → escritura dual → índices creados en línea → migrar FKs → medir el tamaño del índice frente a la RAM → retirar la clave antigua.
  7. Snowflake/IDs distribuidos sólo cuando haya sharding real; implica sincronizar relojes y cuidar la precisión en JS.
  ```sql
  CREATE TABLE orders (
    id         bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,  -- interno, nunca sale de la API
    public_id  text   NOT NULL UNIQUE,                           -- p. ej. 'ord_' + token aleatorio opaco
    customer_id bigint NOT NULL REFERENCES customers(id),
    created_at timestamptz NOT NULL DEFAULT now()
  );
  -- La API recibe /orders/{public_id}; se resuelve a id y se autoriza por propietario en cada acceso.
  ```
- **Trade-offs y cuándo NO aplicar:**
  - `bigint`: 8 B, índices y FKs pequeños, orden natural. Contras: secuencia central; revela volumen si se expone; colisiones al fusionar BDs.
  - UUIDv4: generación independiente, no enumerable. Contras: fragmentación en B-tree, doble tamaño, sin orden.
  - UUIDv7: ordenable + generación independiente. Contras: 16 B; (complemento) revela el instante de creación, así que no conviene como ID público si esa fecha es sensible; puede volver a crear hotspots en BD distribuidas; el orden dentro del mismo ms depende de la implementación.
  - Snowflake: 64 bits ordenable sin coordinador. Contras: dependencia de relojes, asignación de IDs de worker/shard, precisión en JS; complejidad injustificada en un monolito con un solo PostgreSQL (el video lo compara con aplicar arquitectura hexagonal a un formulario de registro).
  - ID público opaco: columna e índice único adicionales y un lookup extra.
- **Heurísticas y umbrales:**
  - Decidir por 3 factores: **infraestructura** (B-tree mono-nodo vs rangos distribuidos), **visibilidad** (expuesto vs interno), **generación** (¿hace falta el ID antes de insertar y sin secuencia central?).
  - 8 B vs 16 B por fila; el sobrecoste se replica en cada FK e índice que referencia la PK (el video menciona 10 tablas relacionadas).
  - `Number.MAX_SAFE_INTEGER` = 2^53 − 1 ≈ 9·10¹⁵.
  - Los defaults autoincrementales de Prisma/Entity Framework no son ingenuos: protegen la salud del B-tree.
- **Anti-patrones / señales de alerta:**
  - `DEFAULT gen_random_uuid()` como PK en PostgreSQL mono-nodo "porque es más profesional/distribuido".
  - (complemento) UUID guardado como `CHAR(36)`/`VARCHAR` (36+ bytes y comparación con collation).
  - PK autoincremental en rutas públicas + autorización limitada a "está autenticado".
  - IDs `bigint` serializados como número JSON hacia JavaScript.
  - `SERIAL` o clave secuencial como PK en CockroachDB/Spanner.
  - `ALTER COLUMN ... TYPE` de la PK en una tabla de decenas de GB.
  - Generador Snowflake propio en un monolito con una sola BD.
- **Preguntas de revisión arquitectónica:**
  1. ¿Motor B-tree mono-nodo o distribuido por rangos? ¿Puede cambiar en 3 años?
  2. ¿El ID aparece en URLs/APIs? ¿Existe un ID público distinto de la PK?
  3. ¿Quién genera el ID y cuándo (cliente offline, microservicio, clave de idempotencia previa al insert)?
  4. ¿La autorización valida la propiedad del recurso con independencia del tipo de ID?
  5. ¿Cómo viaja el ID a clientes JS: número o string?
  6. ¿Cuánto pesarán PK + índices FK + secundarios frente a la RAM disponible?
- **Caso real / empresa citada:** Instagram 2012 (ID de 64 bits tiempo + shard); Twitter Snowflake y `id_str`; documentación de CockroachDB sobre hotspots; Stripe (IDs públicos con prefijo).
- **Precisión técnica:**
  - "CPU alta buscando espacio libre en disco": impreciso. El coste es I/O aleatorio, fallos del buffer pool, splits y amplificación de WAL; la CPU suele aparecer como espera de I/O.
  - PostgreSQL: el heap NO está ordenado por la PK; el daño recae en el índice PK (y en el WAL), no en el orden de la tabla.
  - InnoDB "reordena físicamente toda la tabla en cada inserción": exagerado. Provoca splits y fragmentación del índice agrupado, no una reescritura completa.
  - "UUID de 36 caracteres": son 128 bits (16 B); 36 caracteres es la representación textual.
  - Instagram (post de 2012): descartó los UUID por tamaño y falta de orden temporal. No documentó un colapso en producción con UUID como PK; la narración lo dramatiza.
  - "Ni VACUUM FULL ni OPTIMIZE TABLE lo recuperan": exagerado. Ambos reconstruyen compacto (con bloqueo exclusivo); el problema es que los nuevos inserts aleatorios vuelven a fragmentar. El riesgo real: en PostgreSQL, `ALTER COLUMN TYPE` reescribe la tabla bajo `ACCESS EXCLUSIVE`.
  - Stripe usa guion bajo: `cus_…`, `pi_…` (no guion).
  - (complemento) Soporte de UUIDv7: PostgreSQL 18 (sept. 2025) incluye `uuidv7()` nativo; en versiones anteriores, extensión o generación en la app. MySQL no tiene v7 nativo (`UUID_TO_BIN(u, 1)` sólo reordena v1). SQL Server: `uniqueidentifier` compara empezando por los últimos bytes → un UUIDv7 en esa columna NO queda secuencial; usar `NEWSEQUENTIALID()` o `BINARY(16)`.
  - (complemento) IDOR (OWASP API1: BOLA): el ID opaco es defensa en profundidad; la corrección real es la autorización por objeto.
