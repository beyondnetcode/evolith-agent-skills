# Integración por herramienta

Las skills siguen la especificación abierta [Agent Skills](https://agentskills.io/specification): una carpeta con `SKILL.md` (frontmatter `name` + `description`) y recursos opcionales. La leen de forma nativa muchas herramientas; el resto puede usarlas como Markdown plano.

**Dato clave:** este repositorio guarda las skills por categoría (`skills/<categoria>/<skill>/`), pero la mayoría de herramientas solo descubre **un nivel** (`<ruta>/<skill>/SKILL.md`). Por eso se exponen con [`scripts/instalar_skills.py`](../scripts/instalar_skills.py), que crea enlaces simbólicos planos (o copias con `--copiar`) en la ruta de cada herramienta. Los nombres son únicos en todo el repo, así que aplanar no genera colisiones. Con enlaces, un `git pull` de este repo actualiza todas las herramientas a la vez.

## Recomendación

Dos destinos cubren prácticamente todo:

```bash
python3 scripts/instalar_skills.py --herramienta agents   # ~/.agents/skills
python3 scripts/instalar_skills.py --herramienta claude --agentes   # ~/.claude/skills y ~/.claude/agents
```

Para un proyecto concreto (y poder commitear las skills en él), usa `--proyecto <ruta>` y, si no quieres enlaces, `--copiar`.

## Tabla de rutas (verificadas el 2026-09-28)

| Herramienta | Usuario | Proyecto | ¿Lee subcarpetas de categoría? | Documentación |
|---|---|---|---|---|
| Claude Code | `~/.claude/skills` | `.claude/skills` | No documentado → usar instalador o plugin | [skills](https://code.claude.com/docs/en/skills) |
| OpenAI Codex | `~/.agents/skills` | `.agents/skills` (del cwd a la raíz del repo) | Sí (según su código fuente) | [skills](https://developers.openai.com/codex/skills) |
| GitHub Copilot (VS Code, CLI, cloud agent) | `~/.copilot/skills`, `~/.agents/skills` | `.github/skills`, `.claude/skills`, `.agents/skills` | Probablemente no | [agent skills](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills) |
| Cursor | `~/.cursor/skills`, `~/.agents/skills`, `~/.claude/skills` | `.cursor/skills`, `.agents/skills`, `.claude/skills` | Sí | [skills](https://cursor.com/docs/context/skills) |
| Gemini CLI | `~/.gemini/skills`, `~/.agents/skills` | `.gemini/skills`, `.agents/skills` | No | [skills](https://geminicli.com/docs/cli/skills/) |
| OpenCode | `~/.config/opencode/skills`, `~/.agents/skills`, `~/.claude/skills` | `.opencode/skills`, `.agents/skills`, `.claude/skills` | No | [skills](https://opencode.ai/docs/skills/) |

Otras herramientas con soporte declarado (Junie, Amp, Goose, Roo Code, Kiro, Factory, OpenHands, Letta…): ver [agentskills.io/clients](https://agentskills.io/clients). VS Code exige que `name` coincida con la carpeta; el validador de este repo lo garantiza.

## Claude Code

Tres opciones, de más a menos integrada:

1. **Plugin (recomendado para equipos).** El repo incluye `.claude-plugin/plugin.json` (con las rutas de cada categoría en `skills`) y `.claude-plugin/marketplace.json`:

   ```bash
   claude plugin marketplace add beyondnetcode/evolith-agent-skills
   claude plugin install evolith-skills@evolith
   ```

   Para probar desde una copia local sin instalar:

   ```bash
   claude --plugin-dir /ruta/a/evolith-agent-skills
   ```

   El agente [`arquitecto`](../agents/arquitecto.md) queda disponible y precarga sus skills (campo `skills:`).
2. **Enlaces en el usuario:** `python3 scripts/instalar_skills.py --herramienta claude --agentes`.
3. **Enlaces en un proyecto:** `--proyecto <ruta>` para `.claude/skills` y `.claude/agents` del proyecto.

Claude Code lee `AGENTS.md` solo si no hay `CLAUDE.md`, o si `CLAUDE.md` lo importa con `@AGENTS.md` (como hace este repo). En tus proyectos puedes añadir a su `CLAUDE.md` una línea que apunte a este `AGENTS.md` si quieres que el protocolo esté siempre presente.

## Codex, Copilot, Cursor, Gemini CLI, OpenCode

```bash
python3 scripts/instalar_skills.py --herramienta agents                 # usuario
python3 scripts/instalar_skills.py --herramienta agents --proyecto .    # proyecto actual
```

Todas ellas leen `.agents/skills`. Para rutas propias de cada una: `--herramienta copilot|cursor|gemini|opencode`. Estas herramientas también leen `AGENTS.md` del proyecto ([agents.md](https://agents.md/)); Gemini CLI necesita configurarlo en `context.fileName`.

## Chats y APIs sin sistema de skills

- **Chat (ChatGPT, Claude.ai, Gemini):** adjunta el `SKILL.md` de la skill y, si lo pide, las referencias concretas; indica "aplica esta skill a…". Para proyectos de chat con archivos persistentes, sube los `SKILL.md` más usados y [`llms.txt`](../llms.txt) como índice.
- **API / agentes propios:** carga [`catalog.json`](../catalog.json), muestra al modelo solo `name` + `description` de cada skill, y cuando elija una, inyecta su `SKILL.md` (y después las referencias que pida). Es el mismo patrón de carga progresiva que usan las herramientas nativas.

## Mantener actualizado

- Con enlaces simbólicos: `git pull` en este repo basta.
- Con copias: vuelve a ejecutar el instalador con `--copiar` (reemplaza solo lo que instaló él; nunca toca skills ajenas).
- Para retirar: añade `--desinstalar` con los mismos parámetros.
