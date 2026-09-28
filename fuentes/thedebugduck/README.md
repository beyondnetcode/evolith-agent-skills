# TheDebugDuck

- **Canal:** <https://www.youtube.com/@TheDebug_Duck> — conceptos de desarrollo de software explicados con metáforas visuales y casos reales de producción (español).
- **Alcance analizado:** los 48 videos largos publicados hasta el 2026-09-28 (el conteo del canal incluye además shorts, que no se analizaron).
- **Catálogo de videos → skill:** [`radar-arquitectura/references/indice-videos.md`](../../skills/arquitectura/radar-arquitectura/references/indice-videos.md).

## Método de extracción

1. Transcripción automática (ASR) en español de cada video; los términos técnicos mal transcritos se corrigieron por contexto.
2. Análisis por lotes temáticos con una plantilla fija por video: síntoma en producción, causa raíz (mecanismo), metáfora, estrategias/solución, trade-offs y cuándo no aplicar, heurísticas y umbrales, anti-patrones, preguntas de revisión, caso real y **precisión técnica**.
3. Verificación técnica: las afirmaciones simplificadas, dependientes del motor o incorrectas se corrigieron con documentación y postmortems públicos, marcadas «(complemento)».
4. Síntesis transversal por dominio: principios, matrices "si ves X → considera Y" y recetas de combinación, integradas en cada `SKILL.md`.
5. Cada video quedó como una referencia (`references/NN-tema.md`) de la skill de su dominio, con enlace al original.

Herramienta para repetir la extracción: [`herramientas/descargar_transcripciones.py`](herramientas/descargar_transcripciones.py) con la lista [`herramientas/videos.tsv`](herramientas/videos.tsv). Las transcripciones no se versionan (son obra del autor); solo las notas parafraseadas.

## Cobertura

| Skill | Videos |
|---|---|
| [`datos-persistencia`](../../skills/datos/datos-persistencia/SKILL.md) | 01, 03, 06, 09, 13, 16, 17, 25, 36 |
| [`consistencia-distribuida`](../../skills/arquitectura/consistencia-distribuida/SKILL.md) | 11, 23, 24, 26, 27, 28, 29, 33, 34 |
| [`resiliencia-operacion`](../../skills/operacion/resiliencia-operacion/SKILL.md) | 04, 05, 10, 19, 20, 21, 30, 31, 38 |
| [`estilos-arquitectonicos`](../../skills/arquitectura/estilos-arquitectonicos/SKILL.md) | 08, 14, 15, 18, 22, 46 |
| [`contratos-api`](../../skills/apis/contratos-api/SKILL.md) | 32, 35, 37 |
| [`seguridad-aplicaciones`](../../skills/seguridad/seguridad-aplicaciones/SKILL.md) | 02, 12 |
| [`diseno-de-codigo`](../../skills/codigo/diseno-de-codigo/SKILL.md) | 07, 39, 40, 41, 42, 43, 44, 45 |
| [`sistemas-con-ia`](../../skills/ia/sistemas-con-ia/SKILL.md) | 47, 48 |
| [`comunicar-decisiones`](../../skills/comunicacion/comunicar-decisiones/SKILL.md) | estructura narrativa y metáforas de todos |
| [`radar-arquitectura`](../../skills/arquitectura/radar-arquitectura/SKILL.md) | índice de síntomas de todos |

## Límites conocidos

- **Videos 32–48 (17):** YouTube bloqueó por IP la descarga de sus transcripciones el 2026-09-28. Sus referencias se elaboraron desde el título y el temario público del video más conocimiento técnico verificado contra fuentes primarias (RFCs, documentación oficial), y cada una lo declara en su cabecera (`> Estado: …`). Al obtener las transcripciones, re-analízalas con el mismo método, reemplaza el estado y sube `metadata.version` de las skills afectadas. El índice de videos marca cada fila con **T** (transcripción) o **D** (descripción).
- La fuente son transcripciones automáticas: matices visuales (diagramas, código en pantalla) solo se capturan si se narran.
- Cifras de casos reales (Discord, WhatsApp, Instagram, Prime Video, Cloudflare, Stack Overflow, Knight Capital) se contrastaron con fuentes públicas; donde el video difiere, la referencia lo indica.
- El canal publica con frecuencia: para incorporar videos nuevos, repite el método y actualiza esta tabla, el índice de videos y las skills afectadas (subiendo `metadata.version`).
