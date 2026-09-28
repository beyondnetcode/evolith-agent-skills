# [48] ¿Qué son los tokens en IA?

> Fuente: TheDebugDuck — https://youtu.be/NYRsNFvHciI · notas parafraseadas; «(complemento)» = conocimiento añadido o corrección.
> Estado: elaborado a partir del título y el temario público del video; la transcripción no estuvo disponible (bloqueo de YouTube, 2026-09-28). Lo que no figura en el temario es «(complemento)». Pendiente de contrastar con la transcripción.

- **Temario público (lo único tomado de la fuente):** qué es un token; cómo la IA divide el texto; por qué los tokens no son palabras; relación con el costo y el uso; mejorar prompts entendiendo los tokens.
- **Síntoma en producción (escenario ilustrativo, complemento):** la factura del LLM se triplica en un mes con los mismos usuarios. Un PR "inofensivo" empezó a pasar como contexto el HTML completo de la ficha de producto y el JSON indentado de la API interna. Las respuestas largas salen cortadas con JSON inválido y el parser falla en silencio. El flujo en español cuesta más que el piloto en inglés. Tras migrar de modelo, el mismo prompt "pesa" más y aparecen 429 por tokens por minuto con pocas requests por segundo. Un solo cliente con un agente en bucle consume el presupuesto diario de todos.
- **Causa raíz (mecanismo):**
  - **Token = unidad del vocabulario del modelo, no palabra, sílaba ni carácter.** El tokenizador (BPE a nivel de bytes y alternativas como el modelo unigram, p. ej. vía SentencePiece) aprende de su corpus qué secuencias son frecuentes y las fusiona en un único token; lo raro se parte en varios. Ejemplo documentado por OpenAI: " tokenization" → " token" + "ization". El espacio inicial suele ir pegado al token y mayúsculas o variantes cuentan distinto (complemento en el detalle).
  - **La regla de bolsillo solo vale para inglés:** ~4 caracteres o ~0,75 palabras por token (OpenAI y Anthropic). Se desvían idiomas con menos peso en el corpus del tokenizador, el código (sangría, símbolos, identificadores), los números y el texto de alta entropía: UUIDs, hashes, base64, URLs con parámetros (complemento).
  - **Español:** Petrov et al. (NeurIPS 2023) midieron sobre FLORES-200 una prima de ~1,5× para español frente a inglés con el tokenizador de GPT-4 de entonces (cl100k_base). Tokenizadores posteriores la reducen, pero no la eliminan: mide con tu corpus (complemento).
  - **Cada modelo trae su tokenizador:** el mismo texto cambia de conteo entre proveedores y también entre generaciones del mismo proveedor (diferencias de decenas de por ciento son posibles). Al cambiar de modelo, vuelve a medir con su endpoint de conteo antes de reutilizar presupuestos (complemento).
  - **Todo lo que viaja cuenta:** system, historial, definiciones de herramientas (nombres, descripciones, esquemas JSON), resultados de herramientas, imágenes y PDF (convertidos a tokens según tamaño o páginas) y la salida. Los tokens de razonamiento se facturan como salida y ocupan ventana aunque no se muestren (complemento).
  - **Coste = entrada + salida, con precios distintos** (complemento en las proporciones):
    ```text
    coste ≈ entrada_sin_caché × p_in + caché_escritura × p_write + caché_lectura × p_read + salida × p_out
    ```
    La salida cuesta varias veces la entrada (entre ~4× y ~8× en las tablas públicas de los principales proveedores en 2026; lo más común, ~5×) y se genera token a token, así que la latencia crece con la longitud de la salida. La lectura de caché cuesta una fracción de la entrada (de ~0,5× en modelos antiguos a ~0,1× o menos en los recientes); los lotes asíncronos, del orden de la mitad. Consulta la tabla vigente del proveedor: precios y proporciones cambian.
  - **Tres límites distintos** (complemento): ventana de contexto (entrada + salida), máximo de salida por request (`max_tokens` o equivalente) y límites de uso en tokens por minuto (entrada y salida por separado), además de requests por minuto.
- **Metáfora propia (complemento):** *la imprenta de tipos móviles con bloques de sílabas.* La caja del tipógrafo tiene letras sueltas y, además, bloques prefundidos para los fragmentos más comunes del idioma para el que se diseñó (" the", "ing", "ción"). Para componer un texto usa un bloque grande cuando existe y letras sueltas cuando no. Pagas por pieza colocada; si además le pides que redacte (salida), cada pieza cuesta varias veces más y la compone de una en una. Un texto en otro idioma, un UUID o un JSON con sangría obligan a usar muchas piezas pequeñas. · *vocabulario aprendido por frecuencia; coste y límites por pieza* · ⚠️ Se rompe en tres puntos: BPE no busca la composición con menos piezas, aplica en orden las fusiones que aprendió; los bloques no son sílabas ni morfemas (frecuencia estadística, no lingüística); y cada modelo trae su propia caja, así que los conteos no se transfieren entre modelos.
- **Estrategias / solución:**
  1. **Contar antes de enviar** con el tokenizador o el endpoint del modelo destino (Anthropic ofrece un endpoint de conteo gratuito con rate limit propio; para modelos de OpenAI, `tiktoken`). El conteo previo es una estimación; la verdad es el campo `usage` de la respuesta (complemento).
     ```python
     n = contar_tokens(modelo, system, herramientas, mensajes)   # API o tokenizador del proveedor
     if n + reserva_salida > presupuesto_request:
         recortar_o_compactar()                                  # nunca enviar "a ver si cabe"
     ```
  2. **Presupuesto por request:** techo de entrada por funcionalidad, `max_tokens` explícito con margen, tope de iteraciones y de llamadas a herramientas por tarea de agente (complemento).
  3. **Presupuesto por usuario / tenant:** cubo de tokens (*token bucket*) medido en tokens, no en requests, por minuto y por día; 429 propio con `Retry-After` y degradación elegante (modelo menor, respuesta más corta, cola). Es rate limiting aplicado a tokens (ver `resiliencia-operacion`, video 38) (complemento).
  4. **Dieta de entrada** (el "mejorar prompts" del temario, llevado a producción): HTML → texto o Markdown limpio; JSON → solo los campos necesarios, sin sangría, o tabla/CSV para muchas filas homogéneas; logs → deduplicar, agrupar por firma de error, ventana temporal y nivel; IDs largos que el modelo no necesita → alias cortos que el código traduce de vuelta; few-shot → los mínimos que mueven la métrica (complemento en el detalle).
  5. **Dieta de salida:** formato compacto (salida estructurada con esquema, sin repetir la entrada), límites explícitos ("≤ 5 viñetas"), diffs en lugar de archivos completos; comprobar el motivo de parada (`stop_reason` / `finish_reason`) y no parsear una salida cortada por límite (complemento).
  6. **Caché de prompts:** prefijo estable (herramientas, system, documentos fijos) al principio y lo variable al final; medir la tasa de acierto (tokens leídos de caché / tokens de entrada). En al menos un proveedor, los tokens leídos de caché no cuentan para el rate limit de entrada (complemento).
  7. **Modelo adecuado por tarea:** router que manda lo simple a modelos pequeños; procesamiento por lotes para lo que no es interactivo (complemento).
  8. **Observabilidad del consumo:** por request, registrar modelo, tokens de entrada, salida, caché (lectura/escritura) y razonamiento, motivo de parada, latencia, funcionalidad y tenant. Las convenciones semánticas GenAI de OpenTelemetry (estado *Development*) nombran `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`, `gen_ai.usage.cache_read.input_tokens` y `gen_ai.response.finish_reasons`. Alertas por p95 de tokens por request y coste por funcionalidad y día; prueba de regresión de tokens en CI para las plantillas de prompt (complemento).
- **Trade-offs y cuándo NO aplicar:** comprimir de más (abreviaturas crípticas, quitar contexto útil) baja la calidad y provoca reintentos que cuestan más; el objetivo es quitar tokens *irrelevantes*, no tokens. Las claves cortas y los alias dificultan depurar. Un router de modelos exige evaluación continua. Contar por API añade una llamada y latencia: para orden de magnitud basta la heurística; para límites duros, cuenta. No optimices tokens en un prototipo de bajo volumen: mide primero y ataca donde volumen × tokens por request domina la factura (complemento).
- **Heurísticas y umbrales (complemento):**
  - Estimación rápida: caracteres / 4 en inglés; en español y en código, añade un margen del orden de 1,5× y valida con el tokenizador real.
  - Una página web media de ~10 kB ronda ~2 500 tokens y un PDF de investigación de ~500 kB, ~125 000 (ejemplos publicados por Anthropic para su herramienta de fetch): nunca "pegar la página" sin extraer lo pertinente.
  - Coste mensual ≈ requests/día × 30 × (tokens_entrada × p_in + tokens_salida × p_out); en conversaciones, el historial reenviado y la salida suelen dominar.
  - Reserva de salida explícita en cada request; con modelos de razonamiento, amplia (OpenAI recomienda empezar reservando al menos 25 000 tokens para razonamiento + salida al experimentar).
  - Alerta si cae la tasa de acierto de caché o si el p95 de tokens por request sube de forma sostenida tras un despliegue.
- **Anti-patrones / señales de alerta:** estimar por palabras o caracteres para límites duros; reutilizar conteos tras cambiar de modelo; JSON indentado, HTML crudo, logs completos o base64 dentro del texto; ejemplos few-shot que crecen sin control; `max_tokens` al máximo "por si acaso" o tan bajo que corta sin que nadie lo detecte; límites de uso solo en requests; no registrar `usage`; presupuesto global sin atribución por funcionalidad o tenant; fecha u hora al inicio del prompt; pedir en producción explicaciones o razonamiento visible que nadie lee (se paga como salida).
- **Preguntas de revisión arquitectónica:**
  1. ¿Cuántos tokens de entrada y de salida tiene el request típico y el p95, medidos con el tokenizador del modelo destino?
  2. ¿Qué capa domina (system, herramientas, historial, recuperación, resultados) y qué parte es irrelevante para la tarea?
  3. ¿Qué `max_tokens` se usa, cómo se detecta una salida cortada y qué hace el sistema entonces?
  4. ¿Cuál es el presupuesto por request, por conversación, por usuario/tenant y por día, y qué componente lo hace cumplir?
  5. ¿Qué tasa de acierto de caché tiene el prefijo y qué la invalida?
  6. ¿Se registran tokens (entrada, salida, caché, razonamiento) y motivo de parada por funcionalidad y tenant? ¿Qué alerta existe?
  7. ¿Qué pasa con coste, límites y ventana si cambia el modelo o el idioma de los usuarios?
  8. ¿Los límites de tokens por minuto del proveedor están modelados en la capacidad, las colas y el backoff?
- **Referencias:**
  - OpenAI — Key concepts (tokens): https://developers.openai.com/api/docs/concepts
  - OpenAI — tiktoken (BPE): https://github.com/openai/tiktoken
  - OpenAI Cookbook — How to count tokens with tiktoken: https://developers.openai.com/cookbook/examples/how_to_count_tokens_with_tiktoken
  - OpenAI — Reasoning models (tokens de razonamiento): https://developers.openai.com/api/docs/guides/reasoning
  - Anthropic — Token counting: https://platform.claude.com/docs/en/build-with-claude/token-counting
  - Anthropic — Pricing (proporciones, caché, lotes, tokens de herramientas): https://platform.claude.com/docs/en/about-claude/pricing
  - Anthropic — Prompt caching: https://platform.claude.com/docs/en/build-with-claude/prompt-caching
  - Anthropic — Context windows: https://platform.claude.com/docs/en/build-with-claude/context-windows
  - Sennrich et al., *Neural Machine Translation of Rare Words with Subword Units* (BPE), ACL 2016: https://arxiv.org/abs/1508.07909
  - Kudo y Richardson, *SentencePiece*, EMNLP 2018: https://arxiv.org/abs/1808.06226
  - Petrov et al., *Language Model Tokenizers Introduce Unfairness Between Languages*, NeurIPS 2023: https://arxiv.org/abs/2305.15425
  - OpenTelemetry — GenAI semantic conventions: https://github.com/open-telemetry/semantic-conventions-genai
- **Precisión técnica:**
  - "Un token es una palabra" o "una sílaba": no. Es un fragmento de frecuencia aprendida; ~0,75 palabras por token solo describe inglés (complemento).
  - Los modelos operan sobre tokens, no sobre letras: por eso fallan al contar caracteres de una palabra o al manipular dígitos que quedaron agrupados en un solo token (complemento).
  - La ventana incluye la salida; `max_tokens` limita la salida, no la entrada (complemento).
  - Los tokens de razonamiento se facturan como salida y ocupan ventana; la respuesta puede quedarse sin texto visible si el límite se agota razonando (OpenAI lo documenta) (complemento).
  - La caché abarata tokens, no los quita de la ventana; el conteo previo por API no aplica la caché (complemento).
  - El conteo por API es una estimación y puede incluir tokens que el proveedor añade y no factura (Anthropic) (complemento).
  - El formato de chat añade unos pocos tokens de estructura por mensaje (roles, delimitadores; el Cookbook de OpenAI usa 3 por mensaje en sus modelos): muchos mensajes cortos no son gratis (complemento).
  - Precios y tamaños de ventana no se memorizan ni se copian a un diseño: consulta la tabla vigente del proveedor y anota la fecha de la consulta (complemento).
