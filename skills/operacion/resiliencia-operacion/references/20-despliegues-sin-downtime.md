# [20] Cómo actualizar tu app en producción SIN que los usuarios lo noten

> Fuente: TheDebugDuck — https://youtu.be/0QsGouoEy-k · notas parafraseadas; «(complemento)» = conocimiento añadido o corrección.

- **Síntoma en producción:**
  - Un deploy que "apaga la ciudad" (downtime total).
  - Errores fantasma durante un rolling: el mismo endpoint devuelve 500 a unos usuarios y 200 a otros.
  - Rollouts atascados a medias; rollbacks que tardan 40 minutos de pipeline.
  - Canary con CPU verde mientras cae la conversión del checkout.
- **Causa raíz (mecanismo):**
  - Blast radius total (todo el tráfico al cambio a la vez).
  - Convivencia de versiones sin compatibilidad hacia atrás: contrato JSON, semántica de status codes o migraciones de BD que v1 no tolera.
  - Capacidad del clúster insuficiente para el `maxSurge`.
  - Promoción sin criterios de aborto medibles.
  - Confundir "pasó el pipeline" con "está sano en producción".
- **Metáfora visual del video:** cambiar el avión con pasajeros a bordo desde la sala de control. Rolling es una ola que cambia cajas de color; blue/green es cambiar de piscina; canary es el canario en la mina.
- **Estrategias / solución:**
  - **Recreate:** mata todos los pods y luego levanta los nuevos, con un hueco. Para staging, herramientas internas o ventana anunciada.
  - **RollingUpdate:** sustitución gradual (default en Kubernetes). `maxUnavailable` y `maxSurge` = 1/1 es conservador; más surge acelera, pero consume CPU y RAM del clúster. Exige compatibilidad hacia atrás o feature flags: si v2 añade un campo, v1 lo ignora o usa un default.
  - **Blue/Green:** dos stacks completos; se valida green y se hace el cutover cambiando el selector del Service (o la regla del LB/DNS). El rollback consiste en devolver el selector.
  - **Canary:** 1–10 % del tráfico por pesos en ingress o mesh (Istio, Linkerd, NGINX, LB del cloud), con gates automáticas de salud y negocio.
  - **Progressive delivery:** escalones explícitos con pausas (Argo Rollouts, Flagger, Spinnaker + Kayenta).
  - **Shadow/dark launch:** copiar tráfico real a v2 sin devolver su respuesta; comparar resultados y latencias antes del canary.
  - **Feature flags:** separar *deploy* (binario en producción) de *release* (comportamiento visible); rollback de producto sin redeploy.
  - **Canary ≠ A/B:** el canary pregunta "¿rompe producción?"; el A/B pregunta "¿mejora la conversión?".
  ```yaml
  # Rolling conservador (reescrito)
  strategy:
    type: RollingUpdate
    rollingUpdate: { maxUnavailable: 1, maxSurge: 1 }
  ---
  # Blue/green: el Service apunta a una "piscina"; rollback = volver el selector
  kind: Service
  spec: { selector: { app: checkout, track: green } }   # antes: track: blue
  ---
  # Progressive delivery (estilo Argo Rollouts)
  strategy:
    canary:
      steps:
        - setWeight: 1
        - pause: { duration: 5m }
        - setWeight: 5
        - pause: { duration: 5m }
        - analysis: { templates: [ { templateName: checkout-health } ] }  # error_rate<1%, p99<400ms, conversión estable
        - setWeight: 25
        - pause: { duration: 10m }
        - setWeight: 100
  ```
  ```text
  # Shadow (middleware)                           # Feature flag
  handle(req):                                     if flags.enabled("new-checkout", user): checkoutV2(cart)
    async sendToV2(clone(req))  # sin efectos      else: checkoutV1(cart)
    return v1.handle(req)
  ```
  - Reglas de pulgar del video:
    - Downtime aceptable → Recreate.
    - Rollback instantáneo y presupuesto para doble stack → Blue/Green.
    - Mucho tráfico y riesgo alto → Canary.
    - Misma API pero motor interno nuevo → Shadow.
    - Separar código de comportamiento visible → Flags.
    - Todo compatible hacia atrás → Rolling como default.
- **Trade-offs y cuándo NO aplicar:**
  - Recreate implica downtime.
  - Rolling mezcla versiones y su rollback es otro rollout.
  - Blue/green duplica la infraestructura durante la ventana. (complemento) La BD suele ser compartida: las migraciones deben ser compatibles con ambas versiones (expand/contract), y el cutover corta conexiones largas.
  - El canary necesita volumen para ser estadísticamente significativo, enrutamiento por pesos y métricas de negocio.
  - El shadow duplica carga y es peligroso con efectos laterales (pagos, emails, escrituras): necesita stubs o sandbox.
  - Los flags generan deuda (flags muertos) y combinatoria de pruebas; necesitan dueño y fecha de retiro.
- **Heurísticas y umbrales:**
  - Canary al 1/5/10 % (ejemplo 95/5).
  - Gates: error rate > 1 %, p99 > 400 ms o caída de conversión → rollback automático.
  - Escalones 1 → 5 → 25 → 100 con pausas de ~5 min.
  - `maxUnavailable`/`maxSurge` 1/1 como opción conservadora.
  - Blast radius: 1 de cada 20 usuarios = daño 20 veces menor.
  - Cita: "Un canary sin métricas es solo suerte con estilo."
- **Anti-patrones / señales de alerta:**
  - Big Bang un viernes a las 17:00 sin métricas.
  - Saltarse el canary porque "en staging iba bien"; rolling sin compatibilidad hacia atrás; blue/green sin probar green con tráfico real antes del cutover.
  - Sin runbook de rollback; "pasó el pipeline" usado como criterio de salud.
  - Canary sin gates ni rollback automático; shadow que ejecuta efectos reales; mezclar objetivos de A/B y canary.
  - (complemento) Migraciones destructivas (drop o rename de columnas) en el mismo release que el código que deja de usarlas.
  - (complemento) Pods sin `readinessProbe` ni graceful shutdown (manejo de SIGTERM, `preStop`, drenaje): hay errores en el rolling aunque el código sea compatible.
- **Preguntas de revisión arquitectónica:**
  1. ¿Qué blast radius es aceptable para este cambio y cómo se limita (porcentaje, región, tenant, flag)?
  2. ¿v(n) y v(n+1) pueden convivir: API, eventos, esquema de BD, cachés serializadas?
  3. ¿Cuánto tarda el rollback, está automatizado y se ha probado?
  4. ¿Qué métricas técnicas y de negocio son gates de promoción, y quién o qué aborta?
  5. ¿Las migraciones siguen expand/contract? ¿Qué pasa con los datos escritos por v2 si volvemos a v1?
  6. ¿Los flags tienen dueño y fecha de retiro? ¿El shadow está libre de efectos laterales?
- **Caso real / empresa citada:**
  - Kubernetes (rolling por defecto), AWS CodeDeploy (blue/green con hooks de validación), Netflix (Spinnaker, análisis automatizado de canary con Kayenta), Google SRE (rollouts graduales), LaunchDarkly y similares (flags).
  - Libros: *Continuous Delivery* (Humble y Farley) y *Accelerate* (Forsgren, Humble y Kim).
- **Precisión técnica:**
  - "Accelerate de Nicole Forgren, Jess Humble y Jim Kim" → Nicole Forsgren, Jez Humble y Gene Kim. "Launch similares" → LaunchDarkly y similares.
  - (complemento) El default de Kubernetes es `maxUnavailable: 25%`, `maxSurge: 25%`.
  - (complemento) Un cutover por DNS no es "en un golpe": el TTL y las cachés de los resolvers alargan la convivencia; para cortes atómicos se usan el LB o el selector.
  - (complemento) El "rollback en segundos" de blue/green solo vale si el esquema y los datos escritos por green siguen siendo legibles por blue.
  - (complemento) Kayenta fue desarrollado por Netflix con Google. Sin mesh, un canary por proporción de réplicas solo aproxima el porcentaje.
