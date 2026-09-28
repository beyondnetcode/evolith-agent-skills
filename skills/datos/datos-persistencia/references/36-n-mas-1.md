# [36] ¿Por qué tu API está lenta? (N+1 explicado fácil)

> Fuente: TheDebugDuck — https://youtu.be/T3zUdZGe7mk · notas parafraseadas; «(complemento)» = conocimiento añadido o corrección.
> Estado: elaborado a partir del título y el temario público del video; la transcripción no estuvo disponible (bloqueo de YouTube, 2026-09-28). Lo que no figura en el temario es «(complemento)». Pendiente de contrastar con la transcripción.

- **Síntoma en producción:**
  - La API está lenta y no hay errores (contexto del video: Spring Boot con JPA/Hibernate).
  - (complemento) La BD no se satura por una consulta pesada, sino por cientos o miles de consultas cortas idénticas.
  - (complemento) La latencia crece linealmente con el tamaño de página o con la antigüedad del cliente. En local, con 3 filas, no se nota.
  - (complemento) Bajo carga se agota el pool y aparecen 504 ([09]).
  - (complemento) En el APM se ve una "escalera" de spans `SELECT … WHERE cliente_id = ?` dentro de una sola traza.
- **Causa raíz (mecanismo):**
  - Una consulta trae N padres. Al tocar una relación **lazy** de cada uno (en un bucle, en el mapper o al serializar), Hibernate inicializa el proxy o la colección con un `SELECT` por padre: 1 + N consultas, cada una con su RTT y su checkout del pool.
  - (complemento) En JPA, `@OneToMany`/`@ManyToMany` son LAZY por defecto, pero `@ManyToOne`/`@OneToOne` son EAGER. Un `findAll()` o un JPQL sin `join fetch` dispara SELECT secundarios para cada to-one EAGER: N+1 sin haber tocado nada.
  - (complemento) Spring Boot activa Open Session in View por defecto y lo avisa al arrancar. Eso permite cargas lazy durante la serialización con Jackson y esconde el problema fuera de la capa de servicio.
- **Metáfora visual (complemento, propia; la del video no está disponible):** un mesero con una mesa de 50 comensales.
  - Trae la lista de comensales y luego va a la cocina una vez por cada plato: 51 viajes.
  - `fetch join` = una bandeja con todo.
  - Batch fetch = bandejas de 25.
  - Proyección DTO = traer solo lo que se pidió, sin la vajilla.
  - ⚠️ Límite: con colecciones, la bandeja única de dos colecciones multiplica filas (producto cartesiano), y paginar esa bandeja ocurre en memoria.
- **Estrategias / solución:**
  1. **Detectar con logs SQL** (temario):
     - `logging.level.org.hibernate.SQL=DEBUG`, y además `org.hibernate.orm.jdbc.bind=TRACE` en Hibernate 6 (complemento).
     - (complemento) `spring.jpa.properties.hibernate.generate_statistics=true` imprime por sesión cuántas sentencias JDBC se ejecutaron.
     - La misma consulta repetida con distinto parámetro = N+1.
  2. **Test que cuenta queries** (complemento). Afirma el número de sentencias por caso de uso con `Statistics#getPrepareStatementCount` de Hibernate, datasource-proxy o `SQLStatementCountValidator` (Hypersistence Utils). El test falla si la página de 1 y la de 50 no generan el mismo número.
  3. **Detectar en producción** (temario; herramientas complemento):
     - Número de spans de BD por traza (OpenTelemetry, Datadog).
     - Detector de N+1 de Sentry.
     - `pg_stat_statements`: una consulta con `calls` enorme y `mean_exec_time` mínimo.
  4. **Fetch join.** Úsalo para relaciones to-one y para **una** colección sin paginar:
     ```java
     // Spring Data JPA (reescrito)
     @Query("select p from Pedido p join fetch p.cliente where p.estado = :estado")
     List<Pedido> pendientesConCliente(Estado estado);     // to-one: compatible con paginación
     ```
  5. **`@EntityGraph`.** Declara el plan de carga por método sin reescribir el JPQL: `@EntityGraph(attributePaths = {"cliente"})`. Por debajo es un fetch join: con colecciones hereda sus mismos límites.
  6. **Batch fetch** (complemento en detalle):
     - Con `spring.jpa.properties.hibernate.default_batch_fetch_size=50` o `@BatchSize(size = 50)`, las inicializaciones lazy se agrupan en `IN (…)`: 1 + ⌈N/50⌉ consultas.
     - `@Fetch(FetchMode.SUBSELECT)` carga en una sola consulta las colecciones de todos los padres de la consulta anterior.
     - Es la opción que mejor convive con la paginación del padre.
  7. **Proyecciones DTO** para lecturas: `select new com.acme.PedidoResumen(p.id, c.nombre, p.total) from Pedido p join p.cliente c`, o proyecciones de interfaz o record de Spring Data. No hay entidades gestionadas, ni proxies, ni dirty checking. Si el DTO lleva colecciones: segunda consulta con `IN (:ids)` y ensamblado en memoria.
  8. **Paginación correcta.** No combines nunca un `join fetch`/`@EntityGraph` de colección con `Pageable`. Hibernate no emite `LIMIT`: trae todo, pagina en memoria y avisa con `HHH90003004: firstResult/maxResults specified with collection fetch; applying in memory` (en Hibernate 5 era `HHH000104`) (complemento). Patrón en dos consultas:
     ```java
     Page<Long> ids = repo.idsPorEstado(estado, pageable);        // LIMIT/OFFSET o keyset en SQL ([01])
     List<Pedido> pedidos = repo.conItemsPorIds(ids.getContent()); // join fetch p.items where p.id in :ids
     // reordenar según ids; en CI: hibernate.query.fail_on_pagination_over_collection_fetch=true (complemento)
     ```
  9. **Cortar las cargas invisibles** (complemento): `spring.jpa.open-in-view=false`, mapear a DTO dentro del servicio transaccional y no serializar entidades.
- **Trade-offs y cuándo NO aplicar:** (complemento)
  - El fetch join de colecciones duplica filas por padre. Con dos colecciones produce un cartesiano; si las dos son `List`, lanza `MultipleBagFetchException`.
  - El batch fetch no elimina consultas: las acota.
  - Los DTOs multiplican tipos.
  - Las dos consultas cuestan dos viajes, pero la paginación ocurre en SQL.
  - Un N+1 con N pequeño y acotado (≤ 3–5 hijos, endpoint poco frecuente) puede ser aceptable. Mide antes de complicar.
- **Heurísticas y umbrales:** (complemento)
  - Las consultas por request deben ser O(1) respecto al tamaño de página: el mismo número con la página de 1 y con la de 50.
  - Batch size alineado con el tamaño de página típico (25–100).
  - Una colección por consulta.
  - To-one siempre `LAZY` explícito (`@ManyToOne(fetch = FetchType.LAZY)`), y la carga se decide por caso de uso. Es la recomendación de Hibernate.
- **Anti-patrones / señales de alerta:**
  - Cambiar a EAGER "para arreglarlo".
  - Open Session in View activado y entidades serializadas por Jackson.
  - `@Transactional` para tapar una `LazyInitializationException` sin definir el plan de carga.
  - `findAll()` + `stream().map(getters)`.
  - `@EntityGraph` con colección + `Pageable`.
  - Dos `join fetch` de `List` en la misma consulta.
  - `coleccion.size()` para contar.
  - Batch size gigante sin mirar el `IN` generado (Oracle limita a 1 000 elementos) (complemento).
  - Validar con 2 filas de prueba.
- **Preguntas de revisión arquitectónica:**
  1. ¿Cuántas consultas genera este endpoint con página de 1 y con página de 50? ¿Hay un test que lo fije?
  2. ¿Qué relaciones son EAGER, incluidas las to-one por defecto, y por qué?
  3. ¿`spring.jpa.open-in-view` está desactivado? ¿Se serializan entidades?
  4. ¿La paginación se aplica en SQL, o aparece `HHH90003004` en los logs?
  5. ¿Esta lectura debería ser una proyección DTO?
  6. ¿Qué muestra el APM: número de spans de BD por traza y su tendencia tras cada deploy?
- **Caso real / referencias (complemento):**
  - Hibernate ORM User Guide, capítulo Fetching y ajustes `hibernate.default_batch_fetch_size`, `hibernate.generate_statistics` y `hibernate.query.fail_on_pagination_over_collection_fetch`: https://docs.hibernate.org/orm/6.6/userguide/html_single/Hibernate_User_Guide.html
  - Especificación Jakarta Persistence (valores por defecto de `fetch`).
  - Spring Data JPA Reference (`@EntityGraph`, proyecciones).
  - Vlad Mihalcea, *High-Performance Java Persistence* y "The best way to fix the Hibernate HHH000104 warning".
  - EF Core, "Single vs. Split Queries".
  - Prisma, "Query optimization".
  - Casos GitLab y Stack Overflow: ver [06].
- **Precisión técnica:**
  - **Por qué EAGER no es la solución** (temario; detalle complemento):
    - EAGER es global y estático: lo pagan todos los casos de uso, también los que no usan la relación, y no se puede desactivar por consulta.
    - En JPQL, Criteria y consultas derivadas, las to-one EAGER que no están en `join fetch` se cargan con SELECT secundarios, así que el N+1 sigue ahí.
    - En colecciones arrastra grafos enteros y cartesianos.
    - Hibernate recomienda marcar todo LAZY y decidir la carga ansiosa por consulta.
  - N cuenta entidades relacionadas distintas, no filas: el contexto de persistencia (identity map) carga una sola vez cada cliente repetido (complemento).
  - Hibernate 6 elimina los duplicados de la raíz en los fetch joins sin necesidad de `distinct` (complemento).
  - El lado inverso de un `@OneToOne` (`mappedBy`) no puede ser lazy sin bytecode enhancement: Hibernate debe consultar para saber si es null, así que genera N+1 aunque declares LAZY. Usa `@MapsId` o el lado propietario (complemento).
  - Desde Hibernate 6, `hibernate.batch_fetch_style` está deprecado y el estilo se elige automáticamente (complemento).
  - **Equivalentes en otros ORMs** (complemento):
    - EF Core: el lazy loading es opcional (proxies o `ILazyLoader`). Herramientas: `Include`/`ThenInclude`, `AsSplitQuery()` para varias colecciones (si no se configura, avisa con `MultipleCollectionIncludeWarning`), y `Select` + `AsNoTracking()` para leer.
    - Prisma: no tiene lazy loading; su N+1 son `await` dentro de bucles. Usa `include`/`select` o `where: { id: { in } }`. Agrupa automáticamente los `findUnique` equivalentes del mismo tick (útil en resolvers GraphQL).
    - TypeORM: relaciones lazy como `Promise`; `relations` o `leftJoinAndSelect`.
    - En GraphQL: un DataLoader por request.
