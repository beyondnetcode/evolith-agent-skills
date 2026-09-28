---
name: datos-persistencia
description: Criterio de arquitecto para persistencia y rendimiento de datos — paginación OFFSET vs keyset/cursor, elección de identificadores (bigint, UUIDv4, UUIDv7, Snowflake, ID público opaco), índices y coste de escritura, ORM bien usado (N+1, explosión cartesiana, proyecciones), pool de conexiones y proxies, event sourcing vs UPDATE, y elección/migración de motor (Cassandra → ScyllaDB en Discord). Úsala siempre que un diseño, esquema, migración, PR o incidente toque tablas grandes, consultas lentas, CPU/I/O de base de datos, "funciona en local pero no en producción", timeouts 504 con la BD tranquila, claves primarias, índices nuevos, ORMs (Hibernate/JPA, EF Core, Prisma, TypeORM, Django) o auditoría de historial, aunque el usuario no nombre el patrón.
license: MIT
metadata:
  categoria: datos
  version: "1.0.0"
  idioma: es
  fuentes: "TheDebugDuck: 01, 03, 06, 09, 13, 16, 17, 25, 36"
  relacionadas: "consistencia-distribuida, resiliencia-operacion, radar-arquitectura"
---

# Datos y persistencia

Conocimiento destilado de TheDebugDuck (videos 01, 03, 06, 09, 13, 16, 17, 25, 36) con correcciones por motor. Regla madre: **el coste lo decide el mecanismo físico del motor, no la sintaxis**. Revisar una consulta o un esquema es traducirlo a "qué hace el B-tree, el WAL, el pool o el LSM" con volúmenes de producción.

## Cómo usar esta skill

1. Pide o estima los números que cambian la respuesta: filas y crecimiento, ratio lectura/escritura, distribución (claves calientes), topología (mono-nodo vs distribuida por rangos), motor y versión.
2. Ubica el caso en la matriz y lee la referencia correspondiente; trae SQL de ejemplo, umbrales y precisiones por motor (PostgreSQL, MySQL/InnoDB, SQL Server, Cassandra/Scylla).
3. Entrega con el formato de salida e incluye **cómo verificarlo** (`EXPLAIN ANALYZE`, conteo de queries, métricas del pool).

## Índice de referencias

| Tema | Archivo | Léelo cuando… |
|---|---|---|
| OFFSET profundo vs keyset/cursor | `references/01-paginacion-offset-vs-keyset.md` | listados que crecen sin cota, jobs que recorren tablas |
| UUID vs bigint vs UUIDv7, fragmentación de índices | `references/03-uuid-y-rendimiento-de-indices.md` | elegir o cambiar la PK, IDs expuestos en URLs |
| ORM: sesión, lazy/eager, cartesianos, proyecciones | `references/06-orm-bien-usado.md` | includes anidados, rendimiento de ORM, lectura vs escritura |
| Pool de conexiones, proxies, 504 con BD tranquila | `references/09-bd-miles-de-usuarios.md` | dimensionar pools, autoscaling de pods, PgBouncer/RDS Proxy |
| Índices y coste del INSERT, selectividad, HOT updates | `references/13-rendimiento-de-insert.md` | proponer o auditar índices, escrituras lentas en picos |
| IDs distribuidos tipo Snowflake (Instagram) | `references/16-ids-snowflake-instagram.md` | sharding propio, IDs de 64 bits ordenables sin coordinador |
| Elección y migración de motor (Discord: Mongo → Cassandra → Scylla) | `references/17-discord-cassandra-scylla.md` | working set > RAM, particiones calientes, tombstones, migración en caliente |
| Event sourcing vs UPDATE, auditoría | `references/25-peligro-del-update.md` | "demostrar qué pasó", estado en el instante T, ledgers |
| N+1 queries (JPA/Hibernate, Spring) | `references/36-n-mas-1.md` | endpoints lentos sin error, relaciones lazy, fetch join/EntityGraph |

## Principios (y por qué)

1. **Traduce el código a lo que hace el motor.** Un OFFSET recorre y descarta; un índice se mantiene en cada INSERT; un include anidado multiplica filas. Si no puedes decir qué hace el motor, no puedes aprobar el diseño.
2. **La escala cambia la naturaleza del problema.** 20 filas en local no validan nada; prueba con volumen y distribución de producción y vigila que el working set quepa en RAM.
3. **El orden de las claves depende de la topología.** Claves monótonas son ideales en un B-tree mono-nodo y crean hotspot en bases distribuidas por rangos. No existe un tipo de ID universal.
4. **Toda estructura de acceso cobra en escritura o memoria.** Índices, eager loading, identity maps, proyecciones y logs de eventos trasladan coste; mide ambos lados.
5. **Separa el contrato público del detalle interno**: ID público opaco vs PK, cursor opaco vs offset, DTO de lectura vs entidad. Permite cambiar la implementación sin romper clientes y reduce superficie de ataque (BOLA/IDOR), aunque la autorización por objeto sigue siendo obligatoria.
6. **Acota los recursos compartidos a propósito**: pool pequeño, timeout de adquisición corto, fail fast. Más concurrencia contra un recurso finito baja el throughput.
7. **Leer ≠ escribir.** ORM con unidad de trabajo para modificar agregados; proyecciones o SQL parametrizado para leer; read models para reportes.
8. **Mide por dimensión, no en promedio**: percentiles segmentados por profundidad de página, tamaño de cliente o tenant; conteo de queries por request en CI.
9. **El motor del MVP no es eterno.** Diseña una capa de acceso que permita migrar en caliente (dual write, backfill con checkpoints, validación).
10. **Helpers, generadores e IA reproducen patrones por defecto** (skip/take, includes, `gen_random_uuid()`, IDs expuestos). La pregunta útil no es "¿se lee bien?" sino "¿qué SQL genera y qué pasa en el extremo?".

## Matriz "si ves X → considera Y"

| Si ves… | Considera… |
|---|---|
| `OFFSET` controlado por el usuario sobre tabla sin cota | Keyset `(orden, id)` + índice alineado + cursor opaco; límite de profundidad y filtros obligatorios |
| Job que recorre una tabla con `page++`/`skip` | Keyset por PK con checkpoint y lotes fijos |
| Latencia media sana pero quejas en "casos grandes o antiguos" | Percentiles segmentados por la dimensión sospechosa |
| UUIDv4 como PK en PostgreSQL/MySQL mono-nodo | `bigint identity`, o UUIDv7 si el ID debe nacer fuera de la BD; ID público opaco aparte |
| PK secuencial o UUIDv7 en CockroachDB/Spanner/TiDB | Claves dispersas: UUIDv4, hash-sharded, bit-reversed, `AUTO_RANDOM` |
| PK autoincremental en URLs públicas | ID público opaco con prefijo (`cus_…`) + autorización por objeto |
| `bigint`/Snowflake serializado como número JSON hacia JavaScript | Serializar como string (límite 2^53 − 1) |
| `ALTER COLUMN TYPE` de la PK en tabla grande | Expand/contract: columna paralela, backfill por lotes, dual write, índice concurrente, cambio de FKs |
| `include`/`JOIN FETCH` anidado para una lectura | Proyección a DTO sin tracking, split queries o SQL parametrizado |
| Navegación de entidad dentro de un bucle | Carga por lote (`IN`, batch fetch, EntityGraph) + test que cuente queries |
| `join fetch`/`@EntityGraph` de colección + paginación (aviso HHH90003004) | Paginar IDs en SQL y luego cargar por `IN (:ids)`, o batch fetch; `hibernate.query.fail_on_pagination_over_collection_fetch=true` en CI |
| 504 con CPU de BD baja | Fuga o retención de conexiones: timeout de adquisición 2–3 s, detección de fugas, métricas del pool; buscar I/O remoto dentro de transacciones |
| Propuesta de subir `maxPoolSize` | Medir tiempo de retención; punto de partida `(2 × núcleos de la BD) + discos` |
| Pods × pool > capacidad de la BD | PgBouncer/ProxySQL/RDS Proxy; tope de conexiones en el autoscaling |
| Llamada HTTP o a cola dentro de una transacción | Sacarla; efectos externos por Outbox |
| Propuesta de índice nuevo | `EXPLAIN ANALYZE`, selectividad, compuesto o parcial, coste por INSERT en pico |
| Índice sobre columna de baja cardinalidad | Parcial, compuesto con prefijo selectivo, o eliminarlo |
| UPDATE de estado muy frecuente en PostgreSQL con muchos índices | Menos índices, `fillfactor` para HOT updates, separar el estado caliente en otra tabla |
| Working set creciendo más que la RAM | Particionar por tiempo, archivar, índices compactos, cambio de modelo o de motor |
| Una entidad caliente degrada a todos | Request coalescing, caché, subdividir la clave de partición |
| Borrados masivos en un almacén LSM (Cassandra/Scylla) | TTL, particiones por tiempo que se descartan enteras, vigilar tombstones; no usar LSM como cola |
| Requisito "demostrar qué pasó" o "estado en el instante T" | Event sourcing o alternativas más baratas (tablas temporales, auditoría, CDC, ledger de doble entrada) |
| Replay de proyecciones | Idempotencia por `event_id`/posición, side effects desactivados, ensayo en staging |

## Árbol de decisión: tipo de identificador

```text
¿BD distribuida por rangos (CockroachDB / Spanner / TiDB)?
├─ Sí → claves dispersas (UUIDv4, hash-sharded, bit-reversed). Evita la monotonía.
└─ No (B-tree mono-nodo: PostgreSQL / MySQL / SQL Server)
    ├─ ¿Sharding propio con muchos generadores sin coordinador? → Snowflake-like de 64 bits
    │     (guardia de reloj, worker IDs únicos, string en JSON)
    ├─ ¿El ID debe existir antes del INSERT (offline, idempotencia, microservicios)? → UUIDv7
    │     (SQL Server: BINARY(16) o NEWSEQUENTIALID; uniqueidentifier NO ordena un v7)
    └─ En otro caso → bigint identity
Siempre: si se expone fuera → ID público opaco separado + autorización por objeto.
```

## Preguntas de revisión

1. ¿Cuántas filas tendrá esta tabla en 2 años y qué consulta la recorre?
2. ¿Qué SQL real genera este código (log SQL) y cuántas queries por request? ¿Es O(1) o O(N)?
3. ¿Qué índice sirve a cada consulta crítica y cuánto cuesta en cada INSERT/UPDATE en pico?
4. ¿Cuál es el tamaño del pool, cuántas réplicas × pool llegan a la BD y qué pasa al agotarse?
5. ¿Hay I/O remoto dentro de una transacción?
6. ¿El ID es seguro de exponer y la autorización es por objeto?
7. ¿El working set cabe en RAM? ¿Qué clave de partición puede volverse caliente?
8. ¿Cómo se migra este esquema sin downtime (expand/contract) y cómo se revierte?

## Precisiones por motor que los videos simplifican (no las repitas)

- PostgreSQL: el heap **no** está ordenado por la PK; UUIDv4 daña el índice PK y el WAL. `uuidv7()` es nativo desde PostgreSQL 18. `ALTER COLUMN TYPE` reescribe la tabla bajo `ACCESS EXCLUSIVE`.
- InnoDB no "reordena toda la tabla" con UUIDv4: provoca splits y fragmentación del índice agrupado.
- SQL Server compara `uniqueidentifier` empezando por los últimos bytes: un UUIDv7 ahí **no** queda secuencial.
- El WAL hace fsync **por COMMIT** (con group commit), no por índice; el coste de índices es volumen de WAL, full-page images y lecturas aleatorias de páginas no cacheadas.
- Un índice de baja cardinalidad puede servir con distribución sesgada (valor raro), como parcial, o con skip scan (PostgreSQL 18, Oracle, MySQL ≥ 8.0.13).
- No todos los ORMs tienen sesión/identity map: Hibernate/JPA, EF Core, NHibernate y SQLAlchemy sí; Prisma, Django y TypeORM (por defecto) no. En JPA, `@ManyToOne`/`@OneToOne` son EAGER por defecto: fuente clásica de N+1 inesperados.
- EAGER no evita el N+1: en JPQL o consultas derivadas, las relaciones to-one EAGER sin `join fetch` se cargan con SELECT secundarios. Spring Boot activa open-in-view por defecto y esconde cargas lazy durante la serialización.
- La fórmula de pool es `(núcleos × 2) + discos efectivos` **del servidor de BD**, como punto de partida; "pool pequeño gana" vale para OLTP de consultas cortas.
- Instagram generaba IDs combinando tiempo y `nextval() % 1024` sin estado entre sesiones; la guardia contra reloj que retrocede es de Snowflake (Twitter).
- UPDATE es correcto para la mayoría de los datos; el problema es usarlo cuando el requisito es historial auditable. Event sourcing no es la única vía.

## Formato de salida

```
Decisión: <cambio concreto de esquema/consulta/configuración>, en una línea.
Mecanismo del motor: <qué hace hoy el motor y qué hará con el cambio>.
Números: <volumen, selectividad, pool, coste por escritura; supuestos explícitos>.
Cómo verificarlo: <EXPLAIN ANALYZE, conteo de queries, métrica del pool, prueba con volumen real>.
Migración y reversa: <expand/contract, backfill, rollback>.
Trade-offs: <coste de escritura, memoria, complejidad>.
Fuente: <referencia(s) y video(s)>.
```
