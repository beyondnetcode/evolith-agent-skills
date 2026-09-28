# [46] ¿Qué es un API Gateway?

> Fuente: TheDebugDuck — https://youtu.be/cxN_vkyZuto · notas parafraseadas; «(complemento)» = conocimiento añadido o corrección.
> Estado: elaborado a partir del título y el temario público del video; la transcripción no estuvo disponible (bloqueo de YouTube, 2026-09-28). Lo que no figura en el temario es «(complemento)». Pendiente de contrastar con la transcripción.

- **Síntoma en producción:** (complemento; el temario no trae gancho)
  - Sin gateway: la app móvil llama a 6–8 servicios para pintar una pantalla. Cada servicio valida JWT, CORS y TLS a su manera y expone endpoints internos, y refactorizar uno rompe clientes porque estos conocen la topología.
  - Con un gateway sobredimensionado, el síntoma inverso: cada cambio de negocio espera al equipo de plataforma, una configuración errónea tumba todas las APIs a la vez y el p99 del gateway crece por las agregaciones.
- **Causa raíz (mecanismo):**
  - En microservicios, el cliente queda acoplado a la descomposición interna y las preocupaciones transversales se duplican en cada servicio. El gateway ofrece un punto único de entrada que enruta, autentica y simplifica la comunicación entre clientes y servicios (temario).
  - Técnicamente es un reverse proxy L7 con políticas (complemento).
  - Al centralizar, concentra también el riesgo: punto único de fallo, cuello de botella y punto único de cambio (temario: ventajas y desventajas; detalle complemento).
- **Metáfora visual (complemento, propia; la del video no está disponible):** la recepción de un edificio de oficinas.
  - Verifica tu identidad, te dice a qué piso ir, te da una credencial de visita, registra la entrada y limita cuántos suben a la vez. No negocia contratos en nombre de las oficinas.
  - Un BFF es una recepción distinta para mensajería y para clientes VIP.
  - ⚠️ Límites de la metáfora:
    - La credencial abre el edificio, pero cada oficina decide si puedes abrir *ese* cajón (la autorización por objeto vive en el servicio).
    - Una sola recepcionista es un punto único de fallo; un gateway real son varias réplicas detrás de un balanceador.
    - Si la recepción reúne documentos de tres pisos, tardas lo que tarde el piso más lento.
- **Estrategias / solución:**
  1. **Responsabilidades transversales (offloading).** Enrutamiento y autenticación vienen del temario; el resto es complemento.
     - Enrutamiento L7 por host, ruta o cabecera, con reparto por versión (canary, [20] en `resiliencia-operacion`).
     - Terminación TLS, y mTLS hacia dentro.
     - Autenticación en el borde: firma vía JWKS, `iss`, `aud`, `exp` ([12] en `seguridad-aplicaciones`).
     - Rate limiting y cuotas por API key o tenant ([38]).
     - Límites de tamaño, CORS y WAF.
     - Observabilidad: logs de acceso, métricas RED por ruta, `traceparent` (W3C Trace Context) y correlation ID.
     - Timeouts y circuit breaker por ruta ([31]).
     - Caché y compresión.
  2. **Identidad hacia dentro** (complemento):
     - Borra las cabeceras de identidad que lleguen de fuera (`X-User-Id`) y vuelve a inyectarlas firmadas, o reenvía el token.
     - Los servicios solo aceptan tráfico que venga del gateway o del mesh (network policy, mTLS).
  3. **BFF por tipo de cliente** (complemento):
     - Un backend por experiencia (web, móvil, socios), del que es dueño el equipo de ese cliente. Agrega y adapta el formato; el gateway general queda delgado.
     - Un BFF compartido por todos los clientes vuelve a ser el gateway general.
  4. **Agregación con su coste explícito** (complemento):
     - Llamadas en paralelo, con timeout por llamada y deadline total.
     - Respuesta parcial cuando fallan secciones opcionales.
     - La latencia ≈ la llamada más lenta + el coste del salto, no la suma, si van en paralelo. Nada de cadenas en serie.
     - Alternativa: GraphQL/federación con DataLoader, para no crear N+1 remotos ([36] en `datos-persistencia`).
  5. **Lo que NO hace** (complemento):
     - Reglas de negocio (precios, validaciones de dominio).
     - Orquestar sagas o cadenas de llamadas con efectos ([27] en `consistencia-distribuida`).
     - Guardar estado o abrir transacciones.
     - Autorizar por objeto (BOLA).

     Regla: si la regla cambia cuando cambia el negocio, no va en el gateway.
  6. **Operarlo** (complemento):
     - Réplicas sin estado en ≥ 2 zonas, detrás de un LB L4 o anycast.
     - Configuración como código, con despliegue escalonado y rollback: un cambio de gateway tiene radio global.
     - Gateways separados por clase de tráfico (público, socios, interno) para acotar ese radio.
     - Un solo nivel de reintentos, para no multiplicarlos (cliente × gateway × mesh).
  7. **Diferencias con piezas vecinas** (complemento):
     - **Load balancer:** reparte entre instancias del **mismo** servicio, con health checks ([19]). El gateway decide **a qué** servicio va la petición y aplica políticas de API. Suelen ir juntos.
     - **Service mesh:** gobierna el tráfico este-oeste entre servicios (mTLS, reintentos, outlier detection y telemetría, en sidecars o en modo ambient). El gateway gobierna el tráfico norte-sur. El ingress gateway de un mesh puede hacer de API gateway, pero suele traer menos gestión de APIs (WAF, productización, transformación).
     - **Reverse proxy:** es el mecanismo. Gateway = reverse proxy + políticas de API.
- **Trade-offs y cuándo NO aplicar:**
  - Añade un salto de red.
  - Es punto único de fallo y cuello de botella si no se replica y dimensiona (temario: desventajas).
  - (complemento) También puede ser cuello de botella organizativo, si un solo equipo aprueba cada ruta.
  - (complemento) Lock-in con funciones propietarias del producto, y complejidad de configuración.
  - (complemento) No aplica con un monolito, o con 1–2 servicios y un solo cliente: basta un reverse proxy o un LB con TLS.
  - (complemento) El tráfico interno entre servicios no debe salir y volver a entrar por el gateway público (hairpinning).
- **Heurísticas y umbrales:** (complemento)
  - Gateway delgado.
  - BFF cuando hay ≥ 2 tipos de cliente con necesidades divergentes (payload, autenticación, cadencia).
  - Agregar solo si ahorra ≥ 2 viajes del cliente sobre redes de alta latencia.
  - Presupuesto de latencia propio del gateway, medido en p99 y con alerta.
  - ≥ 2 réplicas en ≥ 2 zonas.
  - Timeout del gateway ≥ timeout del backend + un margen, con deadline propagado.
- **Anti-patrones / señales de alerta:**
  - "ESB con ropa de gateway" (Thoughtworks Radar: *Overambitious API gateways*, en Hold).
  - Un gateway que encadena llamadas HTTP con efectos.
  - Servicios que confían en `X-User-Id` sin que el gateway lo haya limpiado.
  - Servicios alcanzables saltándose el gateway.
  - Un mega-gateway compartido, con configuración manual.
  - Reintentos en cliente, gateway y mesh a la vez.
  - Autorización fina solo en el gateway.
  - Un BFF genérico para todos los clientes.
- **Preguntas de revisión arquitectónica:**
  1. ¿Qué responsabilidades tiene el gateway? ¿Se ha colado alguna que sea de negocio?
  2. ¿Cómo llega la identidad al servicio, y qué impide falsificarla o saltarse el gateway?
  3. ¿Cuántas réplicas hay y en cuántas zonas? ¿Qué pasa si se despliega una configuración errónea (canary, rollback)?
  4. ¿Qué latencia añade el gateway (p99) y cuánto suman las agregaciones?
  5. ¿Hace falta un BFF por cliente, o basta el gateway general?
  6. ¿Dónde se reintenta y dónde se corta (timeouts, breaker) para no multiplicar la carga?
- **Caso real / referencias (complemento):**
  - Microsoft Azure Architecture Center, "API gateways" y los patrones Gateway Routing, Gateway Aggregation y Gateway Offloading: https://learn.microsoft.com/azure/architecture/microservices/design/gateway
  - Sam Newman, "Backends For Frontends" (2015). El patrón nació en SoundCloud (Phil Calçado).
  - Chris Richardson, microservices.io: API Gateway y BFF.
  - Thoughtworks Technology Radar: "Overambitious API gateways" y "ESBs in API gateway's clothing", ambos en Hold.
  - Netflix Zuul como gateway de borde.
  - OWASP API Security Top 10 2023 (API1: BOLA).
  - W3C Trace Context.
- **Precisión técnica:**
  - El "punto único de entrada" es lógico, no físico: solo es punto único de fallo si se despliega como una sola instancia, o con una configuración global sin escalonar (complemento).
  - Autenticar en el borde no es autorizar. El servicio sigue comprobando permisos por objeto y no acepta una identidad sin verificar su origen: confianza cero (complemento).
  - El gateway no reduce por sí mismo la latencia total. Ahorra viajes del cliente cuando el RTT del cliente ≫ el RTT interno, pero añade un salto (complemento).
  - Gateway ≠ LB ≠ service mesh. La Gateway API de Kubernetes es una especificación de enrutamiento, sucesora de Ingress; no es un producto de gestión de APIs (complemento).
  - El rate limiting del gateway es admisión por cliente. No sustituye la protección de capacidad del servicio ni el load shedding ([38]) (complemento).
