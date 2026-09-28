# evolith-agent-skills

Biblioteca de **skills y agentes reutilizables** para trabajar con IA en cualquier proyecto. Cada skill es conocimiento accionable (método, matrices de decisión, preguntas de revisión, formato de salida) en Markdown plano con frontmatter estándar, así que la puede leer **cualquier LLM o agente**: Claude Code, Codex, Copilot, Cursor, Gemini o un chat al que le adjuntes los archivos.

## Estructura

```text
evolith-agent-skills/
├── AGENTS.md              # protocolo para agentes: descubrir, elegir y aplicar skills
├── CLAUDE.md              # importa AGENTS.md para Claude Code
├── llms.txt               # índice para LLMs (generado)
├── catalog.json           # índice para máquinas (generado)
├── skills/
│   ├── categorias.json    # taxonomía (fuente de verdad)
│   ├── README.md          # catálogo por categoría (generado)
│   └── <categoria>/<skill>/
│       ├── SKILL.md       # frontmatter + instrucciones
│       ├── references/    # detalle bajo demanda
│       └── scripts/       # herramientas deterministas
├── agents/                # roles que combinan skills (p. ej. arquitecto)
├── docs/                  # integración por herramienta y estándar de autoría
├── plantillas/            # plantillas de skill y agente
├── fuentes/               # origen y trazabilidad del conocimiento
├── scripts/               # build_catalog.py (valida y genera índices) e instalar_skills.py
├── tests/                 # pruebas de los scripts (unittest)
└── .claude-plugin/        # empaquetado como plugin de Claude Code
```

## Catálogo

Ver [`skills/README.md`](skills/README.md) (generado). Hoy: 10 skills en 8 categorías y el agente [`arquitecto`](agents/arquitecto.md), destilados de los 48 videos del canal TheDebugDuck ([fuente](fuentes/thedebugduck/README.md)).

| Categoría | Skills |
|---|---|
| Arquitectura | `radar-arquitectura` (entrada), `estilos-arquitectonicos`, `consistencia-distribuida` |
| Datos | `datos-persistencia` |
| Operación | `resiliencia-operacion` |
| APIs y contratos | `contratos-api` |
| Seguridad | `seguridad-aplicaciones` |
| Código | `diseno-de-codigo` |
| IA | `sistemas-con-ia` |
| Comunicación | `comunicar-decisiones` |

## Uso rápido

- **Claude Code:** instala el repo como plugin o enlaza las skills; ver [`docs/integracion.md`](docs/integracion.md).
- **Otros agentes (Codex, Copilot, Cursor, Gemini…):** apunta el agente a [`AGENTS.md`](AGENTS.md) o copia/enlaza las carpetas de skills en la ruta que su herramienta lea; ver [`docs/integracion.md`](docs/integracion.md).
- **Chat sin herramientas:** adjunta el `SKILL.md` de la skill (y las referencias que indique) y pide que lo aplique.

Escáner de riesgos de arquitectura sobre cualquier repositorio (Python estándar):

```bash
python3 skills/arquitectura/radar-arquitectura/scripts/escanear_senales.py <ruta-del-repo>
```

## Añadir o cambiar skills

1. Sigue [`docs/estandar-de-skills.md`](docs/estandar-de-skills.md) y parte de [`plantillas/`](plantillas/SKILL.template.md).
2. Registra el origen en [`fuentes/`](fuentes/README.md).
3. Valida, regenera índices y prueba:

   ```bash
   python3 scripts/build_catalog.py
   ```

   ```bash
   python3 -m unittest discover -s tests
   ```

## Licencia

[MIT](LICENSE) © 2026 BeyondNet Tech.
