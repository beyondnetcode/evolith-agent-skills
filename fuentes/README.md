# Fuentes

Registro del origen de todo el conocimiento de la biblioteca. Cada skill declara su fuente en `metadata.fuentes`; aquí se documenta cómo se obtuvo y con qué límites, para que cualquiera pueda auditarlo o actualizarlo.

| Fuente | Tipo | Skills que alimenta | Fecha de análisis | Detalle |
|---|---|---|---|---|
| TheDebugDuck (YouTube, 48 videos largos) | Casos de producción explicados con metáforas | todas las actuales | 2026-09-28 | [thedebugduck/](thedebugduck/README.md) |

## Reglas para añadir una fuente

1. Crea `fuentes/<fuente>/README.md` con: qué es, enlace, método de extracción, cobertura (qué partes alimentan qué skills), límites conocidos y fecha.
2. El contenido de las skills se **parafrasea**; no se copian textos, transcripciones ni código protegidos. Como máximo una cita breve atribuida.
3. Lo que se añade o corrige respecto de la fuente se marca «(complemento)» en la referencia correspondiente.
4. Añade la fila a esta tabla.
