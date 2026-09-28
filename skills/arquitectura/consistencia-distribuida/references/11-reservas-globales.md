# [11] Dos personas, misma habitación: Arquitectura de Reservas Globales

> Fuente: TheDebugDuck — https://youtu.be/O9w-cFf21lg · notas parafraseadas; «(complemento)» = conocimiento añadido o corrección.

- **Síntoma en producción:** dos clientes reciben confirmación (correo + código) para la misma habitación y noche; se descubre al llegar al alojamiento. No hay error 500: el coste aparece en soporte, reembolsos, reubicaciones y créditos manuales. Tras una partición de red entre regiones, al reconectar aparecen reservas en conflicto para la misma noche.
- **Causa raíz (mecanismo):** carrera *check-then-act* entre nodos: dos servidores leen "libre" antes de que cualquiera persista "ocupado". Con escritura local por región (multi-master, replicación asíncrona) cada réplica dice "sí" antes de enterarse de la otra; la consistencia eventual solo garantiza convergencia *después*, y el daño ocurre dentro de la ventana de divergencia. Bajo partición, si ambas mitades siguen aceptando escrituras para no perder disponibilidad, se produce *split brain*. Serializar por red cuesta RTT (física de la fibra), por eso la tentación de escribir local.
- **Metáfora visual del video:** hotel con dos recepciones en extremos opuestos, cada una con su cuaderno, que se copian al final del día.
- **Estrategias / solución:**
  1. **Un solo nodo/BD (monolito):** consistencia fuerte vía la BD.
     ```sql
     -- Corrección por restricción (preferible como última línea de defensa)
     CREATE TABLE reserva_noche (
       habitacion_id bigint, noche date, reserva_id uuid NOT NULL,
       PRIMARY KEY (habitacion_id, noche));      -- el 2.º INSERT falla → "no disponible"
     -- (complemento) para rangos de fechas en PostgreSQL:
     -- EXCLUDE USING gist (habitacion_id WITH =, estancia WITH &&)

     -- Bloqueo pesimista
     BEGIN;
       SELECT estado FROM inventario WHERE habitacion_id=:h AND noche=:n FOR UPDATE;
       -- si 'LIBRE': UPDATE inventario SET estado='TENTATIVA', hold_hasta=now()+'10 min' ...
     COMMIT;
     ```
  2. **Varias regiones:** o serializas el acceso por red (pagando latencia) o aceptas decisiones divergentes y reparas después. Para recurso escaso global: exclusión mutua o consenso **antes** del "sí".
  3. **Candado distribuido** con tres propiedades: exclusión suficiente para el riesgo de negocio, **TTL/lease** (no bloquear para siempre si el proceso muere) y **fencing token** (un dueño atrasado/zombie no puede escribir tras perder el lease).
     ```
     Redlock (según doc. de Redis):
     t0 = now()
     votos = #nodos donde SET lock:hab42:2026-10-01 <token_aleatorio> NX PX <ttl> tuvo éxito
     validez = ttl - (now() - t0) - deriva_reloj
     si votos >= N/2+1 y validez > 0 → tengo el lock
     si no → liberar en todos los nodos, reintentar con backoff aleatorio
     Fencing (complemento): el almacenamiento rechaza escrituras con token < último token visto.
     ```
  4. **Idempotency key** (estilo Stripe): el cliente genera un UUID **una vez por intento lógico**, lo reenvía en cada reintento en un header; el servidor guarda clave + respuesta y ante repetición devuelve la respuesta guardada sin repetir el efecto.
  5. **Saga** para el flujo completo (tentativa → lock → cobro → confirmación → aviso al anfitrión) con compensaciones de negocio (liberar lock, cancelar tentativa, devolver inventario); orquestada o coreografiada.
  6. Receta final del video: lock (serializa el stock) + idempotencia (no duplica efectos) + saga (deshace a mitad de camino).
- **Trade-offs y cuándo NO aplicar:** consistencia fuerte = latencia (RTT inter-región) o rechazo de escrituras bajo partición; eventual = rapidez con riesgo de overbooking. Un lock no diseña el flujo, solo serializa la sección crítica. Redlock depende de supuestos de temporización (relojes, pausas de proceso): no usarlo si una violación de exclusión es inaceptable; preferir etcd/ZooKeeper (consenso) o la restricción de BD. No aplicar locks distribuidos si el recurso puede tener un único dueño de escritura (complemento: *single-writer* por clave/región "hogar" del inventario evita el lock global).
- **Heurísticas y umbrales:** RTT CDMX–São Paulo ≈150–170 ms ida y vuelta; confirmación local en "decenas de ms"; quórum mayoritario (el video dice 2 de 3; la doc. de Redis usa 5 maestros → 3). Pregunta de diseño obligatoria: ¿qué hace el sistema cuando no puede preguntarle al otro lado? → rechazar, encolar o aceptar y reparar.
- **Anti-patrones / señales de alerta:** `SELECT` de disponibilidad seguido de `INSERT/UPDATE` sin lock ni constraint; escrituras multi-master de inventario escaso; lock sin TTL; lock con TTL pero sin fencing; clave de idempotencia generada en el servidor o regenerada por reintento; flujo reserva+cobro+confirmación como cadena HTTP sin compensaciones; "usamos Redlock porque empresa X lo usa".
- **Preguntas de revisión arquitectónica:**
  1. ¿Dónde está el único punto de serialización para "habitación H, noche N"? ¿Hay una restricción de BD que lo garantice aunque el lock falle?
  2. Bajo partición entre regiones, ¿esta operación es CP (rechaza) o AP (acepta y reconcilia)? ¿Está escrito y aceptado por negocio el coste de cada opción?
  3. ¿El lock tiene TTL y fencing token verificado por el almacenamiento?
  4. ¿Quién genera la clave de idempotencia y cuánto tiempo se retiene?
  5. ¿Qué compensación existe para cada paso si el cobro falla o la confirmación no llega?
  6. ¿Cuál es el proceso de reparación (reubicación, crédito) cuando, pese a todo, hay doble venta?
- **Caso real / empresa citada:** Stripe (idempotency keys, documentado); Redis/antirez (Redlock); Martin Kleppmann (crítica 2016); Brewer, Gilbert y Lynch (CAP); García-Molina y Salem (Sagas). El video aclara que **no** consta que Airbnb use Redlock. (complemento) Airbnb sí publicó en 2019 "Avoiding Double Payments in a Distributed Payments System" (librería de idempotencia *Orpheus*).
- **Precisión técnica:**
  - CAP: el video define C como "los nodos que se hablan ven la misma verdad"; en la formulación de Gilbert-Lynch C es **linealizabilidad** (toda lectura ve la última escritura o devuelve error) y A exige respuesta no errónea de todo nodo no caído. (complemento) El argumento de latencia sin partición es PACELC, no CAP.
  - "El mismo UNIQUE en un DC lejano no mata la carrera": impreciso. Un único primario con UNIQUE/`FOR UPDATE` **sí** garantiza que no haya doble venta global; el coste es latencia y dependencia de disponibilidad de esa región. La carrera solo existe si cada región decide localmente.
  - "Una transacción ACID global no existe": exagerado. 2PC/XA y bases globales (p. ej. Spanner) existen; el problema es bloqueo del coordinador, latencia y falta de soporte en APIs/SaaS heterogéneos (complemento).
  - Redlock no emite tokens monótonos, por lo que por sí solo no provee fencing; etcd (revision) o ZooKeeper (zxid) sí (complemento). Distinción de Kleppmann: lock "por eficiencia" vs "por corrección".
  - Stripe retiene claves de idempotencia ~24 h y devuelve 409 ante peticiones concurrentes con la misma clave (complemento).
  - Sagas no tienen aislamiento (ACD sin I): la "tentativa" funciona como *semantic lock* (complemento).
