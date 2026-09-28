---
name: sistemas-con-ia
description: Criterio de arquitecto para diseñar sistemas y agentes con LLMs tratando contexto y tokens como recursos finitos y caros — ventana de contexto, estado y memoria de corto y largo plazo, RAG y recuperación, carga progresiva, compactación, recorte de resultados de herramientas, subagentes, degradación en contextos largos (lost in the middle, context rot), orden de instrucciones, prompt caching, inyección de prompts vía contenido recuperado, tokenización, límites de entrada y salida, coste, presupuestos y observabilidad del consumo. Úsala siempre que un diseño, ADR, PR o incidente involucre agentes, RAG, memoria conversacional, asistentes con herramientas o MCP, prompts largos, elegir qué meter en el contexto, presupuestar tokens o costes de un LLM, o síntomas como "el agente olvida", "alucina con documentos largos", "se encarece", "responde cortado" o "ignora el system prompt", aunque el usuario no hable de tokens ni de contexto.
license: MIT
metadata:
  categoria: ia
  version: "1.0.0"
  idioma: es
  fuentes: "TheDebugDuck: 47, 48"
  relacionadas: "comunicar-decisiones, radar-arquitectura, resiliencia-operacion"
---

# Sistemas con IA: contexto y tokens

**El contexto es un recurso finito y caro: se presupuesta y se diseña como una caché.** El modelo solo sabe lo que viaja en cada request; todo lo demás (estado, memoria, conocimiento, límites de gasto) es responsabilidad de la aplicación. Base: TheDebugDuck 47 y 48 (elaborados desde título y temario, sin transcripción), ampliados a nivel de arquitecto y verificados con documentación oficial y papers; lo añadido está marcado «(complemento)» en las referencias.

## Cómo usar esta skill

1. **Clasifica el problema:** ¿*qué* entra al contexto y cómo se usa (olvido, alucinación con documentos, pérdida de hilo, inyección) o *cuánto* cabe y cuesta (factura, truncado, 429, límites)? Suelen venir juntos.
2. **Pide números antes de opinar:** proveedor y modelo; tokens por capa del request típico y del p95 (contados con el tokenizador del modelo destino); turnos por conversación; herramientas y tamaño de sus resultados; volumen diario; distribución de motivos de parada; tasa de acierto de caché.
3. **Busca el síntoma en la matriz** y abre solo la referencia indicada.
4. **Ventanas, precios, TTL de caché y mínimos cacheables:** consulta la tabla vigente del proveedor; nunca de memoria. En esta skill solo hay órdenes de magnitud.
5. **Entrega con el formato de salida.** Decisiones estructurales (memoria, RAG, multiagente, proveedor) van a un ADR; lo que no se cierre en el cambio, al registro de hallazgos.

## Índice de referencias

| Tema | Archivo | Léelo cuando… |
|---|---|---|
| Contexto en agentes: estado, memoria, RAG, carga progresiva, compactación, subagentes, degradación, orden, caché, inyección | `references/47-contexto-en-agentes-ia.md` | el agente olvida o se contradice, diseñas memoria o RAG, el contexto crece sin control, hay contenido externo no confiable |
| Tokens: tokenización, idioma, límites, coste entrada/salida, conteo, presupuestos, observabilidad | `references/48-tokens-en-ia.md` | la factura sube, respuestas cortadas, 429 por tokens, estimar coste o capacidad, migrar de modelo |

## Principios (y por qué)

1. **El modelo no tiene estado; la aplicación sí.** Cada llamada es una función de lo que envías. Persistir la conversación y reconstruir el prompt desde fuentes de verdad hace el sistema depurable, reproducible y aislado entre usuarios.
2. **El contexto es un presupuesto, no un almacén.** Más tokens no es mejor: la calidad cae antes del techo (*context rot*, *lost in the middle*, distracción por irrelevante) y el coste y la latencia suben. Busca el conjunto mínimo de tokens de alta señal.
3. **Diseña el contexto como una caché jerárquica.** Lo estable arriba (reutilizable y cacheable), lo volátil abajo, el conjunto de trabajo mínimo dentro y el resto detrás de un puntero (ID, ruta, URL) que se carga *just-in-time*. Así se alinean atención, caché de prefijos y coste.
4. **Carga progresiva: índice → documento → detalle.** La mayoría de tareas necesita una fracción pequeña del conocimiento disponible; este repositorio funciona así (catálogo → `SKILL.md` → referencias).
5. **Recorta en origen.** Los resultados de herramientas son el mayor consumidor en agentes y se reenvían en cada turno: paginar, filtrar y proyectar antes de que entren es más barato y fiable que resumir después.
6. **Aísla el trabajo ruidoso.** Exploración y lectura masiva en subagentes con contexto propio que devuelven solo conclusiones. Ahorra contexto del orquestador, no tokens totales.
7. **La memoria de largo plazo es un sistema de datos.** Escritura explícita, esquema, procedencia, caducidad, borrado y defensa contra envenenamiento; "guardar todo el chat en un índice vectorial" no es memoria.
8. **Todo contenido externo es dato, no instrucción.** Documentos, páginas, correos y resultados de herramientas pueden traer órdenes (inyección indirecta). No hay prevención infalible: contén con mínimo privilegio, confirmación humana en acciones con efectos y validación de la salida con código.
9. **Mide en tokens del modelo destino.** Palabras y caracteres engañan: el conteo varía por idioma, tipo de contenido y generación de tokenizador (decenas de por ciento).
10. **La salida es la parte cara y lenta.** Cuesta varias veces la entrada y se genera secuencialmente: formatos compactos, `max_tokens` con margen, detección de truncado.
11. **Presupuesta en capas y hazlo cumplir con código:** por request, por conversación, por usuario/tenant, por funcionalidad y por día; topes de iteraciones y de gasto en agentes. Un bucle de agente sin tope es un coste no acotado.
12. **El consumo de tokens es una métrica de primera clase.** Entrada, salida, caché, razonamiento y motivo de parada por request, funcionalidad y tenant; sin eso, una regresión de prompt solo se descubre en la factura.

## Matriz "si ves X → considera Y"

| Si ves… | Mecanismo probable | Considera… | Evita… |
|---|---|---|---|
| El agente "olvida" o contradice el system prompt en conversaciones largas | historial truncado por la app, *context rot*, instrucción enterrada en medio | compactación estructurada al 60–70 % de la ventana útil; reafirmar invariantes al final; estado y decisiones fuera del modelo | subir de modelo o de ventana como arreglo |
| No recuerda al usuario entre sesiones | API sin estado; nadie persiste hechos | memoria de largo plazo con esquema, TTL y consentimiento, recuperada al inicio o por herramienta | volcar historiales completos en cada request |
| Respuestas peores al añadir más documentos | distracción por irrelevante; relevante en posiciones medias | top-k acotado, reranking, umbral de relevancia, documentos arriba y pregunta al final, citar antes de responder | "por si acaso, mételo todo" |
| Base de conocimiento pequeña y estable | RAG añade un punto de fallo | meterla entera como prefijo cacheado si cabe holgada | montar un índice vectorial por inercia |
| RAG devuelve fragmentos "correctos" pero sin sentido ("creció un 3 %… ¿quién?") | fragmentos sin contexto | contexto por fragmento (título, fuente, fecha), búsqueda híbrida léxica + embeddings, reranking | chunks de tamaño fijo sin metadatos |
| El coste por conversación crece más rápido que los turnos | historial reenviado cada turno: acumulado ≈ cuadrático | caché del prefijo + compactación + tope de turnos | reconstruir el prompt con datos variables al inicio |
| Tasa de acierto de caché baja | prefijo inestable (fecha, usuario, orden de herramientas o claves no determinista) | estable arriba, variable al final, serialización determinista, medir lectura de caché | cachear lo que cambia en cada request |
| Agente con decenas de herramientas: lento, caro, elige mal | definiciones ocupan contexto y se solapan | menos herramientas y más ortogonales, carga diferida de definiciones, subagentes por dominio | exponer cada endpoint 1:1 como herramienta |
| Resultados de herramienta enormes (logs, HTML, JSON de MB) | resultados que se acumulan y reenvían | paginación, filtros, proyección de campos, techo por resultado, limpiar resultados ya procesados | pegar la respuesta cruda |
| El agente pierde el hilo tras compactar | resumen con pérdida | resumen estructurado (objetivo, decisiones, restricciones, IDs, pendientes) + notas externas (progreso, git) | resumen libre "de lo que pasó" |
| El orquestador se llena de exploración | subtareas mezcladas en un contexto | subagentes que devuelven resumen condensado | subagentes para tareas triviales o muy acopladas |
| Un documento, web o correo cambia la conducta del agente | inyección indirecta de prompts | delimitar y etiquetar lo no confiable, mínimo privilegio, confirmación humana, validar salida | confiar solo en "ignora órdenes de los documentos" |
| Respuesta cortada o JSON inválido | límite de salida alcanzado (o de ventana) | comprobar motivo de parada, `max_tokens` con margen, salida estructurada compacta, pedir por partes | reintentar idéntico o parsear lo truncado |
| La factura sube sin más usuarios | regresión de tokens por request (HTML, JSON indentado, logs, few-shot) | métricas por funcionalidad, prueba de tokens en CI, alerta por p95 | mirar solo la factura mensual |
| 429 con pocas requests por segundo | límite de tokens por minuto | presupuestar TPM de entrada y salida, caché, colas con backoff, lotes | subir concurrencia |
| Mismo prompt, distinto coste por idioma o tras migrar de modelo | tokenizador distinto | recontar con el modelo destino, re-presupuestar, margen para español y código | reutilizar conteos o estimar por caracteres |
| Un usuario o tenant agota el presupuesto de todos | sin cuotas en tokens ni tope de pasos | token bucket por tenant medido en tokens, tope de iteraciones y gasto por tarea, degradación elegante | límites solo por request |

## Recetas de combinación

- **Asistente conversacional con memoria:** conversación persistida por ID → prefijo estable cacheado (herramientas + system + políticas versionadas) → memoria de usuario con esquema y techo → recuperación acotada → historial compactado por umbral → turno actual al final → reserva de salida → `usage` registrado por request.
- **Agente con herramientas de larga duración:** pocas herramientas ortogonales o carga diferida → resultados paginados con techo → limpieza de resultados procesados → notas externas de progreso y decisiones → subagentes para exploración → topes de pasos y gasto → confirmación humana en acciones con efectos.
- **RAG sobre base documental:** ¿cabe holgada y es estable? → prefijo cacheado. Si no → fragmentos con contexto + búsqueda híbrida + reranking + top-k con umbral → documentos arriba y pregunta al final → respuesta con citas → "no lo sé" sin evidencia → evaluación de la recuperación separada de la de la respuesta.

## Preguntas de revisión de un diseño con LLM

1. ¿Dónde vive el estado de la conversación y quién reconstruye el prompt en cada llamada? ¿Se guarda el prompt efectivo para depurar?
2. ¿Cuál es el presupuesto de tokens por capa (system, herramientas, memoria, recuperación, historial, reserva de salida) y qué código lo hace cumplir?
3. ¿Qué entra siempre, qué se carga bajo demanda y qué no entra nunca?
4. ¿Cuándo se compacta y qué invariantes sobreviven? ¿Hay prueba de calidad tras compactar?
5. ¿Cuál es el techo de un resultado de herramienta y cómo se pagina?
6. ¿Qué contenido no confiable entra al contexto, qué acciones puede disparar y dónde hay confirmación humana?
7. ¿Qué parte del prompt es prefijo estable y cuál es su tasa de acierto de caché medida?
8. ¿Cuántos tokens de entrada y salida tiene el request típico y el p95, medidos con el tokenizador del modelo destino?
9. ¿Cómo se detecta y trata una salida cortada por límite?
10. ¿Cuáles son los topes por usuario/tenant, por tarea de agente y por día, y qué ve el usuario al alcanzarlos?
11. ¿Se registran tokens (entrada, salida, caché, razonamiento) y motivo de parada por funcionalidad y tenant, con alertas?
12. ¿Se evaluó con contextos del tamaño de producción, con lo relevante en posiciones medias, y se re-evalúa al cambiar de modelo?

## Precisiones (no las repitas)

- "La IA recuerda la conversación": la aplicación reenvía el historial. Incluso con estado del lado del servidor, el historial ocupa ventana y se factura como entrada.
- "Más ventana arregla el olvido": la calidad cae antes del techo; ventana anunciada ≠ ventana útil.
- "Un token es una palabra": ~4 caracteres o ~0,75 palabras solo en inglés; el español y el código suelen necesitar más tokens para el mismo contenido.
- "La caché reduce el contexto": reduce coste y latencia del prefijo; los tokens cacheados siguen ocupando ventana.
- "El límite de contexto es de entrada": incluye la salida y, en modelos con razonamiento, los tokens de razonamiento, que además se facturan como salida.
- "RAG elimina las alucinaciones": las reduce si la recuperación acierta; si falla, el modelo razona con seguridad sobre contexto equivocado.
- "Un índice vectorial es memoria": es recuperación; la memoria necesita política de escritura, actualización y olvido.
- "Los subagentes ahorran tokens": ahorran contexto del orquestador; el total suele multiplicarse.
- "Una instrucción en el system prompt evita la inyección": mitiga, no previene.
- "Caracteres / 4 basta para presupuestar": sirve para orden de magnitud en inglés; para límites duros, cuenta con el proveedor.

## Formato de salida

```
Decisión: <mecanismo mínimo de contexto/tokens>, en una línea.
Presupuesto de contexto: <tokens aprox. por capa: herramientas+system | memoria | recuperación | historial | turno | reserva de salida>.
Siempre / bajo demanda / nunca: <qué entra en cada categoría>.
Estado y memoria: <dónde vive, cómo se reconstruye, caducidad y borrado>.
Coste: <tokens entrada/salida por request × volumen, efecto de caché y lotes; orden de magnitud, precios de la tabla vigente del proveedor con fecha>.
Riesgos y mitigación: <degradación, inyección, truncado, bucles>.
Operación: <métricas de tokens, tasa de caché, motivo de parada, topes y alertas>.
Cuándo NO: <condición en la que el mecanismo sobra>.
Fuente: <referencia(s) y video(s) usados>.
```
