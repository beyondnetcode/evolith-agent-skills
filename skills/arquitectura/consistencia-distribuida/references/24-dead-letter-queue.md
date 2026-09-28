# [24] Dead Letter Queue explicada: el mensaje que paró la fábrica

> Fuente: TheDebugDuck — https://youtu.be/A9EsyymseL8 · notas parafraseadas; «(complemento)» = conocimiento añadido o corrección.

- **Síntoma en producción:** viernes 3 a.m.; sin alertas, CPU aparentemente sana, pero las facturas no salen. Sube la **edad del mensaje más antiguo**, se atrasan facturas/webhooks/emails de cobro, ningún servicio caído; parece "paranormal" y se sospecha de la nube.
- **Causa raíz (mecanismo):** **poison message** (MSG-9F2A): payload que la versión actual del consumidor no puede procesar (JSON roto, tipos invertidos, campo nuevo, null inesperado, regla de negocio que explota). El broker cumple: tras el *visibility timeout* el mensaje reaparece, otro worker lo toma y falla con la misma traza, en bucle indefinido sin techo de reintentos; consume capacidad y retrasa los mensajes sanos detrás.
- **Metáfora visual del video:** fábrica con cinta transportadora; un paquete rojo que se atasca y un sótano de cuarentena (la DLQ).
- **Estrategias / solución:**
  1. **DLQ pareada** con umbral: SQS `redrivePolicy { deadLetterTargetArn, maxReceiveCount: n }`; Azure Service Bus: subcola *dead-letter* por entidad con `MaxDeliveryCount`; otros brokers por TTL/expiración; o **rechazo explícito** desde el código ("esto no lo proceso más").
  2. **Diagnóstico por message ID** en tres fuentes: broker (dónde está y cuántas recepciones), logs (stack trace, versión del deploy), cambio reciente (commit que alteró el esquema). Primer paso del on-call: abrir el cuerpo del mensaje, no reiniciar pods.
  3. **Redrive con juicio:** DLQ → fix → reproducir en staging → redrive (a veces mensaje a mensaje) → cola principal. Nunca redrive masivo a ciegas.
  4. **Alertar si profundidad de DLQ > 0** (`ApproximateNumberOfMessagesVisible` en SQS o equivalente) con dueño.
  5. **Handlers idempotentes:** el redrive reentrega (at-least-once); sin idempotencia genera doble cargo/email.
  ```
  consumir(msg):
    try: procesar(msg); ack(msg)
    except ErrorPermanente: dead_letter(msg, motivo)          # (complemento) no gastar reintentos
    except ErrorTransitorio: nack(msg)  # reintento con backoff; broker mueve a DLQ al superar maxReceiveCount
  ```
- **Trade-offs y cuándo NO aplicar:** la DLQ no arregla el bug, solo aísla; requiere trabajo humano (inspección, fix, replay). Umbral muy bajo manda a DLQ fallos transitorios; muy alto prolonga el atasco. En flujos con orden estricto, sacar un mensaje a DLQ rompe el orden de su entidad (complemento: considerar pausar la clave/partición en vez de saltar).
- **Heurísticas y umbrales:** alerta con DLQ > 0 sostenido; `maxReceiveCount` explícito y documentado; secuencia fija DLQ→fix→staging→redrive. (complemento) Azure `MaxDeliveryCount` por defecto 10; Sidekiq 25 reintentos (~21 días) antes del *Dead set*.
- **Anti-patrones / señales de alerta:** cola sin DLQ; DLQ sin alertas ("sótano olvidado"); redrive masivo sin reproducir en staging; purgar la DLQ sin postmortem; DLQ como basurero permanente; logs sin message ID; reiniciar pods o escalar infraestructura ante un atasco de cola; construir una "cola manual" cuando el producto ya trae dead-letter.
- **Preguntas de revisión arquitectónica:**
  1. ¿Cada cola/suscripción tiene DLQ pareada y un umbral de entrega documentado?
  2. ¿Se distinguen errores permanentes (DLQ inmediata) de transitorios (reintento con backoff)?
  3. ¿Quién recibe la alerta de DLQ > 0 y cuál es el runbook de redrive?
  4. ¿El consumidor es idempotente para soportar reentregas del redrive?
  5. ¿Los logs llevan message ID, versión de deploy y esquema del payload?
  6. ¿Se monitoriza la edad del mensaje más antiguo además de la profundidad?
- **Caso real / empresa citada:** Amazon SQS (redrive policy), Azure Service Bus (dead-letter subqueue), Uber (poison pills en pipelines Kafka), Shopify y e-commerce (background jobs con reintentos acotados y "dead set"). Lecturas: *Designing Data-Intensive Applications* (Kleppmann), *Enterprise Integration Patterns* (Hohpe & Woolf).
- **Precisión técnica:**
  - En una cola estándar (SQS standard), un poison message **no bloquea** toda la cola: desperdicia capacidad y reintentos. El bloqueo real (head-of-line) ocurre con orden estricto: partición Kafka (el consumidor no avanza el offset), grupo de mensajes SQS FIFO, sesiones de Service Bus o consumidor único serial (complemento).
  - Kafka no tiene DLQ nativa: se implementa en el consumidor o con retry topics/DLQ topic (Uber publicó ese diseño en 2018) o `errors.deadletterqueue.topic.name` en Kafka Connect (complemento).
  - SQS estándar: la expiración en la DLQ cuenta desde el encolado **original**; la retención de la DLQ debe ser mayor que la de la cola origen (complemento).
  - El video menciona a la vez "CPU sobrada" y "CPU al máximo": ambos son posibles (worker ocioso esperando vs. worker quemando reintentos); la señal fiable es la edad del mensaje más antiguo.
  - La atribución de Sidekiq a Shopify es vaga; el "dead set" es una característica de Sidekiq.
