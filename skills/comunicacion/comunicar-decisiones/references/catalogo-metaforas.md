# Catálogo de metáforas (TheDebugDuck)

Cada entrada: **concepto** — metáfora del video · *qué mecanismo ilustra* · ⚠️ dónde se rompe (no estirarla más allá). Número = video de origen (ver `radar-arquitectura/references/indice-videos.md`). Las entradas marcadas «(complemento)» son analogías propias: la transcripción de esos videos no estuvo disponible.

## Datos y persistencia

- **Paginación OFFSET vs keyset [01]** — ventanilla con una pila de tickets: con OFFSET el empleado cuenta uno a uno hasta el 100 000; con keyset le enseñas tu último ticket y pide los 20 siguientes. · *coste proporcional a lo descartado vs salto por índice* · ⚠️ un índice cubriente abarata el conteo; la metáfora exagera la constante, no la complejidad.
- **UUIDv4 vs secuencial vs UUIDv7 [03]** — taquillas de un centro de paquetes: la siguiente puerta libre al final del pasillo (serial), un código aleatorio que obliga a buscar huecos por todo el edificio (v4), un código inadivinable cuyas puertas del día se llenan en orden (v7). · *localidad de inserción en un B-tree* · ⚠️ en bases distribuidas por rangos el "pasillo único" es justamente el cuello de botella.
- **ORM que trae de más [06]** — empresa de mudanzas: pides la lámpara y, como el contrato dice "trasladamos el hogar", embalan toda la casa. · *eager loading / includes definidos en el modelo* · ⚠️ no todos los ORMs tienen "contrato de sesión" (Prisma, Django).
- **Pool de conexiones [09]** — valet parking: un encargado con 1 000 llaves no aparca más rápido; un mesero con 50 mesas atiende peor que con 5. · *contención: más concurrencia sobre recurso finito baja el throughput* · ⚠️ vale para OLTP de consultas cortas, no para cargas dominadas por espera externa.
- **Índices y coste del INSERT [13]** — archiveros: cada índice es un archivero que reordena sus fichas con cada pedido. · *N índices ⇒ N+1 escrituras lógicas* · ⚠️ el disco no "confirma" una vez por índice: el WAL se sincroniza por COMMIT.
- **IDs distribuidos Snowflake [16]** — fábrica de matrículas: un solo sello numerador hace fila; códigos aleatorios no tienen orden; la "placa inteligente" de 64 bits la estampan mil mesas independientes calibradas al milisegundo. · *tiempo + shard + secuencia sin coordinador* · ⚠️ el orden es aproximado (relojes), no causal.
- **Elección de motor (Discord) [17]** — libreta en el mostrador (Mongo) → ejército de archivadores idénticos (Cassandra) → los mismos archivadores reconstruidos con menos de la mitad de máquinas (Scylla); la mesa de trabajo es la RAM y el sótano el disco. · *working set vs RAM; coste de GC* · ⚠️ el cambio de motor no arregla particiones calientes: eso lo resolvió también el coalescing.
- **N+1 [36]** (complemento) — mesero con una mesa de 50 que va a la cocina una vez por plato; `fetch join` es una bandeja y batch fetch, bandejas de 25. · *una query por fila* · ⚠️ con colecciones la bandeja única multiplica filas y paginarla ocurre en memoria.
- **UPDATE vs event sourcing [25]** — el saldo en la app es la foto; el extracto es la película; un extracto oficial no se arregla con corrector líquido. · *estado sobrescrito vs log inmutable* · ⚠️ la mayoría de datos no necesita película; la foto con auditoría suele bastar.

## Consistencia y mensajería

- **Reservas globales [11]** — hotel con dos recepciones en extremos opuestos, cada una con su cuaderno, que se copian al final del día. · *escritura local multi-master + replicación asíncrona ⇒ doble venta* · ⚠️ con un único cuaderno central no hay carrera, solo latencia.
- **Consistencia eventual [23]** — dos vistas del mismo pedido que no coinciden, con un reloj en medio. · *propagación → lag → convergencia* · ⚠️ "alterna al refrescar" es falta de lecturas monótonas, no solo lag.
- **Dead Letter Queue [24]** — fábrica con cinta transportadora; un paquete rojo se atasca y va a un sótano de cuarentena. · *poison message + reintentos sin techo* · ⚠️ en una cola estándar el paquete rojo no detiene la cinta: solo con orden estricto (partición, FIFO).
- **Race condition [33]** (complemento) — pizarra vs máquina expendedora: dos vendedores leen "queda 1" y ambos venden; la máquina comprueba y entrega en un solo movimiento. · *read-modify-write vs operación atómica* · ⚠️ no cubre el write skew entre filas distintas, y abrir una transacción no crea la "máquina".
- **Idempotencia [34]** (complemento) — cheque numerado: el banco no paga dos veces el 0042 y rechaza un 0042 con otro importe. · *clave por intento lógico + respuesta almacenada* · ⚠️ las claves caducan y el cheque no modela el estado "en proceso" (409).
- **CQRS [26]** — cocina (reglas estrictas) y vitrina (lo que ve el cliente), con el mesero como proyector entre ambas. · *write model vs read models + lag de proyección* · ⚠️ CQRS no exige dos bases ni eventos.
- **Saga [27]** — estaciones en fila con un hueco entre la 3 y la 4; el detective sigue el Order ID por cuatro mundos. · *transacciones locales sin rollback global* · ⚠️ compensar no es "deshacer": es una operación de negocio inversa y visible.
- **Outbox [28]** — dos mundos (BD y bus) que deben contar la misma historia; guardar y publicar son "dos apuestas seguidas". · *dual write no atómico* · ⚠️ Outbox resuelve la salida, no la entrega duplicada: sigue haciendo falta idempotencia.
- **Webhooks duplicados [29]** — el mensajero toca el timbre dos veces porque nadie abrió a la primera. · *at-least-once + respuesta lenta ⇒ reintentos* · ⚠️ algunos proveedores (GitHub) no reintentan solos.

## Resiliencia y operación

- **Heap vs RSS [04]** — ascensor con letrero "máx. 512 kg": el heap son las bolsas del súper; el RSS es el sensor de peso (bolsas + mochila + carrito); vaciar bolsas (GC) no saca el carrito. · *el cgroup cuenta todo el proceso* · ⚠️ el kernel mira `memory.current`/working set, no exactamente RSS.
- **Async no es paralelo [05]** — farmacia con un farmacéutico que va al depósito y vuelve antes de llamar al siguiente; con 10 000 gritando a la vez colapsa; la solución es un mostrador con 5 puestos. · *serie = N × RTT; sin límite = agotar recursos; semáforo = equilibrio* · ⚠️ el crecimiento en serie es lineal, no exponencial.
- **ReDoS [10]** — estacionamiento subterráneo buscando la rampa: pasillo, pared, reversa, siguiente pasillo; en un laberinto enorme nunca sales. · *backtracking superlineal* · ⚠️ no todos los casos son exponenciales (Stack Overflow fue cuadrático).
- **Load balancing [19]** — la torre de control no aterriza aviones, asigna pistas; la capacidad es la suma de pistas; sin torre, todos a la misma pista. · *distribución + health checks* · ⚠️ un LB L4 asigna por conexión: con HTTP/2 una "pista" puede recibir todo.
- **Despliegues sin downtime [20]** — cambiar el avión con pasajeros a bordo; rolling es una ola que cambia cajas de color; blue/green es cambiar de piscina; canary es el canario en la mina. · *radio de impacto acotado + rollback* · ⚠️ cambiar de piscina solo es reversible si los datos de la nueva siguen siendo legibles por la vieja.
- **Filas virtuales [21]** — la puerta del estadio decide si entras, esperas con tu lugar o no pasas; la fila convierte un golpe en un chorro. · *control de admisión* · ⚠️ la puerta no protege si hay otra entrada: el origen debe validar el pase.
- **Cache stampede [30]** — estampida por una puerta angosta; barras de TTL alineadas que caen juntas; el jitter convierte el bombardeo en llovizna. · *sincronía de expiraciones y misses* · ⚠️ distinguir hot key individual de expiración masiva.
- **Circuit breaker [31]** — el fusible abre el circuito para no quemar la instalación; no repara el aparato, evita que arrastre al resto. · *fail fast ante dependencia degradada* · ⚠️ el breaker es local al cliente; no da aire al downstream si otros siguen golpeando.

- **Rate limiting [38]** (complemento) — portero con una caja de pulseras que se rellena a ritmo fijo (token bucket); el leaky bucket es un embudo que gotea. · *admisión por identidad con ráfagas acotadas* · ⚠️ N réplicas son N porteros con N cajas; una caja central añade latencia y un punto de fallo.

## Estilos y diseño de sistemas

- **Código "limpio" sobre-abstraído [07]** — el tour guiado: si un compañero necesita un tour para seguir el flujo en una guardia, sobra indirección. · *coste cognitivo de cada salto* · ⚠️ con ≥2 variantes reales la abstracción sí paga.
- **Monolito vs microservicios [08]** — edificio de oficinas: en el monolito pides el documento al compañero de al lado; en microservicios tomas un taxi a otra sede; con sagas además contratas despachador, GPS y protocolo de devolución. · *llamada en memoria vs red + consistencia distribuida* · ⚠️ la "otra sede" sí permite escalar y desplegar por separado.
- **Microfrontends con iframes [14]** — dos mundos distintos bajo pantallas que se ven iguales; Conway como espejo del organigrama. · *aislamiento de runtime a cambio de duplicación* · ⚠️ la pregunta es separar el deploy o el código.
- **Fan-out de seguidores [15]** — buzones: dejar la carta en cada buzón al enviarla vs fotocopiarla para un país entero; las megacuentas van a una vitrina central. · *write path vs read path + outliers* · ⚠️ las escrituras dependen de los seguidores del autor.
- **Actores (WhatsApp/Erlang) [18]** — concierto con una sola puerta; cartero gigante con candado vs ejército de mini-mensajeros con buzón propio. · *procesos aislados + mensajes + supervisión* · ⚠️ sin memoria compartida no hay races de memoria, pero sí de orden de mensajes.
- **Polling, SSE, WebSocket [22]** — preguntar una y otra vez; radio en directo; llamada telefónica abierta en ambos sentidos. · *pull vs push unidireccional vs bidireccional* · ⚠️ falta el long polling como punto intermedio.

- **API Gateway [46]** (complemento) — recepción de un edificio de oficinas: identifica, dirige al piso, registra y limita, pero no negocia contratos. · *preocupaciones transversales en el borde* · ⚠️ cada oficina debe autorizar por objeto; una sola recepción es punto único de fallo; agregar cuesta lo que tarde el piso más lento.

## Contratos y seguridad

- **Validación de archivos [02]** — fiarse de la etiqueta pegada por fuera del paquete en lugar de abrirlo y mirar el contenido. · *nombre y MIME los controla quien envía* · ⚠️ mirar los primeros bytes tampoco basta para formatos complejos (ZIP/OOXML, SVG).
- **JWT vs sesiones [12]** — guardia que consulta el libro de recepción en cada pasillo vs tarjeta programada con firma; un token robado es un pasaporte robado con sello auténtico. · *stateless no revocable vs stateful revocable* · ⚠️ las sesiones en un store en memoria sí escalan.
- **Versionado de API [32]** (complemento) — enchufe de pared: forma y voltaje son el contrato; pasar de 110 V a 220 V con el mismo enchufe es el "200 OK que rompe". · *cambio semántico con forma intacta* · ⚠️ un enchufe no negocia versión y no tiene equivalente para cambios aditivos.
- **UTC y fechas [35]** (complemento) — torre de control y agenda del pasajero: la torre registra lo ocurrido en hora Zulu; la reserva futura va en hora local y se recalcula si cambian las reglas. · *instante vs hora civil con zona* · ⚠️ un cumpleaños no tiene hora Zulu; el tiempo Unix ignora los segundos intercalares.
- **Códigos HTTP [37]** (complemento) — sello del sobre devuelto: la sala de correo decide por el sello sin abrir la carta; un 200 con error dentro es un sobre marcado "entregado". · *el código es el contrato para clientes, proxies y métricas* · ⚠️ un sobre lleva un solo sello aunque haya varios problemas, y un intermediario puede poner el suyo (502/504).

## Código

- **Big O [39]** (complemento) — guía telefónica (log n) frente a una fiesta donde todos se dan la mano (n²). · *orden de crecimiento* · ⚠️ la guía exige haberla ordenado antes, y trata igual un acceso a memoria que una llamada de red.
- **SOLID [40]** (complemento) — la instalación eléctrica de una casa: tablero por circuitos, regletas, adaptadores, enchufe estándar. · *módulos con contratos estables* · ⚠️ en software el enchufe lo diseñas tú: hacerlo antes de tener dos aparatos da el enchufe equivocado.
- **DIP [41]** (complemento) — la ficha técnica del restaurante que cualquier proveedor puede cumplir. · *el dominio define la abstracción* · ⚠️ las abstracciones tienen fugas (un fake en memoria no se comporta como SQL) y con un único proveedor es burocracia.
- **ISP [42]** (complemento) — control remoto de 60 botones frente a uno por uso. · *interfaces por rol de cliente* · ⚠️ 30 interfaces de un método dispersan el concepto.
- **LSP [43]** (complemento) — pieza de repuesto que encaja en los tornillos pero aguanta menos presión. · *contrato de comportamiento, no de firma* · ⚠️ el contrato rara vez está escrito (ley de Hyrum).
- **OCP [44]** (complemento) — corcho frente a pared pintada: se añaden tarjetas sin repintar. · *extensión sin modificación* · ⚠️ solo protege contra el cambio que anticipaste; con 200 tarjetas es ilegible.
- **SRP [45]** (complemento) — el empleado con tres jefes. · *una razón (un actor) para cambiar* · ⚠️ en equipos pequeños no hay actores distintos y dividir añade navegación.

## IA

- **Contexto en agentes [47]** (complemento) — consultor sin memoria con una mesa de trabajo de tamaño fijo que se barre al salir; el archivo está en otra sala y un becario trae hojas. · *ventana de contexto, estado en la aplicación, recuperación* · ⚠️ el modelo no lee en orden ni se cansa: su sesgo es de posición y de dilución; la caché abarata pero no agranda la mesa.
- **Tokens [48]** (complemento) — imprenta de tipos móviles con bloques de sílabas: se paga por pieza y la redacción sale más cara. · *límite y coste en tokens, salida más cara* · ⚠️ los bloques son estadísticos (no sílabas) y cada modelo trae su propia caja de tipos.
