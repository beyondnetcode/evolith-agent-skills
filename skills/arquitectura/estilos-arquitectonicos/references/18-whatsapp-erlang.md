# [18] Cómo 50 ingenieros soportaron 900 millones de usuarios (WhatsApp y Erlang)

> Fuente: TheDebugDuck — https://youtu.be/RpKzma-EDG0 · notas parafraseadas; «(complemento)» = conocimiento añadido o corrección.

- **Síntoma en producción:** en Año Nuevo millones envían mensajes al mismo tiempo y aparece "mensaje no enviado"/"enviando" colgado: el pico sincronizado satura la **entrada** (aceptar conexión e ingresar el mensaje), no el interior del sistema.
- **Causa raíz (mecanismo):** el modelo típico de servidor (hilos que comparten memoria y datos protegidos con locks) degrada bajo alta concurrencia: contención, race conditions, deadlocks, bugs que solo aparecen bajo carga, CPU consumida en coordinación. Además, un hilo del SO por conexión es caro en memoria y kernel. Escalar vertical tiene techo de coste.
- **Metáfora visual del video:** concierto con una sola puerta (el cuello de botella está en la fila de entrada); cartero gigante con candado en el mostrador vs ejército de mini-mensajeros, cada uno con su buzón, comunicándose por sobres.
- **Estrategias / solución:** **modelo de actores en Erlang/BEAM + OTP**:
  - Procesos ligeros (baratísimos frente a hilos del SO), uno por conexión/sesión; memoria propia, sin estado compartido; comunicación por mensajes asíncronos al buzón.
  - **Let it crash**: no intentar recuperar un proceso en estado corrupto; dejarlo morir limpiamente, el fallo queda aislado.
  - **Árbol de supervisión**: supervisores reinician workers caídos en milisegundos (solo ese o un grupo, según estrategia).
    ```
    Supervisor raíz
     ├─ Sup. conexiones (one_for_one) ─ proc. conexión A | proc. conexión B | ...
     └─ Sup. enrutamiento/sesiones  (rest_for_one / one_for_all según dependencia)
    ```
  - Escalar horizontal **y** maximizar cada servidor (tuning del SO, FreeBSD): ~2 millones de conexiones TCP por máquina.
- **Trade-offs y cuándo NO aplicar:** encaja con muchas conexiones simultáneas de larga vida, mucho paralelismo pequeño y tolerancia a fallos (mensajería, presencia, notificaciones, telecom). Para cómputo intensivo por CPU o crunching numérico, BEAM no es el mejor runtime (complemento). Coste: ecosistema y talento más escasos. (complemento) Buzones sin límite → riesgo de sobrecarga si un proceso recibe más de lo que consume: se requiere backpressure/limitación de carga; llamadas síncronas cíclicas entre actores pueden bloquearse. Equivalentes en otros stacks: Akka (JVM), Orleans (.NET), Elixir/Phoenix, goroutines+channels (Go, CSP).
- **Heurísticas y umbrales:** ~50 ingenieros para ~900 M usuarios; ~2 M conexiones TCP activas por servidor; tres lecciones: procesos aislados sin memoria compartida, mensajes en lugar de locks, supervisores que levantan lo caído. Diagnóstico: ¿tu sistema es un "cartero gigante" o una "oficina con millones de mensajeros"?
- **Anti-patrones / señales de alerta:**
  - Un hilo del SO por conexión persistente a gran escala.
  - Estado mutable compartido protegido con locks en el camino caliente.
  - `try/catch` defensivo que deja procesos vivos en estado inconsistente.
  - Respuesta por defecto a la saturación = "máquina más grande".
  - Sin estrategia de reinicio/supervisión ni aislamiento de fallos por sesión.
  - Picos sincronizados previsibles (Año Nuevo, finales) sin prueba de carga ni control de admisión.
- **Preguntas de revisión arquitectónica:**
  1. ¿Cuántas conexiones concurrentes de larga vida se esperan y cuánto cuesta cada una (memoria, hilo)?
  2. ¿Qué estado se comparte entre unidades de trabajo y cómo se evita la contención?
  3. ¿Cuál es la unidad de fallo y quién la reinicia?
  4. ¿Dónde está el cuello de botella en el pico: admisión, cola o procesamiento?
  5. ¿Hay backpressure cuando un consumidor no da abasto?
  6. ¿Se ha exprimido el rendimiento por nodo antes de añadir nodos?
- **Caso real / empresa citada:** WhatsApp (Erlang/BEAM, OTP, FreeBSD); Ericsson (origen de Erlang en conmutadores telefónicos).
- **Precisión técnica:**
  - Concurrencia ≠ paralelismo: millones de procesos avanzan **concurrentemente**, pero en paralelo solo tantos como schedulers/núcleos (BEAM usa un scheduler por núcleo con preempción por reducciones) (complemento).
  - "Sin datos compartidos" es casi cierto: los mensajes se copian, pero los binarios grandes (>64 bytes) se comparten por referencia y ETS permite estado compartido (complemento).
  - Los actores eliminan races de memoria, pero no races de orden de mensajes ni deadlocks por llamadas síncronas mutuas (complemento).
  - Cifras según fuente/año: en 2014 (compra por Facebook) eran ~32 ingenieros y ~450 M usuarios; la cifra de 50/900 M corresponde a 2015. Los ~2 M de conexiones/servidor proceden del blog de WhatsApp de 2012 (complemento). WhatsApp partió de ejabberd (XMPP) y usaba Mnesia (complemento).
  - ASR: "BINVM" = BEAM VM; "Earline/airlang" = Erlang; "Rong time" = runtime; "books/bus" = bugs.
