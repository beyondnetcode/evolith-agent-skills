#!/usr/bin/env python3
"""Expone las skills de esta biblioteca a cualquier herramienta de IA.

El repositorio guarda las skills por categoría (skills/<categoria>/<skill>/), pero
la mayoría de herramientas solo descubre un nivel (<ruta>/<skill>/SKILL.md). Este
script crea enlaces simbólicos (o copias) planas en la ruta que cada herramienta lee.
Los nombres de skill son únicos en todo el repo (lo garantiza build_catalog.py),
así que aplanar es seguro.

Ejemplos:
  # Recomendado: cubre Codex, Copilot, Cursor, Gemini CLI y OpenCode (usuario)
  python3 scripts/instalar_skills.py --herramienta agents
  # Claude Code (usuario) + agentes en ~/.claude/agents
  python3 scripts/instalar_skills.py --herramienta claude --agentes
  # Solo en un proyecto concreto, copiando en vez de enlazar
  python3 scripts/instalar_skills.py --herramienta agents --proyecto ~/code/mi-app --copiar
  # Una categoría o skills concretas, simulando
  python3 scripts/instalar_skills.py --herramienta claude --categorias datos,operacion --dry-run
  # Ruta arbitraria
  python3 scripts/instalar_skills.py --destino /ruta/a/skills
  # Quitar lo instalado por este script
  python3 scripts/instalar_skills.py --herramienta agents --desinstalar

Solo biblioteca estándar.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
MARCA = ".evolith-skill"  # archivo testigo dentro de las copias

# herramienta -> (ruta de usuario, ruta relativa en un proyecto)
RUTAS = {
    "agents":   ("~/.agents/skills",           ".agents/skills"),   # Codex, Copilot, Cursor, Gemini CLI, OpenCode
    "claude":   ("~/.claude/skills",           ".claude/skills"),   # Claude Code (también Copilot/VS Code, Cursor, OpenCode)
    "copilot":  ("~/.copilot/skills",          ".github/skills"),
    "cursor":   ("~/.cursor/skills",           ".cursor/skills"),
    "gemini":   ("~/.gemini/skills",           ".gemini/skills"),
    "opencode": ("~/.config/opencode/skills",  ".opencode/skills"),
    "codex":    ("~/.agents/skills",           ".agents/skills"),
}


def skills_disponibles(categorias: set[str], nombres: set[str]) -> list[Path]:
    todas = sorted(p.parent for p in (RAIZ / "skills").glob("*/*/SKILL.md"))
    return [s for s in todas
            if (not categorias or s.parent.name in categorias) and (not nombres or s.name in nombres)]


def es_nuestra(destino: Path) -> bool:
    if destino.is_symlink():
        try:
            return RAIZ in destino.resolve().parents
        except OSError:
            return False
    return (destino / MARCA).exists()


def instalar(origen: Path, destino: Path, copiar: bool, dry: bool) -> str:
    if destino.exists() or destino.is_symlink():
        if not es_nuestra(destino):
            return f"OMITIDA  {destino} (ya existe y no la instaló este script)"
        if not dry:
            destino.unlink() if destino.is_symlink() else shutil.rmtree(destino)
    if dry:
        return f"{'copiaría' if copiar else 'enlazaría'} {destino} → {origen}"
    destino.parent.mkdir(parents=True, exist_ok=True)
    if copiar:
        shutil.copytree(origen, destino)
        (destino / MARCA).write_text(str(origen) + "\n")
    else:
        destino.symlink_to(origen, target_is_directory=True)
    return f"OK       {destino} → {origen}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--herramienta", choices=sorted(RUTAS))
    g.add_argument("--destino", help="carpeta destino arbitraria")
    ap.add_argument("--proyecto", help="instala en <proyecto>/<ruta de la herramienta> en vez de en el usuario")
    ap.add_argument("--categorias", default="", help="ids separados por coma (por defecto, todas)")
    ap.add_argument("--skills", default="", help="nombres separados por coma (por defecto, todas)")
    ap.add_argument("--copiar", action="store_true", help="copiar en lugar de enlazar (p. ej. para commitear en otro repo)")
    ap.add_argument("--agentes", action="store_true", help="con --herramienta claude: enlaza también agents/*.md en ~/.claude/agents")
    ap.add_argument("--desinstalar", action="store_true", help="elimina lo instalado por este script en el destino")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    if a.destino:
        base = Path(a.destino).expanduser()
    else:
        usuario, proyecto = RUTAS[a.herramienta]
        base = (Path(a.proyecto).expanduser() / proyecto) if a.proyecto else Path(usuario).expanduser()

    cats = {c.strip() for c in a.categorias.split(",") if c.strip()}
    noms = {n.strip() for n in a.skills.split(",") if n.strip()}
    seleccion = skills_disponibles(cats, noms)
    if not seleccion:
        print("No hay skills que coincidan con el filtro.")
        return 1

    print(f"Destino: {base}\n")
    for s in seleccion:
        d = base / s.name
        if a.desinstalar:
            if (d.exists() or d.is_symlink()) and es_nuestra(d):
                if not a.dry_run:
                    d.unlink() if d.is_symlink() else shutil.rmtree(d)
                print(f"{'quitaría' if a.dry_run else 'QUITADA '} {d}")
        else:
            print(instalar(s, d, a.copiar, a.dry_run))

    if a.agentes:
        if a.herramienta != "claude":
            print("\n--agentes solo aplica a --herramienta claude (formato de subagentes de Claude Code).")
        else:
            dest_ag = (Path(a.proyecto).expanduser() / ".claude/agents") if a.proyecto else Path("~/.claude/agents").expanduser()
            for ag in sorted((RAIZ / "agents").glob("*.md")):
                d = dest_ag / ag.name
                if a.desinstalar:
                    if d.is_symlink() and es_nuestra(d):
                        if not a.dry_run:
                            d.unlink()
                        print(f"{'quitaría' if a.dry_run else 'QUITADO '} {d}")
                    continue
                if d.exists() and not (d.is_symlink() and es_nuestra(d)):
                    print(f"OMITIDO  {d} (ya existe)")
                    continue
                if a.dry_run:
                    print(f"enlazaría {d} → {ag}")
                    continue
                dest_ag.mkdir(parents=True, exist_ok=True)
                if d.is_symlink():
                    d.unlink()
                d.symlink_to(ag)
                print(f"OK       {d} → {ag}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
