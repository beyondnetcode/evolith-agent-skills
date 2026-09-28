#!/usr/bin/env python3
"""Descarga las transcripciones automáticas (español) de los videos listados en videos.tsv.

Sirve para re-analizar la fuente (p. ej. los videos marcados «D» en el índice) o
incorporar videos nuevos. Las transcripciones son material de trabajo: NO se
versionan en este repositorio (derechos del autor); solo se versionan las notas
parafraseadas en las referencias de las skills.

Requisito (fuera de la biblioteca estándar):
    python3 -m venv .venv && .venv/bin/pip install youtube-transcript-api

Uso:
    .venv/bin/python descargar_transcripciones.py <carpeta-salida> [--solo 32,33,...]

YouTube limita por IP: el script se detiene al primer bloqueo (IpBlocked/RequestBlocked)
para no prolongarlo; reintenta más tarde. Ya descargados se omiten.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

try:
    from youtube_transcript_api import YouTubeTranscriptApi
except ImportError:
    sys.exit("Falta youtube-transcript-api: pip install youtube-transcript-api")

TSV = Path(__file__).with_name("videos.tsv")


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    salida = Path(sys.argv[1]).expanduser()
    salida.mkdir(parents=True, exist_ok=True)
    solo = set()
    if "--solo" in sys.argv:
        solo = {s.strip().zfill(2) for s in sys.argv[sys.argv.index("--solo") + 1].split(",")}
    api = YouTubeTranscriptApi()
    for linea in TSV.read_text(encoding="utf-8").splitlines():
        n, vid, titulo = linea.split("\t")
        if solo and n not in solo:
            continue
        destino = salida / f"{n}_{vid}.txt"
        if destino.exists() and destino.stat().st_size > 500:
            continue
        try:
            partes = api.fetch(vid, languages=["es", "es-419", "es-MX", "es-ES"])
        except Exception as e:  # noqa: BLE001 — la librería expone muchas excepciones
            nombre = type(e).__name__
            print(f"{n} {nombre}")
            if "Blocked" in nombre:
                print("Bloqueo de YouTube por IP: reintenta más tarde.")
                return 2
            continue
        texto = " ".join(p.text.replace("\n", " ") for p in partes)
        destino.write_text(f"# {n} · {titulo}\n# https://youtu.be/{vid}\n\n{texto}", encoding="utf-8")
        print(f"{n} ok ({destino.stat().st_size} bytes)")
        time.sleep(15)
    return 0


if __name__ == "__main__":
    sys.exit(main())
