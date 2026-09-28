# [26] ¿Por qué separar lecturas y escrituras? | CQRS explicado fácil

> Fuente: TheDebugDuck — https://youtu.be/srn3gx_Ot0k · notas parafraseadas; «(complemento)» = conocimiento añadido o corrección.

- **Síntoma en producción:** GET rápido mientras POST hace timeout en el mismo pico; ambos compiten por la misma base, esquema e índices. Tickets de "datos raros", exportes que no cuadran, soporte y finanzas con cifras distintas. Escenario A: la vista muestra "reembolsado"/KPI inflado mientras el write model dice "cobrado" o la proyección aplicó un evento dos veces. Escenario B: el command terminó, pero la vista no lo refleja (proyector caído, lag de 10 min).
- **Causa raíz (mecanismo):** leer y escribir son problemas distintos (ratio 1000:1); un modelo único obliga a índices y esquema de compromiso, y las consultas pesadas compiten con las transacciones. Al separar, aparece el **lag de proyección** (command confirmado → evento → proyector → read model); si no se nombra, se confunde con "caché raro". En *replay*, el backlog presiona la BD de lectura y un proyector no idempotente duplica conteos.
- **Metáfora visual del video:** cocina (write model, reglas estrictas) y vitrina (read models), con el mesero como proyector entre ambas.
- **Estrategias / solución:**
  1. Lado command: mutaciones, agregados, invariantes, una sola puerta para cambiar estado; emite eventos de dominio. Sin consultas pesadas.
  2. Lado query: vistas desnormalizadas por pregunta (dashboard, búsqueda, reportes, pantalla de soporte); no mutan la verdad.
  3. Proyector: consume eventos, actualiza read stores; Outbox/colas en el camino.
  4. **Trazar el Command ID de punta a punta:** handler → offset del proyector → versión del read model; permite distinguir proyección lenta, evento duplicado o réplica vieja.
  5. Operar: SLA y alerta de lag del proyector, read models versionados, as-of en reportes, UX "actualizando", pruebas de replay.
  ```
  proyectar(evento):                       # proyector idempotente (complemento: detalle)
    tx:
      v = read_model.ultima_version(evento.aggregate_id)
      si evento.version <= v: return      # duplicado o replay → no-op
      aplicar(evento); read_model.set_version(evento.aggregate_id, evento.version)
      guardar_offset(evento.offset)        # en la misma transacción
  ```
- **Trade-offs y cuándo NO aplicar:** sube la complejidad (dos modelos, dos esquemas, dos modos de fallo, consistencia eventual). Aplicar en un bounded context con reglas claras, no en todo el monolito por moda. No aplicar en CRUD pequeño; si el equipo no puede operar dos modelos, primero fortalecer observabilidad en un monolito sano.
- **Heurísticas y umbrales:** lecturas ≫ escrituras (ej. 1000:1); checklist de entrada: lecturas dominan, equipo capaz de operar dos modelos, read models versionados, SLA de lag, proyector idempotente, UX admite desfase — "si la mitad es no", no separar todavía. Pipeline típico de ejemplo: 30 s.
- **Anti-patrones / señales de alerta:** CQRS en CRUD de cinco usuarios; dos bases sin estrategia; reportes leyendo el write store bajo carga; cero métricas de lag; proyecciones sin idempotencia; read model usado como write model "con otro nombre"; postmortems que siguen hablando de "una sola tabla para todo".
- **Preguntas de revisión arquitectónica:**
  1. ¿Qué evidencia (ratio, contención, forma de consultas) justifica separar, y se agotaron índices, réplicas y caché?
  2. ¿Cuál es el SLA de lag por read model y cómo se alerta?
  3. ¿El proyector es idempotente y soporta replay completo sin duplicar?
  4. ¿Se puede correlacionar un command ID hasta la versión del read model?
  5. ¿Qué consumidores exigen read-your-writes y cómo se les sirve?
  6. ¿Cómo se reconstruye un read model corrupto y cuánto tarda?
- **Caso real / empresa citada:** LinkedIn (Activity Feed con write path acotado y read path optimizado), Microsoft Learn (advertencia de complejidad), guías de AWS de microservicios (read models), banca/retail con OLTP + reporting store. Lecturas: *Microservices Patterns* (Richardson), *Implementing Domain-Driven Design* (Vaughn Vernon).
- **Precisión técnica:**
  - CQRS **no exige** bases separadas, eventos ni consistencia eventual: puede ser el mismo almacén con modelos distintos o vistas actualizadas en la misma transacción (fuertemente consistente). Réplica de lectura ≠ CQRS (complemento).
  - Una vista "adelantada" respecto del write model suele ser síntoma de **dual write** (evento publicado y transacción revertida) o de aplicación duplicada; se corrige con Outbox + proyector idempotente (complemento).
  - La razón 1000:1 por sí sola no justifica CQRS; primero índices, réplicas y caché (complemento).
