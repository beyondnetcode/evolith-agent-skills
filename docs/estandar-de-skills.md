# Estándar de skills

Cómo escribir una skill para que **cualquier LLM o agente** pueda descubrirla y aplicarla, y para que el validador la acepte. El formato sigue la especificación abierta *Agent Skills* (carpeta con `SKILL.md` + recursos opcionales), de modo que la misma carpeta funciona en Claude Code y en otras herramientas compatibles, y como Markdown plano en cualquier chat.

## 1. Ubicación y taxonomía

```text
skills/<categoria>/<nombre-skill>/
├── SKILL.md        # obligatorio: frontmatter + instrucciones
├── references/     # opcional: detalle que se carga bajo demanda
├── scripts/        # opcional: código ejecutable (preferir biblioteca estándar)
└── assets/         # opcional: plantillas o archivos que se copian a la salida
```

- `<categoria>` debe existir en [`skills/categorias.json`](../skills/categorias.json). Para crear una categoría nueva, añádela ahí con `id`, `nombre` y `descripcion`; el validador genera su hub.
- Una skill pertenece a **una** categoría: la del problema que resuelve, no la de la tecnología que usa.
- Crea una skill nueva cuando cambian el **disparador** (cuándo se usa) o el **formato de salida**; si solo cambia el detalle, es una referencia de una skill existente.

## 2. Frontmatter

```yaml
---
name: nombre-skill                 # kebab-case, ≤ 64, igual que la carpeta, único en el repo
description: Qué resuelve y cuándo usarla, incluidos los casos en que el usuario no nombra el tema. ≤ 1024 caracteres, una sola línea.
license: MIT
metadata:
  categoria: datos                 # igual que la carpeta padre
  version: "1.0.0"                 # semver: mayor = cambia el formato de salida o el alcance
  idioma: es
  fuentes: "Origen del conocimiento (ver fuentes/)"
  relacionadas: "otra-skill, otra-mas"   # opcional; deben existir
---
```

El validador usa un subconjunto simple de YAML: escalares en una línea y un mapa `metadata` con valores de texto. No uses bloques multilínea (`>` o `|`).

### Cómo escribir la `description`

Es el **único** texto que el agente ve antes de decidir si usa la skill, así que carga el peso del disparo:

- Primera frase: qué resuelve, con los términos que aparecerían en la tarea (patrones, síntomas, tecnologías).
- Segunda frase: "Úsala siempre que…", con situaciones concretas y la aclaración "aunque el usuario no nombre el patrón". Los agentes tienden a no usar skills; una descripción algo insistente compensa.
- No repitas el cuerpo: nada de instrucciones aquí.

## 3. Cuerpo del SKILL.md

Objetivo: < 500 líneas. Secciones recomendadas (en este orden):

1. **Título y tesis**: una o dos líneas con la idea central y por qué importa.
2. **Cómo usar esta skill**: pasos para aplicarla (qué datos pedir, qué leer, qué entregar).
3. **Índice de referencias**: tabla `Tema | Archivo | Léelo cuando…`. Todo archivo de `references/`, `scripts/` o `assets/` debe estar citado aquí o en el cuerpo (el validador rechaza huérfanos y enlaces rotos).
4. **Principios**: reglas con su **porqué**. Explicar la razón generaliza mejor que un "SIEMPRE" en mayúsculas.
5. **Matriz "si ves X → considera Y"**: el conocimiento accionable.
6. **Preguntas de revisión**: respondibles con evidencia.
7. **Precisiones**: simplificaciones frecuentes que el agente no debe repetir.
8. **Formato de salida**: plantilla exacta de lo que se entrega.

Estilo: imperativo, denso, sin relleno; números concretos en lugar de adjetivos; lo que no está en la fuente y se añade se marca «(complemento)».

## 4. Referencias

- Un archivo por tema, nombrado `NN-tema.md` cuando proviene de una fuente numerada.
- Encabezado con la fuente y su enlace. Contenido parafraseado: no se reproducen transcripciones ni textos protegidos; como máximo una cita breve (< 15 palabras) atribuida.
- Si supera ~300 líneas, añade una tabla de contenidos al inicio.

## 5. Scripts

- Deterministas, sin dependencias externas si es posible, con `--help` y salida en texto o Markdown.
- Deben explicar sus límites (p. ej. "señales heurísticas, no veredictos").
- Se prueban con casos positivos **y** negativos antes de publicarlos.

## 6. Agentes

Un agente en `agents/<nombre>.md` es un rol que combina skills. Frontmatter: `name` (= nombre del archivo), `description`, `tools` (opcional) y `skills` (lista YAML de nombres existentes). El cuerpo define método de trabajo y estilo, no conocimiento: el conocimiento vive en las skills. Plantilla: [`plantillas/AGENT.template.md`](../plantillas/AGENT.template.md).

## 7. Validación y publicación

```bash
python3 scripts/build_catalog.py          # valida y regenera índices
python3 scripts/build_catalog.py --check  # valida sin escribir (CI / pre-commit)
```

Comprueba: nombre y carpeta, longitud de la descripción, categoría, semver, relaciones, recursos citados y huérfanos, skills de cada agente y todos los enlaces Markdown relativos del repositorio. Sube `metadata.version` al cambiar una skill y registra el origen en [`fuentes/`](../fuentes/README.md).
