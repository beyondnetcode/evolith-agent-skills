# [06] Tu ORM no es lento, lo estás usando mal

> Fuente: TheDebugDuck — https://youtu.be/sOsCAIbhxOY · notas parafraseadas; «(complemento)» = conocimiento añadido o corrección.

- **Síntoma en producción:**
  - Tras desplegar el email de "pedido enviado", el worker se retrasa, la cola crece y los correos no llegan; el worker se queda sin memoria. Si comparte el pool con la API, fallan hasta los logins.
  - En local va perfecto (un cliente, un envío).
  - Los logs SQL muestran decenas o miles de SELECT por unidad de trabajo (el video usa 40 SELECT para un email como umbral de alarma).
- **Causa raíz (mecanismo):**
  - El ORM no traduce la intención a SQL mínimo. Abre una sesión/unidad de trabajo en RAM (Hibernate *persistence context*, EF *Change Tracker*) que dura el request o el job. Cada fila se materializa como entidad completa (todas las columnas), se registra en un *identity map* por ID y se guarda un snapshot para el *dirty checking* al hacer flush.
  - Carga ansiosa anidada (`include` customer → orders → items → product → reviews/images): sigue el grafo del modelo, no la necesidad del caso de uso → arrastra todo el historial del cliente.
  - JOIN de colecciones anidadas o hermanas = producto cartesiano: 1 pedido × 10 ítems × 5 imágenes = 50 filas con columnas repetidas (y BLOBs, si los hay) que el ORM debe deduplicar e hidratar.
  - Lazy loading: tocar `shipment.items` dentro de un bucle lanza un SELECT por iteración (N+1). 50 envíos = 1 + 50 consultas (+50 más si se toca `product`); cada una ocupa una conexión del pool y suma RTT.
  - Reutilizar la consulta "de escritura" (agregado completo) para una lectura de plantilla.
- **Metáfora visual del video:** empresa de mudanzas: pides la lámpara y, como el contrato dice "trasladamos el hogar", embalan sofá, armario y cocina; el inventario son las relaciones que tú definiste en el modelo.
- **Estrategias / solución:**
  1. Activar el log SQL en local/tests con 2–3 registros y contar queries. Un `SELECT … WHERE shipment_id = ?` repetido con distintos IDs = N+1.
  2. Lecturas: proyección explícita a DTO sin tracking. EF Core `AsNoTracking()` + `Select`; Prisma `select` en lugar de `include`; Hibernate proyección a DTO o consulta nativa.
  3. SQL nativo sólo parametrizado, tipado, mapeado a DTO de solo lectura y aislado en la capa de datos (el camino de Stack Overflow → Dapper).
  4. Escrituras complejas (crear pedido + líneas + cobro): ORM con unidad de trabajo, dirty checking y transacción; rollback limpio sin huérfanos si falla el cobro.
  5. (complemento) Evitar cartesianos: EF Core `AsSplitQuery()`; Hibernate `@BatchSize`/`default_batch_fetch_size` o un único `JOIN FETCH` de colección; Django `prefetch_related` vs `select_related`; Rails `preload`; Prisma `relationLoadStrategy`.
  6. (complemento) Test de regresión del nº de queries por caso de uso (assert query count) y detectores (Bullet, Hibernate Statistics, interceptores de EF).
  7. (complemento) Pools separados (bulkhead) para workers y API.
  ```text
  // Lectura para plantilla: 1–2 queries, sin tracking, sólo lo que usa el template
  dto = db.shipments.noTracking()
          .where(id == :shipmentId)
          .select(s -> { name: s.customer.name,
                         tracking: s.trackingUrl,
                         products: s.items.map(i -> i.product.name) })
          .single()

  // Bucle sin N+1: cargar hijos por lote
  shipments = SELECT ... FROM shipments WHERE status = 'pending' LIMIT 50
  items     = SELECT ... FROM shipment_items WHERE shipment_id IN (:ids)   -- 1 query, no 50
  ```
- **Trade-offs y cuándo NO aplicar:**
  - Proyecciones: más DTOs, menos reutilización del "repositorio único".
  - SQL nativo: mantenimiento manual, acoplamiento al esquema, riesgo de inyección si se hace mal.
  - Split queries: más round trips y posible inconsistencia entre consultas sin snapshot común.
  - Eager global: cartesianos.
  - No sustituir el ORM en escrituras de agregados: se perdería la consistencia de la unidad de trabajo. Frase del video: "el ORM se queda, pero el criterio lo pones tú".
- **Heurísticas y umbrales:**
  - Criterio central: ¿el bloque modifica un agregado complejo (ORM con sesión y transacción) o sólo lee para un correo, listado o reporte (proyección o SQL parametrizado)?
  - El nº de queries por unidad de trabajo debe ser O(1), no O(N).
  - 1 × 10 × 5 = 50 filas: la explosión cartesiana es multiplicativa por nivel.
  - Casos: GitLab pasó de > 20 000 queries por petición a < 100; Stack Overflow, de 200 ms a 50 ms.
- **Anti-patrones / señales de alerta:**
  - `include`/`JOIN FETCH` de ≥ 2 niveles o de colecciones hermanas en lecturas.
  - Acceso a navegaciones dentro de `map`/`for`/`forEach`.
  - Un único método `findOrderFull()` reutilizado para todo.
  - Tracking activo en lecturas masivas de workers.
  - Worker y API compartiendo pool.
  - SQL concatenado con strings.
  - PRs aprobados sin mirar el SQL generado; "usar include se ve más senior".
  - Código de IA con includes gigantes probado con un pedido de un solo ítem.
- **Preguntas de revisión arquitectónica:**
  1. ¿Qué SQL exacto genera este acceso y cuántas queries por unidad de trabajo, con datos de producción?
  2. ¿Es lectura o escritura de agregado? ¿Hace falta tracking?
  3. ¿El tamaño del grafo crece con la antigüedad del cliente?
  4. ¿Hay colecciones en JOIN que produzcan cartesiano?
  5. ¿El worker comparte pool o recursos con la API?
  6. Si hay SQL nativo: ¿parametrizado, tipado, aislado y probado?
- **Caso real / empresa citada:**
  - GitLab (2021): un endpoint de runners con > 20 000 queries por petición por Active Record; eliminaron la hidratación innecesaria → < 100.
  - Stack Overflow (2011): de LINQ to SQL a SQL manual parametrizado en las consultas calientes; nace Dapper; página de preguntas de 200 ms a 50 ms; el ORM se mantuvo para las transacciones complejas.
- **Precisión técnica:**
  - "Todos los ORMs tienen la misma sesión": impreciso. Hibernate/JPA, EF Core, NHibernate y SQLAlchemy sí tienen unidad de trabajo + identity map + dirty checking. Prisma NO (query builder sin change tracking ni identity map); Django no tiene identity map; TypeORM tampoco por defecto. En Prisma el N+1 no viene de un lazy loading implícito (no existe), sino de `await` dentro de bucles.
  - (complemento) Lazy loading: en EF Core es opcional (proxies); en JPA `@ManyToOne`/`@OneToOne` son EAGER por defecto y `@OneToMany` LAZY, fuente clásica de N+1 inesperados.
  - "Si no tocaste nada crea SQL de más" (ASR/confuso): sin cambios, el dirty checking no emite UPDATE. El coste es CPU y memoria por snapshots y comparaciones en cada flush (Hibernate hace auto-flush antes de las queries).
  - Las cifras de GitLab y Stack Overflow son las del video y no están verificadas aquí (Dapper sí nació en Stack Overflow en 2011).
