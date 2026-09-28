# AGENTS.md — Protocolo para agentes y LLMs

Este repositorio es una **biblioteca de skills**: conocimiento y procedimientos reutilizables que cualquier LLM o agente de código puede leer y aplicar en cualquier proyecto. No contiene una aplicación. Todo está en Markdown plano con frontmatter YAML, sin dependencias de una herramienta concreta.

## 1. Descubrir

Usa el primer índice que tu entorno pueda leer:

| Índice | Para qué |
|---|---|
| [`catalog.json`](catalog.json) | Máquinas: nombre, categoría, descripción, ruta, versión, recursos y relaciones de cada skill y agente |
| [`llms.txt`](llms.txt) | LLMs: lista enlazada y resumida por categoría |
| [`skills/README.md`](skills/README.md) | Personas y agentes: catálogo navegable por categoría |

Cada skill vive en `skills/<categoria>/<nombre>/SKILL.md`. Los agentes (roles que combinan skills) viven en `agents/`.

## 2. Elegir

- Compara la tarea con el campo `description` de cada skill: dice **qué resuelve y cuándo usarla**, incluidos casos en que el usuario no nombra el tema.
- Si la tarea es un diagnóstico o una revisión de arquitectura y no sabes por dónde empezar, empieza por [`radar-arquitectura`](skills/arquitectura/radar-arquitectura/SKILL.md): enruta a la skill especializada.
- Varias skills pueden aplicar a la vez; `metadata.relacionadas` indica combinaciones habituales.

## 3. Aplicar (carga progresiva)

1. Lee el `SKILL.md` elegido **completo**: contiene el método, las matrices de decisión, las preguntas de revisión y el formato de salida.
2. Abre **solo** los archivos de `references/` que el `SKILL.md` indique para el caso concreto. Son detallados; cargarlos todos desperdicia contexto.
3. Si la skill trae `scripts/`, ejecútalos en lugar de reimplementarlos (Python estándar, sin dependencias). Sus resultados son señales que se confirman leyendo el código.
4. Entrega usando el **formato de salida** de la skill.

## 4. Reglas de uso

- **Precedencia:** las instrucciones del usuario y las reglas del proyecto donde trabajas (ADRs aceptados, stack autorizado, guías de estilo) prevalecen sobre una skill. Una skill aporta criterio; no autoriza tecnología ni decisiones por sí sola.
- **Evidencia antes que afirmación:** cita archivo:línea, métrica o consulta. Lo que no puedas comprobar va como pregunta abierta.
- **Precisión técnica:** las skills marcan con «(complemento)» el conocimiento añadido o corregido respecto de la fuente y enumeran simplificaciones que no deben repetirse. Respétalas.
- **Idioma:** el contenido está en español; responde en el idioma del usuario.

## 5. Si vas a modificar este repositorio

- Sigue [`docs/estandar-de-skills.md`](docs/estandar-de-skills.md) y parte de [`plantillas/SKILL.template.md`](plantillas/SKILL.template.md).
- `catalog.json`, `llms.txt`, `skills/README.md` y `skills/<categoria>/README.md` **se generan**: no los edites a mano.
- Después de cualquier cambio ejecuta y deja en verde:

  ```bash
  python3 scripts/build_catalog.py
  ```

  En CI o antes de un commit: `python3 scripts/build_catalog.py --check` y, si tocaste scripts, `python3 -m unittest discover -s tests`.
- Registra el origen de todo conocimiento nuevo en [`fuentes/`](fuentes/README.md).
