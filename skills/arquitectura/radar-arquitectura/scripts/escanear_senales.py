#!/usr/bin/env python3
"""Radar de señales arquitectónicas (heurístico).

Recorre un repositorio y marca patrones de código que, según el catálogo de
TheDebugDuck, suelen esconder un problema de producción. Son SEÑALES para
revisar, no veredictos: cada hallazgo apunta a la skill/referencia que explica
el mecanismo y la pregunta que hay que responder con evidencia.

Uso:
    python3 escanear_senales.py <ruta> [--max-por-regla N] [--solo regla1,regla2]

Solo usa la biblioteca estándar. Salida en Markdown por stdout.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass, field

IGNORAR_DIRS = {
    ".git", "node_modules", "vendor", "dist", "build", "out", "target", "bin", "obj",
    ".venv", "venv", "__pycache__", ".next", ".nuxt", "coverage", ".idea", ".vscode",
    "migrations_snapshots", ".gradle", ".terraform",
}
EXT_CODIGO = {
    ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".py", ".java", ".kt", ".cs", ".go",
    ".rb", ".php", ".sql", ".scala", ".rs",
}
EXT_INFRA = {".yaml", ".yml"}
MAX_BYTES = 1_500_000


@dataclass
class Regla:
    id: str
    titulo: str
    ref: str
    pregunta: str
    patron: re.Pattern | None = None
    exts: set[str] = field(default_factory=lambda: EXT_CODIGO)
    # Si se define, la regla se evalúa por archivo completo (co-ocurrencias).
    por_archivo: object = None


def rx(p: str, flags: int = re.IGNORECASE) -> re.Pattern:
    return re.compile(p, flags)


REGLAS: list[Regla] = [
    Regla("offset-paginacion", "Paginación por OFFSET/skip",
          "datos-persistencia → references/01-paginacion-offset-vs-keyset.md",
          "¿La tabla crece sin cota y el usuario puede pedir páginas profundas? ¿Por qué no keyset?",
          rx(r"\bOFFSET\s+[:\$\?@{\w]|\.skip\(|\.Skip\(|PageRequest\.of\(|\boffset\s*[:=]\s*\(?\s*page")),
    Regla("uuid-v4-pk", "UUID aleatorio como valor por defecto de clave",
          "datos-persistencia → references/03-uuid-y-rendimiento-de-indices.md",
          "¿Es la PK de un B-tree mono-nodo? ¿Por qué no bigint identity o UUIDv7 + ID público opaco?",
          rx(r"DEFAULT\s*\(?\s*(gen_random_uuid|uuid_generate_v4|NEWID)\s*\(|@default\(uuid\(\)\)|GenerationType\.UUID|uuid\.uuid4\b|Guid\.NewGuid\(\)")),
    Regla("jpa-eager", "Relación EAGER en JPA/Hibernate",
          "datos-persistencia → references/36-n-mas-1.md y 06-orm-bien-usado.md",
          "¿Cuántas queries genera el endpoint con 1 000 filas? ¿Fetch join/EntityGraph/proyección?",
          rx(r"FetchType\.EAGER|@(ManyToOne|OneToOne)\s*$", re.MULTILINE)),
    Regla("promise-all-sin-limite", "Fan-out concurrente sin límite",
          "resiliencia-operacion → references/05-async-no-es-paralelo.md",
          "¿Qué pasa cuando el arreglo tiene 10 000 elementos? ¿Batch primero y luego semáforo 5–10?",
          rx(r"Promise\.all(Settled)?\(\s*[\w.]+\.map\(|asyncio\.gather\(\s*\*|Task\.WhenAll\([^)]*Select\(")),
    Regla("regex-dinamica", "Regex construida dinámicamente o con cuantificadores anidados",
          "resiliencia-operacion → references/10-regex-redos.md",
          "¿Procesa input no confiable? ¿Motor lineal (RE2), límite de longitud y timeout?",
          rx(r"new RegExp\(\s*[^'\"/]|re\.(compile|match|search)\([^'\"]*\+|\([^()]*[+*]\)[+*{]")),
    Regla("jwt-localstorage", "Token guardado en localStorage/sessionStorage",
          "seguridad-aplicaciones → references/12-jwt-diseno-seguro.md",
          "¿Por qué no cookie HttpOnly/SameSite o BFF? ¿Cómo se revoca?",
          rx(r"(local|session)Storage\.setItem\(\s*['\"`][^'\"`]*(token|jwt|auth)", re.IGNORECASE)),
    Regla("jwt-larga-vida", "Access token de larga duración",
          "seguridad-aplicaciones → references/12-jwt-diseno-seguro.md",
          "¿Access en minutos + refresh revocable/rotado? ¿Qué pasa si roban el token?",
          rx(r"expiresIn\s*:\s*['\"]?\s*\d+\s*(h|d|days?|hours?)\b|expires_delta\s*=\s*timedelta\((hours|days)=")),
    Regla("hora-local", "Hora local del servidor en lugar de UTC/instante",
          "contratos-api → references/35-utc-y-fechas.md",
          "¿Se guarda un instante en UTC y la zona del usuario aparte? ¿Qué pasa en el cambio de horario?",
          rx(r"DateTime\.Now\b|LocalDateTime\.now\(\)|datetime\.now\(\)(?!\s*\.astimezone)|datetime\.utcnow\(\)|new Date\(\)\.toLocale(String|DateString)\(\)")),
    Regla("upload-extension", "Validación de archivo por extensión o MIME declarado",
          "seguridad-aplicaciones → references/02-validacion-de-archivos.md",
          "¿Se validan magic bytes, el backend decide Content-Type y se sirve con nosniff/attachment desde otro dominio?",
          rx(r"\.endsWith\(\s*['\"]\.(jpe?g|png|gif|pdf|svg|xlsx?|docx?)['\"]|\.mimetype\b|content_type\s*==\s*['\"](image|application)/|originalname")),
    Regla("read-modify-write", "Read-modify-write de un contador/stock en código",
          "consistencia-distribuida → references/33-race-conditions.md",
          "¿Dos requests simultáneas pueden perder una actualización? ¿UPDATE atómico condicional o constraint?",
          rx(r"\b(stock|inventory|inventario|saldo|balance|quantity|cantidad)\s*(=\s*\w+(\.\w+)*\s*[-+]\s*|[-+]=)")),
    Regla("status-200-error", "Error devuelto con 200 OK",
          "contratos-api → references/37-codigos-http.md",
          "¿El cliente, el LB y las métricas pueden distinguir el fallo? ¿4xx/5xx con cuerpo de error consistente?",
          rx(r"status\(\s*200\s*\)\s*\.json\(\s*\{\s*['\"]?(error|err|success\s*:\s*false)|Ok\(\s*new\s*\{\s*(error|Error)")),
    Regla("cache-ttl-fijo", "TTL de caché fijo (posible expiración sincronizada)",
          "resiliencia-operacion → references/30-cache-stampede.md",
          "¿Claves calientes con el mismo TTL? ¿Jitter, single-flight o stale-while-revalidate?",
          rx(r"\.setex\(|\.set\([^)]*['\"]EX['\"]\s*,\s*\d+|\bexpire\(\s*[^,]+,\s*\d+\s*\)|AbsoluteExpirationRelativeToNow\s*=")),
    # --- Reglas por archivo (co-ocurrencias) ---
    Regla("dual-write", "Guardar en BD y publicar en broker en el mismo archivo",
          "consistencia-distribuida → references/28-outbox.md",
          "¿Son atómicos? Si el publish falla tras el commit (o al revés), ¿qué pasa? ¿Outbox/CDC?",
          por_archivo=lambda t: bool(
              re.search(r"\.(save|saveAndFlush|insert|create|update)\(|SaveChanges(Async)?\(|\bcommit\(", t)
              and re.search(r"\.(publish|produce|basicPublish|sendMessage)\(|producer\.send\(|kafkaTemplate\.send\(|channel\.publish\(|\.emit\(\s*['\"][\w.]+(Created|Updated|Paid|Event)", t))),
    Regla("webhook-sin-firma", "Endpoint de webhook sin verificación de firma aparente",
          "consistencia-distribuida → references/29-webhooks-duplicados.md",
          "¿Se verifica HMAC sobre el cuerpo crudo, se deduplica por event_id y se responde 2xx rápido?",
          por_archivo=lambda t: bool(
              re.search(r"['\"/]webhooks?\b", t, re.IGNORECASE)
              and not re.search(r"hmac|signature|constructEvent|verify(Signature|Webhook)|x-hub-signature", t, re.IGNORECASE))),
    Regla("pago-sin-idempotencia", "Flujo de cobro sin clave de idempotencia aparente",
          "consistencia-distribuida → references/34-idempotencia.md",
          "¿Qué pasa con el doble clic o el reintento del cliente? ¿Idempotency-Key del cliente con respuesta almacenada?",
          por_archivo=lambda t: bool(
              re.search(r"\b(charge|payment|checkout|cobro|pago)s?\b.*\b(post|create|charge)\b", t, re.IGNORECASE)
              and not re.search(r"idempoten", t, re.IGNORECASE))),
    Regla("k8s-sin-limite-memoria", "Deployment sin límite de memoria",
          "resiliencia-operacion → references/04-heap-vs-rss-oomkilled.md",
          "¿Cuál es el límite del contenedor y el heap del runtime queda al 70–80 % de él?",
          exts=EXT_INFRA,
          por_archivo=lambda t: bool(re.search(r"kind:\s*(Deployment|StatefulSet)", t) and not re.search(r"limits:\s*\n(\s+\w+:.*\n)*?\s+memory:", t))),
    Regla("k8s-sin-readiness", "Deployment sin readinessProbe",
          "resiliencia-operacion → references/19-load-balancing.md y 20-despliegues-sin-downtime.md",
          "¿Cómo sabe el balanceador que el pod está listo? ¿Readiness ligera y separada de liveness?",
          exts=EXT_INFRA,
          por_archivo=lambda t: bool(re.search(r"kind:\s*(Deployment|StatefulSet)", t) and "readinessProbe" not in t)),
]


def cuerpo_del_bucle(lineas: list[str], i: int, python: bool) -> list[str]:
    """Aproxima el cuerpo del bucle que empieza en la línea i (máx. 12 líneas)."""
    if python:
        base = len(lineas[i]) - len(lineas[i].lstrip())
        cuerpo = []
        for l in lineas[i + 1:i + 13]:
            if l.strip() and len(l) - len(l.lstrip()) <= base:
                break
            cuerpo.append(l)
        return cuerpo
    # Lenguajes con llaves: el bloque entre la primera "{" y su cierre.
    if "{" not in lineas[i]:
        if lineas[i].rstrip().endswith(";"):
            return [lineas[i]]  # cuerpo en la misma línea: for (...) algo();
        siguiente = lineas[i + 1] if i + 1 < len(lineas) else ""
        if not siguiente.lstrip().startswith("{"):
            return [siguiente]  # bucle sin llaves: una sola sentencia
    bloque = "\n".join(lineas[i:i + 13])
    inicio = bloque.index("{")
    profundidad = 0
    for k in range(inicio, len(bloque)):
        if bloque[k] == "{":
            profundidad += 1
        elif bloque[k] == "}":
            profundidad -= 1
            if profundidad == 0:
                return [bloque[inicio + 1:k]]
    return [bloque[inicio + 1:]]


def await_en_bucle(lineas: list[str], python: bool) -> list[int]:
    """Detecta `await` dentro del cuerpo de un for/foreach/while/forEach."""
    hallazgos = []
    abre = re.compile(r"^\s*(for\b|foreach\b|while\b|\w[\w.]*\.forEach\()")
    literales = re.compile(r"""(['"`])(?:\\.|(?!\1).)*\1""")  # ignora "await" dentro de strings
    for i, l in enumerate(lineas):
        if abre.search(l) and not re.search(r"for\s+await\b|async\s+for\b", l):
            cuerpo = [literales.sub("", v) for v in cuerpo_del_bucle(lineas, i, python)]
            if any(re.search(r"\bawait\b", v) for v in cuerpo):
                hallazgos.append(i + 1)
    return hallazgos


def recorrer(raiz: str):
    for dirpath, dirnames, filenames in os.walk(raiz):
        dirnames[:] = [d for d in dirnames if d not in IGNORAR_DIRS and not d.startswith(".")]
        for f in filenames:
            ext = os.path.splitext(f)[1].lower()
            if ext in EXT_CODIGO or ext in EXT_INFRA:
                ruta = os.path.join(dirpath, f)
                try:
                    if os.path.getsize(ruta) > MAX_BYTES:
                        continue
                    with open(ruta, encoding="utf-8", errors="ignore") as fh:
                        yield ruta, ext, fh.read()
                except OSError:
                    continue


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ruta")
    ap.add_argument("--max-por-regla", type=int, default=15)
    ap.add_argument("--solo", default="", help="ids de regla separados por coma")
    args = ap.parse_args()
    solo = {s.strip() for s in args.solo.split(",") if s.strip()}

    reglas = [r for r in REGLAS if not solo or r.id in solo]
    incluir_await = not solo or "await-en-bucle" in solo
    resultados: dict[str, list[str]] = {r.id: [] for r in reglas}
    resultados["await-en-bucle"] = []
    archivos = 0

    for ruta, ext, texto in recorrer(args.ruta):
        archivos += 1
        rel = os.path.relpath(ruta, args.ruta)
        lineas = texto.splitlines()
        for r in reglas:
            if ext not in r.exts:
                continue
            if r.por_archivo is not None:
                try:
                    if r.por_archivo(texto):
                        resultados[r.id].append(f"`{rel}`")
                except re.error:
                    pass
                continue
            for n, l in enumerate(lineas, 1):
                if r.patron.search(l):
                    resultados[r.id].append(f"`{rel}:{n}` — `{l.strip()[:140]}`")
        if incluir_await and ext in {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".py", ".cs", ".kt", ".rs"}:
            for n in await_en_bucle(lineas, python=(ext == ".py")):
                resultados["await-en-bucle"].append(f"`{rel}:{n}` — `{lineas[n - 1].strip()[:140]}`")

    meta = {r.id: r for r in reglas}
    meta["await-en-bucle"] = Regla(
        "await-en-bucle", "`await` dentro de un bucle (llamadas en serie)",
        "resiliencia-operacion → references/05-async-no-es-paralelo.md",
        "¿Son llamadas remotas independientes? ¿Batch (IN/bulk) o concurrencia acotada?")

    print(f"# Radar de señales — {os.path.abspath(args.ruta)}\n")
    print(f"Archivos analizados: {archivos}. Señales heurísticas: confirma cada una leyendo el código antes de afirmar nada.\n")
    total = 0
    for rid, hallazgos in resultados.items():
        if not hallazgos or rid not in meta:
            continue
        r = meta[rid]
        total += len(hallazgos)
        print(f"## {r.titulo} ({len(hallazgos)})\n")
        print(f"- Referencia: {r.ref}")
        print(f"- Pregunta: {r.pregunta}\n")
        for h in hallazgos[: args.max_por_regla]:
            print(f"  - {h}")
        if len(hallazgos) > args.max_por_regla:
            print(f"  - … y {len(hallazgos) - args.max_por_regla} más")
        print()
    if total == 0:
        print("Sin señales. Eso no prueba ausencia de riesgos: revisa también diseño, configuración e infraestructura.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
