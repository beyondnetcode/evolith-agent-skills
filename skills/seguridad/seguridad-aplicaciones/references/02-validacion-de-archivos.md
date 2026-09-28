# [02] Crees que sabes validar archivos hasta que te pasa esto

> Fuente: TheDebugDuck — https://youtu.be/olhSxQL8GYc · notas parafraseadas; «(complemento)» = conocimiento añadido o corrección.

- **Síntoma en producción:** una funcionalidad "simple" de carga de evidencias de siniestros (aseguradora: foto del daño, PDF de denuncia, cotización del taller) pasa demo, tests y code review. Meses después un funcionario interno abre una "foto" desde el tablero y el navegador ejecuta un script con la sesión corporativa (XSS almacenado), o un PDF lo lleva a un login falso. No hay error visible en el backend: la vulnerabilidad queda persistida en el bucket esperando a un usuario interno.
- **Causa raíz (mecanismo):** todas las validaciones iniciales confían en **metadatos declarados por el cliente**, no en el contenido:
  - `accept` del `<input type=file>` es solo una sugerencia de UX en el navegador; no viaja al servidor y se evita con Postman/curl.
  - `originalname` (extensión) es una cadena arbitraria controlada por quien envía.
  - `mimetype`/`Content-Type` de la parte multipart lo fija el SO del cliente según la extensión o lo escribe a mano el atacante; Multer (y similares) solo lo copian, no inspeccionan bytes.
  - El límite de tamaño (5 MB) frena DoS de almacenamiento pero no un HTML/SVG malicioso de pocos KB.
  - El antivirus del correo no ve cargas que van API → bucket; y un AV tradicional busca malware conocido, no contenido web válido (SVG con `<script>`, HTML con formulario falso).
  - Al servir el archivo, el backend reutiliza el `Content-Type` que declaró el cliente → el navegador interpreta el contenido como activo.
- **Metáfora visual del video:** bolsa de evidencias/paquete: fiarse de la etiqueta pegada por fuera en vez de abrir el empaque y mirar el contenido.
- **Estrategias / solución:**
  1. Mantener `accept` solo como ayuda de UX.
  2. Límite de tamaño + allowlist explícita (necesarios, no suficientes).
  3. **Magic bytes**: leer los primeros bytes del buffer y compararlos contra firmas (como el comando `file`/libmagic). JPG `FF D8 FF`, PNG `89 50 4E 47 0D 0A 1A 0A`, PDF `%PDF-`, XLSX = contenedor ZIP `PK 03 04` (firmas concretas: complemento). Si no coincide → rechazar y **no almacenar nada**.
  4. El `Content-Type` de respuesta lo decide el backend a partir del tipo detectado, nunca el cliente.
  5. Entregar formatos complejos con `Content-Disposition: attachment` (forzar descarga, no render en el panel interno).
  6. Si hay procesamiento (miniatura, recorte): decodificar con librería real; si falla el decode, el archivo estaba corrupto/alterado.
  7. Formatos de riesgo (Excel, PDF): no previsualizar en navegador ni ejecutar en servidor; pedir formatos más seguros o extraer solo los datos necesarios.
  - Pseudocódigo (reescrito):
    ```
    upload(file):
      if file.size > MAX_BYTES → 413
      kind = detectSignature(readHead(file.buffer))      # libmagic / file-type
      if kind ∉ {jpeg, png, pdf} → 415 (no se persiste)
      if kind ∈ imágenes → reencode(decode(file))         # falla ⇒ rechazar
      key = uuid() + extFrom(kind)                        # (complemento) nunca el nombre original
      store(key, contentType = mimeFrom(kind))
    serve(key):
      Content-Type: <tipo detectado>; X-Content-Type-Options: nosniff (complemento)
      Content-Disposition: attachment (formatos complejos)
    ```
  - (complemento) Servir contenido de usuarios desde un **dominio sandbox separado** (sin cookies de sesión corporativa) y/o `Content-Security-Policy: sandbox`; re-codificar imágenes elimina payloads embebidos; para subida directa con URL prefirmada a S3, el backend no ve el archivo → usar bucket de cuarentena + escaneo asíncrono (disparado por evento) antes de publicar; CDR (Content Disarm & Reconstruction) para Office/PDF.
- **Trade-offs y cuándo NO aplicar:** magic bytes confirma **estructura, no seguridad**: XLSX con estructura válida puede traer lógica peligrosa; PDF válido puede tener acciones/enlaces externos (phishing); SVG/HTML no tienen firma fija corta; existen **políglotas** (válidos en dos formatos a la vez). La inspección de bytes es la primera barrera, no reemplaza cómo se procesa y sirve el archivo. Re-codificar cuesta CPU y puede degradar calidad/metadatos (EXIF, que además conviene eliminar por privacidad — complemento).
- **Heurísticas y umbrales:** límite de 5 MB por archivo en el caso; firmas en los primeros ~20 bytes (el video); (complemento) librerías como `file-type` leen hasta ~4 KB para algunos formatos. Regla: todo lo que viaja en la petición (nombre, extensión, MIME) lo define quien envía → tratarlo como no confiable.
- **Anti-patrones / señales de alerta:**
  - `originalname.endsWith('.jpg')` o `includes('.jpg')` como única validación.
  - `if (file.mimetype === 'image/jpeg')` en el middleware sin leer el buffer.
  - Guardar con el nombre original o servir con el `Content-Type` recibido.
  - Previsualizar archivos de usuario en `<iframe>`/`<object>` dentro del panel interno.
  - "Lo pasa el antivirus" como control único.
  - Código de carga generado por IA con el prompt genérico "ruta para subir imágenes y PDFs": suele traer exactamente `accept` + check de MIME + extensión y pasar los tests con el formulario del navegador.
- **Preguntas de revisión arquitectónica:**
  1. ¿Dónde se inspecciona el **contenido** (bytes) y con qué librería de firmas?
  2. ¿Quién decide el `Content-Type` con el que se sirve el archivo y se envía `nosniff`?
  3. ¿Quién abre estos archivos después (humanos internos, talleres, otros sistemas) y con qué privilegios de sesión?
  4. ¿Qué formatos necesita realmente el negocio y cuáles pueden sustituirse por uno más seguro o por datos estructurados?
  5. Si la carga va directa al almacenamiento (URL prefirmada), ¿qué control existe entre la subida y la publicación?
  6. ¿Hay tests que atacan la API directamente (curl) con MIME/extensión falsificados y políglotas?
- **Caso real / empresa citada:** caso hipotético de aseguradora (evidencias de siniestros). Herramientas citadas: Multer, comando `file` de Linux, Postman/curl.
- **Precisión técnica:**
  - El ejemplo `fotodaño.jpg.html` **no** pasa un `endsWith('.jpg')`; el bypass de doble extensión afecta a validaciones débiles (`includes`, `split('.')[1]`, regex sin ancla `$`) o a almacenamientos que infieren el tipo por la última extensión. El punto válido es que el nombre es controlado por el cliente. "Los navegadores leen la extensión desde la derecha" es impreciso: vía HTTP el navegador usa `Content-Type` (+ sniffing), no la extensión.
  - Un SVG dentro de `<img>` **no ejecuta scripts**; sí lo hace al abrirse directamente, en `<iframe>`, `<object>` o `<embed>`. El riesgo real es la navegación/embebido activo, no la etiqueta `<img>`.
  - Excel: `.xlsx` no contiene macros (eso es `.xlsm`); la firma ZIP la comparten DOCX, JAR, APK → hace falta inspección más profunda (`[Content_Types].xml`). Riesgos adicionales: zip bombs, XXE en parsers OOXML, inyección de fórmulas (complemento).
  - ASR: "memchen" = mimetype; "application/alpd" = application/pdf; "denuncia.pdf.bg, SBG" = denuncia.pdf.svg; "bocket" = bucket; "kiles" = KB.
