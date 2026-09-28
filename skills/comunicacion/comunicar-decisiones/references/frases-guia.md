# Frases guía para cerrar explicaciones

Principios del canal reformulados como frases de cierre (las de los videos 32–48 son formulaciones propias: su transcripción no estuvo disponible). Úsalas como "la frase que nos llevamos" de un ADR o postmortem; adáptalas al caso en vez de citarlas literalmente. Número = video de origen.

## Datos
- Una página profunda cuesta lo que descarta, no lo que devuelve. [01]
- El tipo de ID se decide por topología, visibilidad y generación; no hay uno universal. [03]
- El ORM no es lento: hace exactamente lo que el modelo le pidió. [06]
- Un pool más grande no hace más rápida a la base de datos; solo alarga la fila dentro de ella. [09]
- Cada índice acelera una lectura y cobra en cada escritura. [13]
- Si necesitas demostrar qué pasó, no borres el pasado con un UPDATE. [25]
- Una query por fila es una factura por fila. [36]

## Consistencia
- Guardar y avisar en dos pasos es apostar dos veces. [28]
- Sin idempotencia, cada reintento es un cobro nuevo. [34]
- La consistencia eventual se opera: se mide, se alerta y se le avisa al usuario. [23]
- No hay rollback entre servicios; hay compensaciones que alguien diseñó antes del incidente. [27]
- La DLQ no arregla el bug: lo aísla para que el resto siga fluyendo. [24]
- Leer, decidir y escribir en tres pasos es dejar la puerta abierta a otro cliente. [33]

## Resiliencia
- Async libera el hilo, no lo multiplica (parafraseado del video). [05]
- Subir la RAM sin limitar el runtime solo compra minutos. [04]
- Antes de desplegar una regla, pregúntate quién tiene el interruptor para apagarla. [10]
- La fila convierte un golpe en un chorro. [21]
- El breaker no arregla la dependencia caída; evita que arrastre a todos. [31]
- Un canary sin métricas es solo suerte. [20]
- Sticky solo si lo necesitas. [19]
- La sincronía crea picos; el jitter los deshace. [30]
- Un límite que no devuelve 429 con Retry-After solo castiga; uno que lo devuelve, educa. [38]

## Estilos y diseño
- Los microservicios cambian llamadas en memoria por llamadas de red; se justifican por el equipo o la carga, no por moda. [08]
- Pregunta si necesitas separar el despliegue o separar el código: no es lo mismo. [14]
- Diseña el feed empezando por cuántos seguidores tiene quien publica. [15]
- Si tu compañero necesita un tour guiado para seguir el flujo en una guardia, sobra una capa. [07]
- Diseña la reconexión y el heartbeat antes del incidente, no durante. [22]
- El gateway recibe y dirige; el negocio vive detrás. [46]
- Abstrae cuando llega la segunda variante real, no cuando la imaginas. [40–45]
- Lo que funciona con cien elementos puede ser el incidente con un millón. [39]

## Contratos y seguridad
- Todo lo que viaja en la petición lo decide quien la envía: nombre, extensión y MIME incluidos. [02]
- Un token robado es un pasaporte robado con sello auténtico: que caduque pronto y se pueda revocar. [12]
- Un 200 OK puede romper a un cliente si cambió el significado de un campo. [32]
- UTC para lo que ya pasó; hora local con zona para lo que va a pasar. [35]
- El código de estado es para máquinas: clientes, proxies y alertas deciden con él. [37]

## IA
- El contexto es memoria de trabajo finita: se presupuesta y se carga por capas. [47]
- Los tokens miden el límite y la factura; no son palabras. [48]
