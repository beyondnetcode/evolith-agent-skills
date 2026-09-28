---
name: comunicar-decisiones
description: Técnica narrativa de TheDebugDuck para explicar decisiones y riesgos de arquitectura — incidente concreto como gancho, "todo está verde pero algo falla", modo detective siguiendo un ID, metáfora visual cotidiana, mecanismo real, solución en capas, trade-offs y checklist final de preguntas antes del próximo deploy. Úsala siempre que haya que redactar el contexto o las consecuencias de un ADR, un postmortem, una propuesta técnica para gerencia o negocio, la descripción de un PR arquitectónico, material de onboarding, o explicar un concepto técnico (consistencia eventual, idempotencia, backpressure…) a alguien que no es especialista, o cuando el usuario pida "explícamelo fácil", "con una analogía" o "para que lo entienda el equipo".
license: MIT
metadata:
  categoria: comunicacion
  version: "1.0.0"
  idioma: es
  fuentes: "TheDebugDuck (estructura narrativa y metáforas de los 48 videos)"
  relacionadas: "radar-arquitectura"
---

# Comunicar decisiones como TheDebugDuck

El canal enseña conceptos difíciles con una estructura muy consistente. Esa estructura funciona también para que un arquitecto **convenza, alinee y deje trazabilidad**: el lector entiende el riesgo porque lo *vio pasar*, no porque se lo enumeraron. Aplícala al contexto de ADRs, postmortems, propuestas y explicaciones; no la uses para reemplazar las secciones formales de una plantilla, sino para llenarlas mejor.

## La estructura en 8 tiempos

1. **Incidente concreto (gancho).** Una escena con hora, números y un ID: "viernes 3 a. m., pedido 4821", "Black Friday, miles de pedidos pagados que el almacén no ve", "200 `await` dentro de un `for`". Nada de "en sistemas distribuidos a veces…". El lector debe reconocer su propio sistema.
2. **La paradoja: todo parece sano.** Dashboards verdes, sin deploy reciente, CPU normal, sin error 500… y aun así el negocio pierde. Esta tensión es lo que obliga a leer el resto y explica por qué el problema no se detecta con el monitoreo actual.
3. **Modo detective.** Seguir un identificador (order ID, message ID, command ID) a través de los sistemas hasta el punto donde la historia se rompe. Enseña el método de diagnóstico, no solo la respuesta.
4. **Metáfora visual cotidiana.** Un objeto físico que el lector ya entiende y que tiene **el mismo mecanismo** que el problema (no solo el mismo "tema"). Ver `references/catalogo-metaforas.md`.
5. **El mecanismo real, sin metáfora.** Qué hace el motor, el broker, el runtime o el kernel. La metáfora abre la puerta; el mecanismo es lo que permite decidir.
6. **Solución en capas, de la más simple a la más completa**, con código o configuración mínima y el criterio para pasar de una capa a la siguiente.
7. **Trade-offs y "cuándo NO".** Qué se paga (latencia, complejidad, operación) y en qué contexto el patrón sobra. Sin esta sección, la explicación es propaganda.
8. **Cierre accionable.** (a) Checklist de N preguntas "antes del próximo deploy" que el lector puede aplicar a su sistema hoy; (b) una frase memorable que resume el principio ("async libera el hilo, no lo multiplica"; "la fila convierte un golpe en un chorro"); (c) casos reales y lecturas para profundizar.

## Reglas de estilo

- **Números concretos > adjetivos.** "40 ms × 200 llamadas = 8 s" convence más que "muy lento". Si el número es ilustrativo, dilo.
- **Una metáfora por concepto** y abandónala cuando empieces a explicar el mecanismo; estirarla produce conclusiones falsas.
- **La metáfora debe fallar donde falla el sistema.** Si no puedes señalar en la metáfora el punto exacto de la falla (el paquete rojo que atasca la cinta, el mensajero que toca dos veces), no es la metáfora correcta.
- **Nombra el anti-patrón como algo que el lector hizo o haría**, sin culpar: "¿tú también habrías dicho que sí?". Genera identificación, no defensa.
- **Casos reales verificables.** Cita la empresa y el año solo si la fuente es pública; si la historia es ilustrativa, preséntala como tal. Los postmortems reales (Cloudflare 2019, Stack Overflow 2016, Knight Capital 2012) son más creíbles que las anécdotas.
- **Checklist de sí/no.** Cada pregunta debe poder responderse con evidencia (métrica, test, archivo), no con opinión.

## Plantillas

### Contexto y consecuencias de un ADR

```markdown
## Contexto
<Escena concreta del riesgo o incidente, con números.> Hoy los indicadores <X> no lo detectan porque <mecanismo>.
Analogía: <metáfora en 1–2 líneas que falle donde falla el sistema>.
Mecanismo: <qué hace realmente el componente, 3–5 líneas>.

## Consecuencias
Positivas: <qué estado incorrecto se vuelve imposible>.
Negativas / coste asumido: <latencia, operación, complejidad>.
Cuándo revisar esta decisión: <umbral o señal>.
Verificación: <checklist de 4–6 preguntas sí/no con su evidencia>.
```

### Postmortem narrativo (sin culpables)

```markdown
**La escena:** <hora, síntoma visible para el usuario, impacto en negocio>.
**Por qué parecía sano:** <qué dashboards estaban en verde y por qué no miraban lo correcto>.
**Siguiendo el rastro:** <ID seguido a través de sistemas; dónde se rompió la historia>.
**El mecanismo:** <causa raíz técnica>.
**Lo que cambiamos:** <capas de solución, de inmediata a estructural>.
**Antes del próximo deploy:** <checklist sí/no>.
**La frase que nos llevamos:** <principio en una línea>.
```

### Explicación para negocio (1 minuto)

```markdown
Qué pasa: <escena en lenguaje del cliente>.
Por qué pasa: <metáfora>.
Qué proponemos: <decisión en una línea>.
Qué cuesta: <tiempo/dinero/latencia>.
Qué evita: <riesgo cuantificado>.
```

## Referencias

- `references/catalogo-metaforas.md` — metáforas de los 48 videos, agrupadas por concepto, con el punto donde la analogía se rompe (léelo al buscar una analogía).
- `references/frases-guia.md` — frases memorables del canal parafraseadas como principios, útiles para cierres (léelo al redactar el cierre).
