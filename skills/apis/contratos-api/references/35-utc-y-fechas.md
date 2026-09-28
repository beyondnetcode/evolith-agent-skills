# [35] ¿Por qué TODO está en UTC? (explicado fácil)

> Fuente: TheDebugDuck — https://youtu.be/YHHhS37JABg · notas parafraseadas; «(complemento)» = conocimiento añadido o corrección.
> Estado: elaborado a partir del título y el temario público del video; la transcripción no estuvo disponible (bloqueo de YouTube, 2026-09-28). Lo que no figura en el temario es «(complemento)». Pendiente de contrastar con la transcripción.

- **Síntoma en producción:** guardar horas locales rompe calendarios, pagos y vuelos; los problemas aparecen con el horario de verano (DST). Variantes concretas (complemento): la reunión aparece una hora antes tras el cambio de horario; la fecha de nacimiento o de vencimiento se muestra un día antes a usuarios en América (medianoche UTC = día anterior en UTC−5); un cobro recurrente agendado a las 02:30 se ejecuta dos veces o ninguna la noche del cambio; el reporte "del día" no cuadra entre servidores en zonas distintas; tokens que expiran al instante o nunca porque un lado usa segundos y el otro milisegundos; eventos de dos regiones mal ordenados al mezclar horas locales.
- **Causa raíz (mecanismo):** un solo tipo "fecha" se usa para tres conceptos distintos (complemento):
  1. **Instante:** un punto único en la línea de tiempo (pago realizado, log, creación). No depende de la zona → UTC.
  2. **Fecha u hora civil:** lo que muestra un calendario de pared (cumpleaños, vencimiento de factura, feriado, "abrimos a las 09:00"). No es un instante hasta combinarla con una zona.
  3. **Hora local + zona:** intención humana futura ("reunión el 15-nov a las 09:00 en Vancouver"). El instante resultante depende de reglas de zona que **pueden cambiar** entre hoy y esa fecha.
  Además: un **offset** (`-05:00`) es el desplazamiento en un momento dado; una **zona** (`America/Lima`) es un historial de reglas, pasadas y futuras. Y `DateTime.Now`/`LocalDateTime.now()` hacen que el valor guardado dependa de dónde corre el servidor. UTC funciona para apps globales porque es una referencia única, sin DST, que ordena los instantes sin ambigüedad.
- **Metáfora visual (complemento; propuesta propia, no es la del video):** **la torre de control y la agenda del pasajero**. La torre registra cada despegue en hora Zulu (UTC) para ordenar sin ambigüedad lo que ya ocurrió; el pasajero reserva "el vuelo de las 09:00 hora local". Si el país cambia su horario antes del viaje, la torre debe recalcular la hora Zulu a partir de la agenda local, no conservar la que calculó al reservar.
- **Estrategias / solución:**
  1. **Clasificar cada campo temporal y darle su tipo** (complemento):

     | Concepto | Ejemplo | PostgreSQL | JSON | Java / .NET / JS |
     |---|---|---|---|---|
     | Instante | `pagado_en` | `timestamptz` | `"2026-09-28T19:30:00Z"` | `Instant` / `DateTimeOffset` en UTC / `Temporal.Instant` |
     | Fecha civil | `fecha_nacimiento`, `vence_el` | `date` | `"2026-09-28"` | `LocalDate` / `DateOnly` / `Temporal.PlainDate` |
     | Evento futuro local | cita 09:00 en Vancouver | `timestamp` + `text` (zona IANA) + `timestamptz` derivado | `{"inicio_local":"2026-11-15T09:00:00","zona":"America/Vancouver"}` o RFC 9557 `2026-11-15T09:00:00-07:00[America/Vancouver]` | `LocalDateTime` + `ZoneId` / NodaTime `ZonedDateTime` / `Temporal.ZonedDateTime` |
     | Hora del día recurrente | "abre 09:00" | `time` + zona | `"09:00"` | `LocalTime` / `TimeOnly` / `Temporal.PlainTime` |
     | Duración | TTL, SLA | `interval` o entero con unidad | `"PT15M"` o `ttl_s` | `Duration` / `TimeSpan` |

  2. **Instantes: UTC de extremo a extremo, zona solo al mostrar.** Capturar en UTC, guardar en `timestamptz`, transportar en RFC 3339 con `Z` y convertir a la zona del usuario en la presentación:
     ```sql
     -- timestamptz guarda el instante normalizado a UTC; NO guarda la zona de entrada
     CREATE TABLE pagos (id uuid PRIMARY KEY, pagado_en timestamptz NOT NULL DEFAULT now());
     SET TIME ZONE 'UTC';   -- sesión de la app en UTC: literales sin offset y salida no dependen del servidor
     SELECT pagado_en AT TIME ZONE 'America/Lima' AS hora_lima FROM pagos;       -- solo para presentar
     SELECT (pagado_en AT TIME ZONE 'America/Lima')::date AS dia_contable, sum(monto)
     FROM pagos GROUP BY 1;                                                       -- "el día" en una zona explícita
     ```
  3. **Eventos futuros: guardar hora local + zona IANA; derivar el instante** (complemento):
     ```sql
     CREATE TABLE citas (
       id           uuid PRIMARY KEY,
       inicio_local timestamp   NOT NULL,   -- 2026-11-15 09:00 (intención humana)
       zona         text        NOT NULL,   -- 'America/Vancouver' (IANA; nunca '-08:00' ni 'PST')
       inicio_utc   timestamptz NOT NULL    -- derivado e indexado: inicio_local AT TIME ZONE zona
     );
     -- tras actualizar tzdata, recalcular solo lo futuro:
     UPDATE citas SET inicio_utc = inicio_local AT TIME ZONE zona WHERE inicio_utc > now();
     ```
     Con las reglas previas a tzdata 2026b, esa cita valía 17:00Z (−08); con British Columbia en −07 permanente vale 16:00Z. Quien guardó solo 17:00Z muestra la reunión a las 10:00.
  4. **DST: decidir qué pasa con horas inexistentes y repetidas.** En `America/New_York` 2026: el 8-mar las 02:00–02:59 no existen; el 1-nov las 01:00–01:59 ocurren dos veces (complemento). Política explícita: en el hueco, correr hacia adelante (lo que hacen `ZonedDateTime.of` de Java y `disambiguation: "compatible"` de Temporal); en el solape, elegir el primer offset y documentarlo. Jobs técnicos en UTC; jobs de negocio en hora local con política DST e **idempotentes por fecha de negocio** (clave `fecha_negocio`), para que una doble ejecución no cobre dos veces. "+1 día" ≠ "+24 h": un día civil dura 23 o 25 h en el cambio; en PostgreSQL `interval '1 day'` sobre `timestamptz` conserva la hora local de la sesión y `'24 hours'` no.
  5. **Timestamp UNIX con unidad explícita.** Segundos desde 1970-01-01T00:00:00Z sin contar segundos intercalares. (complemento) `Date.now()` (JS) y `System.currentTimeMillis()` (Java) dan milisegundos; `time()` POSIX, `exp`/`iat` de JWT (RFC 7519) y el header `Deprecation` usan segundos. En 2026 un epoch en segundos tiene 10 dígitos (~1,79 × 10⁹) y en ms 13; segundos leídos como ms caen en enero de 1970, y ms leídos como segundos, cerca del año 58 700. Nombra la unidad (`expira_en_epoch_s`) o usa RFC 3339 en APIs públicas. Enteros de 32 bits con signo desbordan el 2038-01-19T03:14:07Z (también el rango de `TIMESTAMP` en MySQL).
  6. **Backend y frontend:** servidor, contenedor, JVM y sesión de BD en UTC como defensa, sin que el código dependa de ello (tipos con zona siempre). El frontend recibe instantes con `Z` y los formatea con `Intl.DateTimeFormat(locale, { timeZone: zonaDelUsuario })`. (complemento) Envía al backend la zona IANA del usuario (`Intl.DateTimeFormat().resolvedOptions().timeZone`), no `getTimezoneOffset()`, que solo vale para ese instante. Para fechas civiles no uses `new Date("2026-09-28")`: se interpreta como UTC y en Lima muestra el 27.
  7. **Sistemas distribuidos:** (complemento) no ordenes eventos entre nodos por reloj de pared (desfase de ms a s; NTP puede retroceder el reloj): usa versiones, secuencias o relojes lógicos; mide duraciones con reloj monotónico (`System.nanoTime`, `performance.now`); guarda `ocurrido_en` (origen) y `recibido_en` (servidor); en headers usa tiempos relativos (`Retry-After: 120`), que no dependen de relojes sincronizados.
- **Trade-offs y cuándo NO aplicar:** "solo UTC" es correcto para instantes pasados e incorrecto para intenciones futuras y fechas civiles. Guardar local + zona exige tzdata actualizada en **cada** runtime (SO, JVM, ICU de .NET/Node, PostgreSQL) y un proceso de recálculo. Si el negocio realmente quiere decir "vence a las 23:59:59 de Lima", eso es un instante: modélalo como tal a partir de fecha + zona del contrato. Convertir a la zona del usuario en el backend solo tiene sentido en reportes o documentos con una zona de negocio explícita; en APIs con varios clientes, conviértelo en la presentación (complemento).
- **Heurísticas y umbrales** (complemento):
  - Pregunta por campo: ¿**ocurrió** (instante), **ocurrirá** según reloj local (local + zona) o es un **día de calendario** (fecha civil)?
  - Zonas siempre como ID IANA (`America/Lima`); nunca abreviaturas (`CST` puede ser EE. UU., China o Cuba) ni offsets fijos.
  - tzdata: 4 releases en 2026 (a–d). Actualiza en ≤ 1 semana si guardas eventos futuros en zonas afectadas.
  - JSON público: RFC 3339 con `Z` y precisión fija documentada (s o ms); nunca un epoch sin unidad en el nombre.
  - Pruebas con reloj inyectable (`Clock`) y zonas con DST (`America/New_York`, `America/Santiago`, `Europe/Madrid`) y sin DST (`America/Lima`), en fechas de transición, 29-feb, fin de mes y medianoche.
- **Anti-patrones / señales de alerta:** persistir `DateTime.Now`, `LocalDateTime.now()` o `new Date().toLocaleString()`; `datetime.utcnow()` (naive y deprecado); `timestamp` sin zona para instantes; guardar el offset como si fuera la zona; fecha de nacimiento como `2026-09-28T00:00:00Z`; sumar 86 400 s para "mañana a la misma hora"; cron de negocio entre 01:00 y 03:00 en zonas con DST sin política; comparar strings de fecha con offsets distintos; formatear fechas en el backend con el idioma y la zona del servidor.
- **Preguntas de revisión arquitectónica:**
  1. Para cada campo temporal: ¿instante, fecha civil o local + zona? ¿El tipo en BD, JSON y código lo refleja?
  2. ¿Qué zona usan la sesión de BD, el proceso y el contenedor? ¿El resultado cambiaría si cambiaran?
  3. ¿Los eventos futuros guardan zona IANA y existe un proceso de recálculo tras actualizar tzdata?
  4. ¿Qué pasa con un job agendado a las 02:30 la noche del cambio de horario? ¿Es idempotente por fecha de negocio?
  5. ¿Qué unidad tiene cada epoch del contrato y dónde está documentada?
  6. ¿Cómo define el negocio "el día" en reportes y cortes, y en qué zona?
  7. ¿Hay pruebas con reloj fijo y fechas de transición DST?
- **Caso real / referencias** (complemento):
  - tzdata 2026b–2026d: British Columbia (−07 permanente desde 2026-03-09), Alberta (−06, 2026-06-18), Territorios del Noroeste (−06, 2026-08-21) y Marruecos (+00 desde 2026-09-20). Cambios legales con semanas de aviso; tzdata modeló los canadienses desde 2026-11-01 por una limitación de CLDR.
  - México eliminó el horario de verano (salvo la franja fronteriza): tzdata 2022f salió el 2022-10-28 para un cambio del 2022-10-30. Paraguay quedó en −03 permanente tras el 2024-10-06 (tzdata 2025a).
  - `America/Lima` no tiene DST vigente: en Perú los bugs de DST llegan al integrarse con EE. UU., Chile o Europa.
  - Primarias: RFC 3339; RFC 9557 (IXDTF, abr-2024); ISO 8601-1:2019; IANA tz database (data.iana.org/time-zones); PostgreSQL 18, *Date/Time Types*; Python `datetime` (utcnow deprecado en 3.12); MDN `Date.parse`; TC39 Temporal (Stage 4 en mar-2026; Firefox 139, Chrome 144).
- **Precisión técnica:**
  - UTC es una escala de tiempo, no un huso con reglas; GMT es la hora civil del Reino Unido en invierno. Coinciden en offset, no son sinónimos (complemento).
  - "Guardar todo en UTC" vale para instantes, no como regla universal: una fecha civil no tiene instante y un evento futuro necesita local + zona (complemento).
  - `timestamptz` de PostgreSQL no guarda la zona: guarda el instante (8 bytes, resolución de 1 µs) y muestra en la zona de la sesión. Si necesitas la zona del usuario, guárdala en otra columna. `timestamp` sin zona **ignora en silencio** el offset del literal. PostgreSQL desaconseja `timetz` (complemento).
  - RFC 9557 redefinió `Z`: "UTC conocido, offset local desconocido" (equivale a `-00:00`); `+00:00` indica que UTC es la referencia preferida. Para enviar instantes en APIs, `Z` sigue siendo lo adecuado (complemento).
  - Unix time no cuenta segundos intercalares; la CGPM (2022) decidió ampliar la tolerancia UT1−UTC a más tardar en 2035, lo que en la práctica suspende los segundos intercalares (complemento).
  - `new Date("2026-09-28")` es UTC; `new Date("2026-09-28T00:00")` es hora local (complemento).
  - `datetime.utcnow()` devuelve un datetime naive que muchos métodos tratan como hora local; está deprecado desde Python 3.12: usa `datetime.now(timezone.utc)` (complemento).
