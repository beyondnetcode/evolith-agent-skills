# [21] Filas virtuales: la ingeniería detrás de ventas que no se caen

> Fuente: TheDebugDuck — https://youtu.be/dPBVU-JnYzs · notas parafraseadas; «(complemento)» = conocimiento añadido o corrección.

- **Síntoma en producción:**
  - En una preventa masiva, todos hacen clic a la vez: el usuario ve "el sitio está lento", no llega al checkout o recibe un error 500.
  - Por dentro: login validando sesiones, inventario con contención por asientos, pagos abriendo conexiones, y esperas, reintentos y F5 que amplifican la carga.
- **Causa raíz (mecanismo):**
  - Se deja pasar a la multitud hasta la parte más cara y frágil (checkout, pagos, inventario) sin admission control.
  - La capacidad real es finita (p. ej. 500 usuarios/min frente a 50.000 en el segundo cero).
  - Los reintentos y refrescos multiplican la carga, y los bots ocupan lugares.
  - Decidir tarde (en el checkout) significa haber consumido ya el recurso caro.
- **Metáfora visual del video:** la puerta del estadio decide si entras ya, esperas con tu lugar o no pasas (abuso). La fila transforma un impacto súbito en un flujo dosificado.
- **Estrategias / solución:**
  1. **Medir la capacidad real** del flujo caro (pagos, BD, inventario) y fijar la tasa de admisión.
  2. **Waiting room antes del backend**, idealmente en el edge (Cloudflare Waiting Room, CloudFront + funciones de edge): quien espera consume una página liviana, no sesiones del clúster.
  3. **Justicia explícita:** FIFO con la venta ya abierta; sala previa con posiciones asignadas aleatoriamente a la hora de apertura, para que no gane el de mejor red o el que usa scripts.
  4. **Pase firmado y temporal** (token o cookie con firma y expiración, con alcance a una zona): el servidor confía en una prueba verificable, no en la pestaña. Copiar la URL, refrescar o falsificar no sirve.
  5. **Liberar en tandas con back pressure:** admitir un grupo, observar latencia y errores del checkout, y subir o bajar el ritmo.
  6. **Reserva temporal de inventario** (hold con TTL de minutos) para no prometer stock inexistente.
  7. **Anti-bots antes de ordenar:** señales de comportamiento, límites por cuenta o dispositivo, retos humanos cuando haga falta.
  8. **UX honesta:** posición y estimación visibles y estables.
  9. Se compone con rate limiting (ritmo), back pressure, circuit breaker hacia proveedores de pago enfermos e idempotencia en pagos y órdenes.
  ```text
  edge(req):
    if verify_hmac(req.cookie.pass) and pass.exp > now and pass.scope == "checkout": forward(origin)
    pos = queue.get_or_enqueue(visitor_id, key = sale_open ? now : random())   # FIFO o sorteo en sala previa
    return waiting_page(pos, eta)                                              # página estática/cacheable

  admitter (cada 10 s):
    rate = controller(checkout_p95, checkout_error_rate)   # sube si sano, baja si enfermo
    for v in queue.pop(rate * 10s):
      issue_pass(v, exp = now + 10m, sig = HMAC(k, v | exp | scope))

  reserve(seat, user):  SET seat:{id} {user} NX EX 600      # hold temporal; libera si no paga
  ```
- **Trade-offs y cuándo NO aplicar:**
  - Añade espera percibida y complejidad (tokens, colas, sorteos).
  - Una tasa demasiado conservadora desperdicia capacidad y alarga la venta.
  - Los pases se pueden compartir si no se atan a sesión o dispositivo.
  - Las reservas con TTL inmovilizan stock (un TTL corto frustra, uno largo bloquea).
  - Depender del edge de un proveedor genera lock-in.
  - No aplica a tráfico sostenido sin picos sincronizados ni escasez: ahí bastan autoscaling y rate limiting.
- **Heurísticas y umbrales:**
  - Ejemplo de capacidad: 500 usuarios/min frente a 50.000 simultáneos.
  - Pase válido por "x minutos" y reserva de asiento por "unos minutos".
  - (complemento) La reserva debe cubrir el p99 del tiempo de pago, típicamente 5–10 min.
  - Ajustar el ritmo según latencia y errores del checkout.
  - Cita: "La fila convierte un golpe en un chorro."
- **Anti-patrones / señales de alerta:**
  - La decisión de admisión se toma dentro del checkout o del origen; la respuesta al pico es "más servidores de checkout".
  - Fila sin información (parece una pantalla congelada); posición que cambia sin explicación.
  - Refresh infinito que premia al más agresivo; pase sin firma o sin expiración.
  - Bots dentro de la fila; prometer stock cuando ya casi no queda.
- **Preguntas de revisión arquitectónica:**
  1. ¿Cuál es la capacidad medida del flujo caro (usuarios o transacciones por minuto) y cómo se obtuvo?
  2. ¿Dónde se decide la admisión (edge u origen) y qué recursos consume quien espera?
  3. ¿Cómo se firma, valida, expira y ata el pase a la sesión o dispositivo?
  4. ¿Qué política de justicia se aplica (FIFO, sorteo) y cómo se comunica?
  5. ¿Qué señales ajustan la tasa de admisión y quién o qué la controla?
  6. ¿Cómo se evitan la sobreventa (reserva con TTL) y los cobros duplicados (idempotencia)?
- **Caso real / empresa citada:** Ticketmaster (Smart Queue), Queue-it, Cloudflare Waiting Room (cookie de cola, métricas de espera y paso), CrowdHandler, Nike SNKRS (bots en lanzamientos limitados).
- **Precisión técnica:**
  - "Back pressure" se usa en sentido amplio. (complemento) Estrictamente, la fila implementa un control de admisión en lazo cerrado cuya señal viene del consumidor (el checkout). Un controlador tipo AIMD (subida aditiva, bajada multiplicativa) es una forma robusta de ajustar la tasa.
  - (complemento) La fila no sustituye la protección en el origen: si alguien la evita (pase robado, endpoint expuesto), el checkout debe validar el pase y aplicar rate limiting propio.
  - (complemento) Tener una fila no garantiza el éxito: la venta del Eras Tour de 2022 en Ticketmaster falló pese a la preinscripción (Verified Fan), por una demanda y un tráfico de bots muy por encima de lo planificado. La capacidad declarada debe ser honesta.
