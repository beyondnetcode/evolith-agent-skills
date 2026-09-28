# [25] Por qué hacer un "UPDATE" en tu base de datos es un peligro

> Fuente: TheDebugDuck — https://youtu.be/7nVmbbiszqY · notas parafraseadas; «(complemento)» = conocimiento añadido o corrección.

- **Síntoma en producción:**
  - Una disputa por un cargo no reconocido, una auditoría o el regulador piden la secuencia de hechos, y la BD sólo tiene el estado final (`balance = 42`).
  - Números que no cuadran entre sistemas, "dos versiones de la verdad", post-mortems sin trazabilidad, auditoría bloqueada. Todo parece correcto hasta que alguien pregunta por el pasado.
  - En event sourcing mal implementado: replays que duplican cobros, emails y métricas.
- **Causa raíz (mecanismo):**
  - La persistencia basada en estado (CRUD) sobrescribe: cada UPDATE destruye el valor previo y el porqué; sólo sobrevive la foto.
  - Event sourcing lo invierte: la fuente de verdad es un log append-only de hechos inmutables por stream (agregado); el estado actual es una función derivada (fold) de los eventos; las lecturas se sirven desde proyecciones.
  - Los fallos típicos rompen alguno de esos invariantes: mutar el log, mezclar estado mutable con el log, reprocesar sin idempotencia o cambiar el esquema de los eventos sin plan.
- **Metáfora visual del video:** la app del banco muestra el saldo (foto); el extracto en PDF es la película, línea a línea. "Un extracto bancario oficial no se arregla con corrector líquido."
- **Estrategias / solución:**
  1. Event store append-only: nunca UPDATE/DELETE; los errores se corrigen con un evento compensatorio (abono/reverso).
  2. Eventos = hechos de negocio en pasado (`OrderPlaced`, `PaymentCaptured`, `InventoryReserved`), no setters (`SetBalance(42)`).
  3. Un stream por agregado (`order-123`, `customer-9`), ordenado por versión.
  4. Reconstrucción por replay con la misma lógica que en vivo, desde el inicio o desde un snapshot.
  5. Snapshots en la posición N: estado derivado cacheado; el log sigue siendo la verdad.
  6. Proyecciones/read models por necesidad (dashboard, búsqueda, reportes); con CQRS, los eventos son el registro maestro.
  7. Versionado de eventos (v1 → v2) con upcasters, planificado como una migración de datos; probar replays completos en staging.
  8. Handlers idempotentes (toleran ver el mismo evento dos veces); rebuilds de proyecciones controlados.
  9. Trazabilidad: `event_id` + posición en el stream + versión del read model (+ comando origen).
  10. GDPR: políticas y cifrado, no borrar líneas a escondidas. (complemento) Crypto-shredding: cifrar la PII con una clave por sujeto y destruir la clave.
  ```sql
  CREATE TABLE events (
    global_position bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    stream_id       text        NOT NULL,       -- 'order-123'
    stream_version  int         NOT NULL,
    event_id        uuid        NOT NULL UNIQUE,
    event_type      text        NOT NULL,       -- 'PaymentCaptured'
    schema_version  int         NOT NULL,       -- para upcasting
    payload         jsonb       NOT NULL,       -- pequeño: referencias, no blobs
    metadata        jsonb       NOT NULL,       -- correlation_id, causation_id, actor
    occurred_at     timestamptz NOT NULL,
    UNIQUE (stream_id, stream_version)          -- (complemento) concurrencia optimista
  );
  REVOKE UPDATE, DELETE ON events FROM app_role;  -- append-only forzado por permisos
  ```
  ```text
  // Rehidratar un agregado
  (state, v) = snapshot(stream) ?? (inicial, 0)
  for e in events(stream) where stream_version > v order by stream_version:
      state = apply(state, upcast(e))

  // Proyección idempotente (misma transacción que el read model)
  on event e:
      if e.global_position <= checkpoint(proyeccion): return
      actualizar read model; checkpoint(proyeccion) = e.global_position
  // En rebuild: desactivar side effects (emails, cobros) o deduplicar por event_id
  ```
- **Trade-offs y cuándo NO aplicar:**
  - Coste: más complejidad (proyecciones, consistencia eventual en lecturas, versionado, rebuilds, crecimiento del log); las consultas ad-hoc sobre el estado actual necesitan proyecciones; GDPR más difícil; curva de aprendizaje.
  - Test del video antes de adoptarlo: ¿me pedirán movimiento a movimiento? ¿hay disputas o regulación? ¿quién leerá esto (sólo yo, contabilidad, alertas)? ¿necesito resúmenes periódicos sin perder detalle? ¿cambiará el formato de las líneas? Si la mitad es "no", basta con CRUD y buenos locks.
  - (complemento) Alternativas más baratas para auditoría: tablas de historial por trigger, tablas temporales system-versioned (SQL Server, MariaDB), ledger tables (SQL Server 2022), CDC (Debezium) hacia un log, o un ledger de doble entrada sólo en el subdominio monetario.
- **Heurísticas y umbrales:**
  - Un stream por agregado; el snapshot es un atajo, no la verdad; replay primero en staging; eventos pequeños (referencias en vez de adjuntos).
  - (complemento) Snapshot cada ~100–1 000 eventos, o cuando la rehidratación supere el presupuesto de latencia.
  - (complemento) Concurrencia optimista con `expected_version` al hacer append.
- **Anti-patrones / señales de alerta:**
  - "CRUD disfrazado": un log de fachada con UPDATE por debajo (peor que un CRUD honesto).
  - Eventos tipo setter (`BalanceSet`).
  - Blobs o adjuntos dentro de los eventos.
  - Snapshot como única verdad (tirar los eventos).
  - Replay sin idempotencia; proyecciones que disparan side effects durante un rebuild.
  - Una sola tabla/stream gigante mezclando agregados.
  - Eventos sin versión de esquema.
  - Borrar eventos para cumplir GDPR.
- **Preguntas de revisión arquitectónica:**
  1. ¿El negocio o el regulador necesitan reconstruir el estado en un instante T o demostrar el camino?
  2. ¿Qué agregados/streams hay, cuáles son sus invariantes y cómo se controla la concurrencia (expected version)?
  3. ¿Cómo se versionan los eventos y cómo se prueban los replays completos?
  4. ¿Consumidores y proyecciones son idempotentes? ¿Se desactivan los side effects en un rebuild?
  5. ¿Cómo se trata la PII y el derecho al olvido en un log inmutable?
  6. ¿Estrategia de snapshots y tiempo objetivo de rehidratación?
- **Caso real / empresa citada:** LMAX Exchange (el event log como núcleo de un trading de rendimiento extremo); Zalando (engineering blog: event sourcing con bounded contexts); guías de AWS sobre trazabilidad event-driven. Lecturas recomendadas: Vaughn Vernon, *Implementing Domain-Driven Design*; Ben Stopford, *Designing Event-Driven Systems*.
- **Precisión técnica:**
  - El título ("UPDATE es un peligro") exagera: UPDATE es correcto para la mayoría de los datos; el problema es usarlo cuando el requisito es un historial auditable.
  - Event sourcing no es la única vía para auditar (ver alternativas).
  - ASR: "eventouring / ident sourcing" = event sourcing; "Elmax" = LMAX; "Salando" = Zalando; "Von Vernon" = Vaughn Vernon; "Ben Stockford" = Ben Stopford; "OPcasters" = upcasters; "B1/B2" = v1/v2; "CRW disfrazado" = CRUD disfrazado; "offset ceridores" ≈ rebuild desde offset cero con consumidores que reprocesan todo.
  - (complemento) LMAX: el rendimiento extremo viene de la lógica en memoria en un solo hilo (Disruptor); event sourcing aporta recuperación y auditoría, no la velocidad por sí mismo.
  - (complemento) Los ledgers bancarios reales suelen ser de doble entrada con saldo materializado; event sourcing es una implementación posible, no un requisito.
  - (complemento) Las proyecciones son eventualmente consistentes: la UI puede leer datos atrasados, y read-your-writes exige una estrategia explícita.
