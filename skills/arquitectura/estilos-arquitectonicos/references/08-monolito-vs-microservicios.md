# [08] La MENTIRA de los Microservicios desde el Día 1 (Monolito vs Microservicios)

> Fuente: TheDebugDuck — https://youtu.be/JgrsAyefLFU · notas parafraseadas; «(complemento)» = conocimiento añadido o corrección.

- **Síntoma en producción:** equipo de 5, producto sin validar (meta 100.000 usuarios). Tres meses después de adoptar microservicios "desde el día uno", los sprints se van en pods, pipelines, contratos entre servicios y logs; las features siguen en backlog. Cada cambio = varios deploys; un 500 en checkout exige saltar entre 4–5 servicios sin correlation ID; cobros sin stock por falta de transacción global.
- **Causa raíz (mecanismo):**
  - Confusión entre **velocidad de entrega** y **latencia de request**. Microservicios convierten una llamada en memoria (ns) en una llamada de red: serialización JSON/Protobuf, DNS, TCP, TLS, red, deserialización (ms, a veces decenas). Un clic que toca pedidos, usuarios, inventario, precios y cupones se vuelve una cadena de round-trips. No arregla un índice mal puesto ni un algoritmo pesado; suma latencia.
  - Pérdida de **ACID local**: con base por dominio, pagos puede hacer commit e inventario fallar; no hay rollback global → sagas, compensaciones, colas (Kafka/RabbitMQ), reintentos e idempotencia.
  - **Observabilidad distribuida** como coste fijo: correlation ID, tracing, logs estandarizados, service mesh, dashboards.
  - Microservicios resuelven un problema **organizacional** (Conway): cientos/miles de devs pisándose en un repo/deploy. Sin ese problema, solo se importa el coste.
- **Metáfora visual del video:** edificio de oficinas: en el monolito pides el documento al compañero de al lado; en microservicios tomas un taxi a otra sede, con tráfico y recepción; con sagas además contratas despachador, GPS y protocolo de devolución.
- **Estrategias / solución:** **monolito modular**: un ejecutable, un deploy, normalmente una base de datos, código dividido por dominio (usuarios, pedidos, pagos, notificaciones) con reglas explícitas de qué puede llamar a qué; comunicación por interfaces/DTO; sin acceso a tablas de otro módulo. Extraer un módulo solo cuando lo pida la realidad.
  ```
  Monolito:  BEGIN → cobrar → descontar stock → crear pedido → COMMIT | ROLLBACK
  Distribuido: Pagos(commit) ─evento→ Inventario(falla) ─evento compensación→ Pagos(reembolso)
               + outbox (complemento) + idempotencia + alerta de saga incompleta
  ```
  - Secuencia: primero que funcione → ordenarlo por módulos → extraer solo la parte que no funciona así.
  - (complemento) Imponer fronteras con herramientas: ArchUnit/jMolecules, Spring Modulith, NetArchTest, dependency-cruiser/eslint-plugin-boundaries; esquema (o prefijo de tablas) por módulo; eventos in-process que luego pueden salir a un broker.
- **Trade-offs y cuándo NO aplicar:** el monolito modular solo funciona si se respetan las fronteras; con imports cruzados, una clase gigante compartida y queries sobre tablas ajenas no es modular, es deuda técnica "con carpetas". Microservicios sí se justifican: carga muy superior de un módulo, tecnología/runtime distinto (ML, procesamiento de video), aislamiento de fallos (si cae no tumba todo), equipos que se bloquean en el mismo deploy. Coste: latencia, consistencia eventual, operación y observabilidad.
- **Heurísticas y umbrales:**
  - Equipo de 1 a ~20 → monolito modular casi siempre más rápido. >50 con varios equipos pisándose en el mismo deploy → hablar de separar servicios. (complemento) Entre 20 y 50 es zona gris: decidir con métricas de contención (conflictos de merge, releases congelados, lead time).
  - Fase: validando producto ≠ empresa con dominios claros y estables.
  - Madurez DevOps: si un solo pipeline ya falla seguido, microservicios multiplica el dolor; sin logs decentes, CI estable y acuerdos entre equipos no se está listo.
  - Prime Video: −90% de coste de infraestructura de un servicio concreto al volver a un proceso. Uber: ~2.200 microservicios críticos.
- **Anti-patrones / señales de alerta:**
  - Justificación "así lo hacen Netflix/Amazon" o "así escalamos" sin carga real.
  - Microservicios para resolver una lentitud que es un índice o un algoritmo.
  - Un endpoint que hace N llamadas síncronas encadenadas entre servicios (chatty).
  - Operaciones de negocio que requieren atomicidad cruzando bases de servicios distintos sin saga/compensación.
  - Ausencia de correlation ID/tracing en un sistema distribuido.
  - En el monolito: módulos que consultan tablas de otros, imports cruzados, "God class" compartida.
- **Preguntas de revisión arquitectónica:**
  1. ¿Qué problema organizacional o de carga concreto resuelve la división hoy?
  2. ¿Cuántos saltos de red añade el camino crítico del usuario y cuál es su presupuesto de latencia?
  3. ¿Qué operaciones necesitan hoy ACID entre dominios y cómo se compensan si se separan?
  4. ¿Existen correlation ID, tracing y logs estandarizados antes de distribuir?
  5. ¿Las fronteras de módulo están impuestas por herramientas o solo por convención?
  6. ¿Qué módulo tiene perfil de carga o runtime distinto que justifique extraerlo primero?
- **Caso real / empresa citada:** Amazon Prime Video (2023, monitoreo de calidad A/V: Lambda + Step Functions + S3 entre etapas → un proceso sobre EC2/ECS, −90% coste); Uber (DOMA, ~2.200 microservicios, agrupados en dominios con gateways y capas); Netflix/Amazon/Uber como ejemplos de escala organizacional; ley de Conway (Melvin Conway, 1968).
- **Precisión técnica:**
  - "No existe rollback global" es una simplificación: existe 2PC/XA, pero se evita por bloqueo, disponibilidad y falta de soporte en muchos brokers/NoSQL (complemento).
  - Microservicios no bajan la latencia, pero sí pueden mejorar el **throughput** escalando solo el punto caliente y la **frecuencia de despliegue** independiente; el video lo reconoce solo para módulos con carga distinta.
  - Prime Video: aun así la solución escala horizontalmente clonando el proceso; parte relevante del coste eran las transiciones de estado de Step Functions y las lecturas/escrituras en S3 (complemento). No fue "volver al monolito" de toda la plataforma.
  - Conway: artículo publicado en 1968 ("How Do Committees Invent?"). (complemento) La "maniobra inversa de Conway" (diseñar equipos para obtener la arquitectura deseada) es la contraparte útil.
  - ASR: "bots" = pods; "S2 y SS" = EC2 y ECS; "AIT" = ACID; "en potencia" = idempotencia; "rontain" = runtime; "C estable" = CI estable.
