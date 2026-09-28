# [23] ¿Por qué tu API muestra datos distintos al refrescar? Explicando consistencia eventual

> Fuente: TheDebugDuck — https://youtu.be/v3I_C5UwpcI · notas parafraseadas; «(complemento)» = conocimiento añadido o corrección.

- **Síntoma en producción:** el correo dice "pedido enviado"; la app, al refrescar, alterna entre "preparando" y "enviado" (pedido 4821). Paneles de almacén y cliente muestran estados distintos a la vez; soporte pide capturas; finanzas confía en un KPI en verde que aún es *stale*; doble reembolso porque el usuario vio dos estados.
- **Causa raíz (mecanismo):** el *read path* va detrás del *write path*. Fuentes concretas de desfase: réplica asíncrona (WAL/binlog aún no aplicado), proyección materializada por un worker, caché de aplicación/CDN con TTL, replicación geográfica multi-región. Sin medir lag ni versionar, cada refresh es aleatorio. Consistencia eventual = si cesan las escrituras y no hay fallos, las copias convergen; hay un delta normal.
- **Metáfora visual del video:** dos vistas del mismo pedido que no coinciden con un reloj en medio (propagación → lag → convergencia).
- **Estrategias / solución:**
  1. **Medir el lag y exponerlo:** PostgreSQL `pg_stat_replication`; `ReplicaLag` en RDS; métrica de retraso propia del read model. Definir SLA (ej.: el dashboard de pedidos no va más de 30 s detrás del primario sin avisar) y alertar.
  2. Modelo mental en 4 pasos: escribir en la fuente de verdad → propagar (streaming/cola/worker) → leer de réplica/vista → converger.
  3. **Read-your-writes** tras un POST mutante: fijar la sesión al primario una ventana corta.
     ```ts
     // readRouter (reescrito)
     function dbParaLectura(sesion) {
       const reciente = sesion.ultimaEscritura && (Date.now() - sesion.ultimaEscritura) < 2000;
       return reciente ? db.primary : db.replica;
     }
     // (complemento) variante robusta: guardar el LSN de la escritura en la sesión y leer
     // de la réplica solo si pg_last_wal_replay_lsn() >= LSN; si no, ir al primario.
     ```
     Mecanismos: stickiness de sesión, cookie de enrutamiento o header interno.
  4. **Lecturas versionadas / as-of** para reportes: guardar `version`/`updated_at` y permitir `GET /pedidos/4821?asOf=10:00`; el snapshot toma la última versión ≤ asOf. No mezclar versiones en un mismo total.
     ```sql
     SELECT DISTINCT ON (pedido_id) *
     FROM pedido_versiones WHERE registrado_en <= :as_of
     ORDER BY pedido_id, version DESC;
     ```
  5. **UX honesta:** indicador "actualizando", skeleton, timestamp de última sincronización; no mostrar cifras definitivas que puedan estar *stale*.
- **Trade-offs y cuándo NO aplicar:** eventual da throughput de lectura a cambio de desfase medible; fuerte (leer del primario) es simple pero limita escalar lecturas. Enrutar al primario tras escribir aumenta carga del primario; la ventana fija de 2 s falla si el lag la supera. No usar réplicas para flujos que exigen leer lo recién escrito (pagos, saldos) sin mecanismo RYW.
- **Heurísticas y umbrales:** SLA ejemplo 30 s de lag para dashboard operativo; ventana RYW de 2 s; alerta de lag en dashboard de ops para distinguir "réplica tardía" de "caída de región"; "el usuario perdona el desfase si lo conoce".
- **Anti-patrones / señales de alerta:** prometer lectura instantánea con pipeline de 30 s; responder "refresca" como solución; ausencia de métrica de lag; lecturas de réplica inmediatamente después de un POST del mismo usuario; totales que agregan filas de distintas versiones; dashboards sin timestamp de frescura; escrituras no idempotentes ante reintentos.
- **Preguntas de revisión arquitectónica:**
  1. ¿Qué lag máximo tolera cada pantalla/consumidor y dónde está alertado?
  2. Tras una mutación, ¿cómo garantizamos read-your-writes (ventana, LSN/versión, primario)?
  3. ¿El balanceador reparte lecturas de una sesión entre réplicas con lag distinto (lecturas no monótonas)?
  4. ¿Los reportes financieros usan snapshot as-of/versión o leen "lo último" mezclado?
  5. ¿La UI comunica frescura del dato?
  6. ¿Las escrituras son idempotentes ante reintentos del cliente?
- **Caso real / empresa citada:** PostgreSQL streaming replication; AWS RDS (métrica de replication lag); DynamoDB (lectura eventual por defecto).
- **Precisión técnica:**
  - El síntoma de "alterna al refrescar" es una violación de **lecturas monótonas** (distintas réplicas con distinto lag), no solo de read-your-writes; se corrige con réplica fija por sesión o token de versión mínima (complemento).
  - "Consistencia fuerte = leer y escribir en la misma base" es simplificación: también se logra con replicación síncrona o quórums R+W>N (complemento).
  - DynamoDB: lectura fuertemente consistente es opcional (`ConsistentRead`), cuesta el doble de RCU y no existe en GSI (complemento).
  - `pg_stat_replication` se consulta en el primario (`write_lag/flush_lag/replay_lag`, PG≥10); en la réplica, `now() - pg_last_xact_replay_timestamp()` sobreestima el lag si el primario está ocioso (complemento).
