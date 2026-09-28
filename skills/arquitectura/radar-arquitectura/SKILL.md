---
name: radar-arquitectura
description: Punto de entrada del arquitecto para diagnosticar incidentes de producción y revisar diseños, PRs o repositorios en busca de riesgos arquitectónicos, con el método de TheDebugDuck (síntoma → rastro → mecanismo → solución en capas → verificación). Incluye un índice síntoma → causa probable → skill especializada y un escáner de señales de código (OFFSET, UUIDv4 como PK, await en bucle, Promise.all sin límite, dual write, webhooks sin firma, JWT en localStorage, regex peligrosas, manifiestos sin límites). Úsala siempre que el usuario pregunte "¿por qué se cae/está lento/duplica/pierde datos?", pida una revisión de arquitectura, un design review antes de salir a producción, una auditoría de riesgos de un repo o PR, o un postmortem técnico, aunque no mencione arquitectura.
license: MIT
metadata:
  categoria: arquitectura
  version: "1.0.0"
  idioma: es
  fuentes: "TheDebugDuck (48 videos)"
  relacionadas: "datos-persistencia, consistencia-distribuida, resiliencia-operacion, estilos-arquitectonicos, contratos-api, seguridad-aplicaciones, diseno-de-codigo, sistemas-con-ia, comunicar-decisiones"
---

# Radar del arquitecto

Esta skill decide **qué mirar primero** y a qué skill especializada derivar. El conocimiento de fondo vive en: `datos-persistencia`, `consistencia-distribuida`, `resiliencia-operacion`, `estilos-arquitectonicos`, `contratos-api`, `seguridad-aplicaciones`, `diseno-de-codigo`, `sistemas-con-ia` y `comunicar-decisiones`.

## Modo A — Diagnóstico de un incidente

El canal resuelve cada caso con el mismo método. Úsalo en orden; saltarse pasos es lo que produce "subimos servidores y sigue cayendo".

1. **Síntoma observable con número.** Qué ve el usuario o el negocio, desde cuándo, con qué magnitud (p99, % de errores, pedidos afectados). Separa síntoma de hipótesis.
2. **La paradoja.** ¿Qué indicadores están en verde? Eso dice qué **no** estamos midiendo (lag, edad del mensaje más antiguo, working set, conexiones del pool, errores por backend).
3. **Seguir el rastro de un ID concreto** (pedido, mensaje, request, evento) a través de cada sistema hasta el punto donde la historia se rompe. Pide logs y trazas de ese ID, no promedios.
4. **Nombrar el mecanismo**, no el componente: "OFFSET recorre y descarta 100 000 filas", "el kernel mata por RSS, no por heap", "el proveedor reintenta porque respondimos tarde". Si no puedes explicar el mecanismo, sigue investigando.
5. **Reproducir con condiciones de producción**: cardinalidad real (5 vs 5 000), mismo límite de memoria, concurrencia, payload adversarial.
6. **Solución en capas**: mitigación inmediata (rollback, kill switch, límite) → corrección → prevención estructural (patrón, restricción, prueba en CI).
7. **Verificación y cierre**: métrica que prueba la corrección, alerta que lo habría detectado antes, runbook, y checklist "antes del próximo deploy". Si hay proceso de ADR o registro de hallazgos, registra ahí.

## Modo B — Revisión preventiva (diseño, PR o repositorio)

1. Si hay código, ejecuta el escáner y trata cada resultado como **pregunta**, no como hallazgo confirmado:
   ```bash
   python3 <ruta-de-esta-skill>/scripts/escanear_senales.py <repo> [--max-por-regla 15] [--solo regla1,regla2]
   ```
   Confirma leyendo el código antes de reportar. Registra también lo que el escáner no ve (diseño, contratos, operación).
2. Recorre los **mínimos de producción** de abajo y marca cuáles no tienen evidencia.
3. Deriva cada riesgo a su skill especializada y usa sus preguntas de revisión.
4. Entrega el informe con el formato de salida.

### Mínimos de producción (preguntas sí/no con evidencia)

| Dominio | Pregunta |
|---|---|
| Datos | ¿Las consultas críticas están medidas con volumen real y el nº de queries por request es O(1)? |
| Datos | ¿El pool está acotado, con timeout de adquisición y métricas? ¿Réplicas × pool < capacidad de la BD? |
| Consistencia | ¿Todo "guardar y publicar" es atómico (Outbox/CDC) y todo consumidor es idempotente? |
| Consistencia | ¿Cada operación con dinero o stock tiene clave de idempotencia y una restricción que impida el estado imposible? |
| Consistencia | ¿Cada cola tiene DLQ, alerta > 0 y runbook de redrive? |
| Resiliencia | ¿Cada dependencia tiene timeout, reintento con backoff+jitter, breaker y bulkhead? |
| Resiliencia | ¿Límites de memoria, concurrencia y tasa definidos por nosotros (no por el kernel o el proveedor)? |
| Resiliencia | ¿Despliegue con readiness, graceful shutdown, expand/contract y rollback probado? |
| Contratos | ¿Los cambios de API son compatibles hacia atrás o versionados, con deprecación y sunset? ¿Los códigos HTTP dicen la verdad? |
| Seguridad | ¿Tokens de vida corta y revocables? ¿Archivos validados por contenido? ¿Fechas como instantes UTC? |
| Estilo | ¿La complejidad distribuida responde a un dolor medido hoy? |
| Operación | ¿Se puede seguir un ID de correlación de punta a punta? |

## Índice síntoma → mecanismo probable → dónde profundizar

| Síntoma | Mecanismo probable | Skill → referencia |
|---|---|---|
| Página 1 rápida, página 5 000 lenta; CPU de BD al 100 % sin consultas raras | OFFSET recorre y descarta | `datos-persistencia` → 01 |
| INSERTs lentos en picos, índice PK que crece y se fragmenta | UUIDv4 como PK en B-tree / demasiados índices | `datos-persistencia` → 03, 13 |
| Endpoint lento sin error, queries que crecen con los datos | N+1, includes anidados, explosión cartesiana | `datos-persistencia` → 36, 06 |
| 504 con la CPU de la BD baja | Pool agotado o conexiones retenidas | `datos-persistencia` → 09 |
| Latencia de lectura que se degrada con el tamaño del dataset | Working set > RAM, particiones calientes, tombstones | `datos-persistencia` → 17 |
| "¿Qué valor tenía esto el martes?" sin respuesta | Estado sobrescrito sin historial | `datos-persistencia` → 25 |
| Doble venta / doble reserva | Check-then-act sin serialización; multi-master | `consistencia-distribuida` → 11, 33 |
| Doble cobro tras doble clic o reintento | Sin idempotencia en el POST | `consistencia-distribuida` → 34 |
| El dato cambia al refrescar; reportes que no cuadran | Lag de réplica/proyección; lecturas no monótonas | `consistencia-distribuida` → 23, 26 |
| Cola que no avanza sin servicios caídos | Poison message sin DLQ | `consistencia-distribuida` → 24 |
| Pagado pero el resto del sistema no lo sabe | Dual write | `consistencia-distribuida` → 28 |
| Pasos ejecutados a medias entre servicios | Sin saga ni compensaciones | `consistencia-distribuida` → 27 |
| Eventos duplicados de un proveedor | Webhook lento + reintentos + sin dedupe | `consistencia-distribuida` → 29 |
| Pod reiniciado con exit 137 y heap "normal" | Límite de cgroup vs memoria total del proceso | `resiliencia-operacion` → 04 |
| Checkout que tarda segundos con CPU baja | `await` en serie dentro de un bucle | `resiliencia-operacion` → 05 |
| CPU al 100 % tras un cambio de config o regex | ReDoS / backtracking | `resiliencia-operacion` → 10 |
| Más servidores y sigue cayendo; un nodo saturado | Balanceo por conexión, sticky, health checks | `resiliencia-operacion` → 19 |
| Errores durante cada despliegue | Versiones incompatibles conviviendo | `resiliencia-operacion` → 20 |
| Caída en la apertura de una preventa | Pico sincronizado sin admisión | `resiliencia-operacion` → 21 |
| Pico de QPS a la BD sin deploy ni tráfico nuevo | Cache stampede | `resiliencia-operacion` → 30 |
| Una dependencia lenta tumba todo | Sin timeout/breaker/bulkhead | `resiliencia-operacion` → 31 |
| API caída por un cliente o bot | Sin rate limiting | `resiliencia-operacion` → 38 |
| "200 OK" pero el negocio dice que los números no cuadran | Cambio de contrato no versionado | `contratos-api` → 32 |
| Clientes que no distinguen error de éxito | Códigos HTTP mal usados | `contratos-api` → 37 |
| Eventos a la hora equivocada, bugs en cambio de horario | Horas locales en lugar de instantes UTC | `contratos-api` → 35 |
| Usuario dado de baja que sigue entrando | JWT de larga vida sin revocación | `seguridad-aplicaciones` → 12 |
| Archivo "imagen" que ejecuta script | Validación por extensión/MIME declarado | `seguridad-aplicaciones` → 02 |
| Equipo lento tras "migrar a microservicios" | Distribución sin dolor que la justifique | `estilos-arquitectonicos` → 08 |
| Feed lento para seguidores de cuentas enormes | Fan-out on write sin tratar outliers | `estilos-arquitectonicos` → 15 |
| Dashboards "en vivo" que saturan el backend | Polling agresivo / transporte inadecuado | `estilos-arquitectonicos` → 22 |
| Cambio simple que toca 15 archivos | Abstracción prematura / acoplamiento | `diseno-de-codigo` → 07, 40–45 |
| Algo que "funcionaba" se vuelve inusable al crecer | Complejidad algorítmica | `diseno-de-codigo` → 39 |
| Agente de IA que olvida, alucina o se encarece | Presupuesto de contexto/tokens mal gestionado | `sistemas-con-ia` → 47, 48 |

El catálogo completo de los 48 videos (URL, skill y lección en una línea) está en `references/indice-videos.md`.

## Formato de salida

```
## Radar — <sistema o PR>
Resumen: <1–3 líneas: riesgo principal y recomendación>.

| # | Riesgo | Evidencia | Mecanismo | Impacto × probabilidad | Recomendación | Skill/ref |
|---|--------|-----------|-----------|------------------------|---------------|-----------|

Sin evidencia (preguntas abiertas): <mínimos de producción que no se pudieron verificar>.
Siguiente paso: <la acción de mayor valor/menor coste>.
```

Ordena por impacto × probabilidad. Una señal del escáner sin confirmar va en "preguntas abiertas", no en la tabla.
