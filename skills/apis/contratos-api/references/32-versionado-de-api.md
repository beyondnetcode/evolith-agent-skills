# [32] API Versioning explicado: 200 OK pero el contrato cambió

> Fuente: TheDebugDuck — https://youtu.be/hJiCokA2Sps · notas parafraseadas; «(complemento)» = conocimiento añadido o corrección.
> Estado: elaborado a partir del título y el temario público del video; la transcripción no estuvo disponible (bloqueo de YouTube, 2026-09-28). Lo que no figura en el temario es «(complemento)». Pendiente de contrastar con la transcripción.

- **Síntoma en producción:** la API responde 200 OK, no hay errores ni alertas, y aun así el negocio dice que los números no cuadran. Variantes típicas (complemento): `monto` pasó de céntimos a unidades o de "sin IGV" a "con IGV"; un `estado` nuevo que la app móvil trata como "desconocido → cancelado"; un campo renombrado que el cliente lee como `null` y convierte en 0; una lista que cambió de orden o de paginación; una fecha que empezó a llegar en hora local. Los dashboards técnicos siguen en verde porque el fallo es **semántico**, no de transporte.
- **Causa raíz (mecanismo):** el **contrato** de una API es todo lo que un cliente puede observar y usar: rutas, métodos, campos, tipos, obligatoriedad, valores de enum, unidades, códigos de estado, forma de los errores, orden, paginación y límites. Un **breaking change** es cualquier cambio que obliga a un cliente existente a modificar su código para seguir obteniendo el mismo resultado. Dos agravantes (complemento): (1) los cambios semánticos (misma forma, otro significado) pasan cualquier validación de esquema; (2) los clientes que no controlas —apps móviles ya instaladas, integraciones B2B, SDKs congelados— no se actualizan al ritmo de tus despliegues. Ley de Hyrum: con suficientes consumidores, cualquier comportamiento observable acaba siendo una dependencia de alguien.
- **Metáfora visual (complemento; propuesta propia, no es la del video):** un **enchufe de pared**. Detrás de la pared puedes rehacer toda la instalación (implementación); la forma de los orificios y el voltaje (contrato) son una promesa a aparatos que no conoces. Pasar de 110 V a 220 V sin cambiar la forma del enchufe es el "200 OK que rompe": el aparato encaja, enciende y se quema. Versionar es instalar un enchufe nuevo al lado y retirar el viejo con aviso y fecha.
- **Estrategias / solución:**
  1. **Clasificar el cambio antes de decidir** (complemento):
     - Compatible (aditivo): endpoint nuevo; campo opcional nuevo en la respuesta; parámetro opcional nuevo cuyo valor por defecto preserva el comportamiento; relajar una validación; valor de enum nuevo **solo si el contrato declaró el enum como abierto**.
     - Breaking: quitar o renombrar campo/endpoint; cambiar tipo, formato o unidad (número → string, segundos → ms, hora local → UTC); volver obligatorio lo opcional; parámetro obligatorio nuevo; endurecer validación; cambiar semántica, valor por defecto, orden o paginación; cambiar códigos de estado o forma del error; cambiar requisitos de autenticación/autorización; quitar valores de enum.
  2. **Evolucionar sin romper clientes** mientras se pueda: cambios aditivos + (complemento) **tolerant reader** en los clientes (ignorar campos desconocidos, no depender del orden, rama `default` en todo enum) + **expand/contract** (*parallel change*) para lo que sí rompe:
     ```text
     expand   → publicar `importe_centimos` junto a `monto`; ambos documentados y calculados de la misma fuente
     migrate  → medir quién sigue leyendo `monto` (logs por client_id / versión de app) y avisar con fecha
     contract → retirar `monto` solo con uso medido ≈ 0 o al vencer el sunset pactado
     ```
  3. **Versionar cuando el cambio rompe y expand/contract no alcanza.** Dónde poner la versión (URL, header y query según el temario; media type y fijación por cuenta son complemento):

     | Esquema | Ejemplo | A favor | En contra |
     |---|---|---|---|
     | Ruta | `/v2/pedidos` | visible en logs, fácil de enrutar en gateway y de cachear; el más común (Google AIP-185) | versiona toda la API a la vez; la URI del recurso deja de ser estable; invita a duplicar controladores |
     | Header | `X-GitHub-Api-Version: 2022-11-28` | URI estable; versiones por fecha, frecuentes y pequeñas | invisible si no se registra; exige `Vary` en caches; el valor por defecto sin header es una decisión de contrato |
     | Query | `?api-version=2024-10-01` (estilo Azure) | explícito y fácil de probar | se mezcla con parámetros de negocio; se pierde en redirecciones o claves de caché mal definidas |
     | Media type | `Accept: application/vnd.acme.pedido.v2+json` | versiona la representación, no la URI | peor soporte en tooling y gateways; difícil de depurar y documentar |
     | Fijada por cuenta | versión asignada en la primera llamada + override por header (Stripe) | el cliente no se rompe por no enviar versión | el servidor mantiene transformaciones entre muchas versiones |

  4. **Deprecación y sunset como parte del contrato** (headers: complemento):
     ```http
     HTTP/1.1 200 OK
     Deprecation: @1788220800
     Sunset: Mon, 01 Mar 2027 00:00:00 GMT
     Link: <https://api.ejemplo.com/docs/migrar-a-v2>; rel="deprecation"; type="text/html"
     ```
     `Deprecation` (RFC 9745) usa fecha de Structured Fields: `@` + segundos Unix (aquí 2026-09-01T00:00:00Z). `Sunset` (RFC 8594) usa HTTP-date y no puede ser anterior a la deprecación. Tras el sunset, responde **410 Gone** con `application/problem+json` y enlace a la migración (o 308 si el recurso tiene URI nueva equivalente), nunca un 404 o 500 genérico.
  5. **OpenAPI y gateway como puntos de control:** el documento OpenAPI versionado en el repositorio es la fuente del contrato. (complemento) `deprecated: true` en operaciones, parámetros y, vía JSON Schema 2020-12 (OpenAPI 3.1), en propiedades; diff del contrato en CI (p. ej. oasdiff u openapi-diff) que **falla** ante breaking no declarados; lint (Spectral); contratos dirigidos por el consumidor (Pact) en B2B e internos. El gateway enruta `/v1` y `/v2`, inyecta `Deprecation`/`Sunset` y mide uso por versión y consumidor.
  6. **Observabilidad del contrato:** (complemento) métricas por versión × consumidor (API key, client_id, versión de app) × endpoint; uso de campos deprecados; tasa de 4xx por consumidor tras cada despliegue; y **métricas de negocio** (conteos, sumas de importes por día contra la línea base), las únicas que detectan un "200 OK con números que no cuadran".
- **Trade-offs y cuándo NO aplicar:** cada versión viva multiplica código, pruebas, documentación, soporte y superficie para parches de seguridad. No versiones cambios aditivos. No crees `v2` para un campo: usa expand/contract. En APIs internas con un solo consumidor que se despliega a la vez (o monorepo), coordina el cambio en lugar de versionar (complemento). Versión mayor en la ruta para rediseños grandes; versiones por fecha en header cuando hay cambios pequeños y frecuentes. Apps móviles: no puedes forzar la actualización; necesitan la ventana más larga o una señal de versión mínima soportada propia del contrato (complemento).
- **Heurísticas y umbrales** (complemento salvo el temario):
  - Compatibilidad por defecto; versión mayor solo ante breaking inevitable; ≤ 2 versiones mayores vivas.
  - Ventana de sunset: API pública ≥ 12 meses (GitHub garantiza ≥ 24 meses a la versión anterior); B2B según contrato firmado; móvil ≥ vida de la versión de app más antigua con uso relevante.
  - Retirar solo con uso medido ≈ 0 durante ≥ 30 días o con los consumidores restantes contactados por nombre; *brownouts* programados (cortes cortos anunciados con 410) para descubrir clientes olvidados.
  - Sin header de versión → versión estable más antigua soportada, nunca "la última".
  - Checklist de 6: OpenAPI en el repo; diff bloqueante en CI; política de enums abiertos declarada; `Deprecation` + `Sunset` + `Link`; uso por versión y consumidor; changelog y aviso directo a consumidores.
- **Anti-patrones / señales de alerta:** cambiar unidades o significado de un campo sin cambiar nombre ni versión; `v2` como copia completa del código de `v1` que diverge; una versión nueva por sprint; default "latest" cuando falta el header (cada release rompe a quien no fija versión); retirar por fecha sin medir quién queda; 404 tras el sunset; clientes con deserialización estricta (Jackson falla ante propiedades desconocidas por defecto; Spring Boot lo desactiva) o `switch` exhaustivo sin `default` sobre enums del servidor; OpenAPI escrito a mano que ya no coincide con el código.
- **Preguntas de revisión arquitectónica:**
  1. ¿El cambio es aditivo o breaking según la lista? ¿Cambia el significado de algún campo existente aunque la forma sea igual?
  2. ¿Quién consume hoy este endpoint (client_id, versión de app, partner) y con qué evidencia?
  3. ¿El diff de OpenAPI en CI bloquea breaking changes no declarados?
  4. ¿Qué versión recibe un cliente que no envía versión?
  5. ¿Hay `Deprecation`, `Sunset`, `Link` y aviso directo con fecha a cada consumidor afectado?
  6. ¿Qué responde la versión retirada después del sunset y quién vigila ese tráfico?
  7. ¿Qué métrica de negocio detectaría en menos de un día un 200 OK con datos incorrectos?
- **Caso real / referencias** (complemento; no se sabe qué casos cita el video):
  - GitHub REST: header `X-GitHub-Api-Version` con fechas; sin header se usa `2022-11-28`; al salir `2026-03-10`, la anterior quedó con soporte hasta 2028-03-10. Su lista de breaking incluye quitar valores de enum, añadir validaciones y cambiar requisitos de autorización.
  - Stripe: versión fijada por cuenta con override `Stripe-Version`; desde `2024-09-30.acacia`, versiones mensuales sin breaking y dos mayores al año. Considera compatibles añadir propiedades, cambiar su orden, cambiar la longitud de IDs opacos, añadir tipos de evento y valores a enums abiertos: sus clientes deben ser tolerant readers. Los webhooks se renderizan con la versión del endpoint.
  - Azure: `api-version` por query con fecha. Google AIP-185: versión mayor en la ruta.
  - Primarias: RFC 9745 (Deprecation, mar-2025, Standards Track); RFC 8594 (Sunset, may-2019, Informational); OpenAPI 3.1.1 (oct-2024; existe 3.2.0, sep-2025); Fowler, *TolerantReader*; Sato, *ParallelChange*.
- **Precisión técnica:**
  - Versionar no evita breaking changes: solo aísla a quien no migra. La estrategia principal es no romper (aditivo + tolerant reader + expand/contract) (complemento).
  - Añadir un campo es compatible solo si los clientes ignoran lo desconocido; añadir un valor de enum solo si el enum se declaró abierto (complemento).
  - `Deprecation` no cambia el comportamiento del recurso: sigue funcionando (RFC 9745). El fin lo marca `Sunset`, que RFC 8594 define como pista, no garantía (complemento).
  - `Deprecation` usa `@<segundos Unix>`; `Sunset` usa HTTP-date. No son intercambiables (complemento).
  - `info.version` de OpenAPI es la versión del documento, distinta de la versión de la especificación (`openapi: 3.1.1`) y no necesariamente la de la API expuesta (complemento).
  - Versionar por header sin `Vary: <header>` permite que una caché compartida sirva la respuesta v1 a un cliente v2 (complemento).
  - 426 Upgrade Required es para cambiar de protocolo y exige el header `Upgrade`; no es el código de "actualiza tu app" (complemento).
