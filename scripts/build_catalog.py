#!/usr/bin/env python3
"""Valida la biblioteca de skills y genera sus índices.

Fuente de verdad: el frontmatter de cada skills/<categoria>/<skill>/SKILL.md,
skills/categorias.json y el frontmatter de agents/*.md.

Genera (no editar a mano):
  - catalog.json               índice legible por máquinas
  - llms.txt                   índice para LLMs (formato llms.txt)
  - skills/README.md           catálogo por categoría
  - skills/<categoria>/README.md  hub de cada categoría

Uso:
  python3 scripts/build_catalog.py           # valida y regenera
  python3 scripts/build_catalog.py --check   # valida y falla si algo generado está desactualizado (CI)

Solo biblioteca estándar.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SKILLS = RAIZ / "skills"
AGENTES = RAIZ / "agents"
NOMBRE_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
AVISO = "<!-- Generado por scripts/build_catalog.py a partir del frontmatter. No editar a mano. -->"

errores: list[str] = []
avisos: list[str] = []


def err(msg: str) -> None:
    errores.append(msg)


def leer_frontmatter(ruta: Path) -> tuple[dict, str]:
    """Parser mínimo del subconjunto YAML usado aquí: escalares, un mapa anidado y listas simples."""
    texto = ruta.read_text(encoding="utf-8")
    if not texto.startswith("---\n"):
        err(f"{rel(ruta)}: falta frontmatter YAML al inicio")
        return {}, texto
    fin = texto.find("\n---", 4)
    if fin == -1:
        err(f"{rel(ruta)}: frontmatter sin cierre '---'")
        return {}, texto
    bloque, cuerpo = texto[4:fin], texto[fin + 4:].lstrip("\n")
    datos: dict = {}
    clave_actual = None
    for linea in bloque.splitlines():
        if not linea.strip() or linea.lstrip().startswith("#"):
            continue
        if linea.startswith("  ") and clave_actual:
            item = linea.strip()
            if item.startswith("- "):
                if not isinstance(datos[clave_actual], list):
                    datos[clave_actual] = []
                datos[clave_actual].append(desentrecomillar(item[2:]))
            elif ":" in item:
                if not isinstance(datos[clave_actual], dict):
                    datos[clave_actual] = {}
                k, v = item.split(":", 1)
                datos[clave_actual][k.strip()] = desentrecomillar(v.strip())
            continue
        if ":" not in linea:
            err(f"{rel(ruta)}: línea de frontmatter no válida: {linea!r}")
            continue
        k, v = linea.split(":", 1)
        k, v = k.strip(), v.strip()
        datos[k] = desentrecomillar(v) if v else {}
        clave_actual = k if not v else None
    return datos, cuerpo


def desentrecomillar(v: str) -> str:
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    return v


def rel(p: Path) -> str:
    return str(p.relative_to(RAIZ))


def cargar_categorias() -> list[dict]:
    ruta = SKILLS / "categorias.json"
    try:
        cats = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        err(f"skills/categorias.json ilegible: {e}")
        return []
    ids = [c.get("id") for c in cats]
    if len(ids) != len(set(ids)):
        err("skills/categorias.json: ids duplicados")
    return cats


def cargar_skills(categorias: list[dict]) -> list[dict]:
    ids_cat = {c["id"] for c in categorias}
    skills = []
    nombres = set()
    for ruta in sorted(SKILLS.glob("*/*/SKILL.md")):
        carpeta, cat = ruta.parent, ruta.parent.parent.name
        fm, cuerpo = leer_frontmatter(ruta)
        nombre, desc = fm.get("name", ""), fm.get("description", "")
        meta = fm.get("metadata") if isinstance(fm.get("metadata"), dict) else {}
        r = rel(ruta)
        if not NOMBRE_RE.match(nombre) or len(nombre) > 64:
            err(f"{r}: 'name' debe ser kebab-case en minúsculas (≤ 64): {nombre!r}")
        if nombre != carpeta.name:
            err(f"{r}: 'name' ({nombre}) debe coincidir con la carpeta ({carpeta.name})")
        if nombre in nombres:
            err(f"{r}: nombre de skill duplicado: {nombre}")
        nombres.add(nombre)
        if not desc or not isinstance(desc, str):
            err(f"{r}: falta 'description'")
        elif len(desc) > 1024:
            err(f"{r}: 'description' supera 1024 caracteres ({len(desc)})")
        if cat not in ids_cat:
            err(f"{r}: la categoría '{cat}' no existe en skills/categorias.json")
        if meta.get("categoria") != cat:
            err(f"{r}: metadata.categoria ({meta.get('categoria')}) debe ser '{cat}'")
        if not SEMVER_RE.match(meta.get("version", "")):
            err(f"{r}: metadata.version debe ser semver (x.y.z)")
        for otra in [s.strip() for s in meta.get("relacionadas", "").split(",") if s.strip()]:
            if not list(SKILLS.glob(f"*/{otra}/SKILL.md")):
                err(f"{r}: metadata.relacionadas menciona una skill inexistente: {otra}")

        # Recursos: todo lo citado existe y todo lo existente está citado.
        citados = set(re.findall(r"(?:references|scripts|assets)/[\w./-]+\.\w+", cuerpo))
        for c in sorted(citados):
            if not (carpeta / c).exists():
                err(f"{r}: cita '{c}' pero el archivo no existe")
        recursos = sorted(
            str(p.relative_to(carpeta)) for sub in ("references", "scripts", "assets")
            for p in (carpeta / sub).rglob("*") if p.is_file() and p.name != ".DS_Store"
        )
        for f in recursos:
            if f not in citados:
                err(f"{r}: '{f}' no está enlazado desde SKILL.md (recurso huérfano)")
        skills.append({
            "name": nombre,
            "categoria": cat,
            "description": desc,
            "version": meta.get("version", ""),
            "fuentes": meta.get("fuentes", ""),
            "relacionadas": [s.strip() for s in meta.get("relacionadas", "").split(",") if s.strip()],
            "ruta": rel(ruta),
            "recursos": recursos,
        })
    return skills


def cargar_agentes(skills: list[dict]) -> list[dict]:
    nombres = {s["name"] for s in skills}
    agentes = []
    for ruta in sorted(AGENTES.glob("*.md")):
        fm, _ = leer_frontmatter(ruta)
        lista = fm.get("skills") if isinstance(fm.get("skills"), list) else []
        for s in lista:
            if s not in nombres:
                err(f"{rel(ruta)}: la skill '{s}' no existe")
        if fm.get("name") != ruta.stem:
            err(f"{rel(ruta)}: 'name' debe coincidir con el nombre del archivo")
        agentes.append({"name": fm.get("name", ""), "description": fm.get("description", ""),
                        "ruta": rel(ruta), "skills": lista})
    return agentes


def validar_enlaces() -> None:
    """Todo enlace Markdown relativo del repositorio debe resolver."""
    for md in RAIZ.rglob("*.md"):
        if ".git" in md.parts or "node_modules" in md.parts:
            continue
        texto = md.read_text(encoding="utf-8")
        for destino in re.findall(r"\]\(([^)\s]+)\)", texto):
            if re.match(r"^(https?:|mailto:|#)", destino):
                continue
            objetivo = (md.parent / destino.split("#", 1)[0]).resolve()
            if not objetivo.exists():
                err(f"{rel(md)}: enlace roto → {destino}")


def primera_frase(desc: str) -> str:
    corte = desc.split(" Úsala", 1)[0].strip()
    return corte if len(corte) <= 260 else corte[:257].rsplit(" ", 1)[0] + "…"


def generar(categorias, skills, agentes) -> dict[Path, str]:
    salida: dict[Path, str] = {}
    por_cat = {c["id"]: [s for s in skills if s["categoria"] == c["id"]] for c in categorias}

    salida[RAIZ / "catalog.json"] = json.dumps(
        {"esquema": 1, "categorias": categorias, "skills": skills, "agentes": agentes},
        ensure_ascii=False, indent=2) + "\n"

    # llms.txt
    l = ["# evolith-agent-skills", "",
         "> Biblioteca de skills y agentes para cualquier LLM o agente de código. Cada skill es una carpeta con SKILL.md "
         "(frontmatter name/description + instrucciones) y recursos bajo demanda en references/ y scripts/. "
         "Lee AGENTS.md para el protocolo de uso.", "",
         "Protocolo: 1) elige la skill cuya description encaje con la tarea; 2) lee su SKILL.md completo; "
         "3) abre solo las references que el SKILL.md indique para el caso; 4) aplica su formato de salida.", ""]
    for c in categorias:
        if not por_cat[c["id"]]:
            continue
        l += [f"## {c['nombre']}", ""]
        l += [f"- [{s['name']}]({s['ruta']}): {primera_frase(s['description'])}" for s in por_cat[c["id"]]]
        l.append("")
    if agentes:
        l += ["## Agentes", ""]
        l += [f"- [{a['name']}]({a['ruta']}): {a['description']}" for a in agentes]
        l.append("")
    l += ["## Documentación", "",
          "- [Protocolo para agentes](AGENTS.md): cómo descubrir y aplicar skills",
          "- [Integración por herramienta](docs/integracion.md): Claude Code, Codex, Copilot, Cursor, Gemini y chats",
          "- [Estándar de skills](docs/estandar-de-skills.md): cómo escribir y validar una skill nueva",
          "- [Fuentes](fuentes/README.md): origen y trazabilidad del conocimiento",
          "- [Catálogo JSON](catalog.json): índice legible por máquinas", ""]
    salida[RAIZ / "llms.txt"] = "\n".join(l)

    # skills/README.md
    t = ["# Catálogo de skills", "", AVISO, "",
         f"{len(skills)} skills en {sum(1 for c in categorias if por_cat[c['id']])} categorías. "
         "Cada skill funciona sola; `metadata.relacionadas` indica con cuáles se combina.", ""]
    for c in categorias:
        if not por_cat[c["id"]]:
            continue
        t += [f"## [{c['nombre']}]({c['id']}/README.md)", "", c["descripcion"], "",
              "| Skill | Qué resuelve | Versión |", "|---|---|---|"]
        t += [f"| [`{s['name']}`]({s['categoria']}/{s['name']}/SKILL.md) | {primera_frase(s['description'])} | {s['version']} |"
              for s in por_cat[c["id"]]]
        t.append("")
    salida[SKILLS / "README.md"] = "\n".join(t)

    # hubs de categoría
    for c in categorias:
        lista = por_cat[c["id"]]
        if not lista:
            continue
        h = [f"# {c['nombre']}", "", AVISO, "", c["descripcion"], "",
             "| Skill | Qué resuelve | Relacionadas |", "|---|---|---|"]
        for s in lista:
            rels = ", ".join(f"`{x}`" for x in s["relacionadas"]) or "—"
            h.append(f"| [`{s['name']}`]({s['name']}/SKILL.md) | {primera_frase(s['description'])} | {rels} |")
        h += ["", "Volver al [catálogo](../README.md).", ""]
        salida[SKILLS / c["id"] / "README.md"] = "\n".join(h)
    return salida


def main() -> int:
    check = "--check" in sys.argv
    categorias = cargar_categorias()
    skills = cargar_skills(categorias)
    agentes = cargar_agentes(skills)
    salida = generar(categorias, skills, agentes)

    desactualizados = [p for p, c in salida.items() if not p.exists() or p.read_text(encoding="utf-8") != c]
    if check:
        for p in desactualizados:
            err(f"{rel(p)} está desactualizado: ejecuta python3 scripts/build_catalog.py")
    else:
        for p in desactualizados:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(salida[p], encoding="utf-8")
    validar_enlaces()

    for a in avisos:
        print(f"aviso: {a}")
    if errores:
        for e in errores:
            print(f"ERROR: {e}")
        print(f"\n{len(errores)} error(es).")
        return 1
    accion = "verificado" if check else f"regenerados {len(desactualizados)} archivo(s)"
    print(f"OK: {len(skills)} skills, {len(agentes)} agente(s), {len(categorias)} categorías — {accion}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
