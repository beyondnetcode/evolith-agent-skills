"""Pruebas de los scripts del repositorio (biblioteca estándar).

Ejecutar: python3 -m unittest discover -s tests -v
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ESCANER = RAIZ / "skills/arquitectura/radar-arquitectura/scripts/escanear_senales.py"
INSTALADOR = RAIZ / "scripts/instalar_skills.py"
CATALOGO = RAIZ / "scripts/build_catalog.py"


def correr(*args: str) -> str:
    r = subprocess.run([sys.executable, *args], capture_output=True, text=True, check=False)
    if r.returncode != 0:
        raise AssertionError(f"{args} → {r.returncode}\n{r.stdout}\n{r.stderr}")
    return r.stdout


def escribir(base: Path, rel: str, contenido: str) -> None:
    p = base / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(contenido).lstrip())


class EscanerSenales(unittest.TestCase):
    def test_detecta_las_senales_positivas(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            escribir(base, "src/orders.ts", """
                export async function confirmOrder(items) {
                  for (const it of items) {
                    await checkStock(it.sku);
                  }
                  await Promise.all(items.map(i => reserve(i)));
                  localStorage.setItem('access_token', jwt);
                  product.stock = product.stock - qty;
                  await repo.save(order);
                  await producer.send({ topic: 'orders', messages: [evt] });
                }
                app.post('/webhooks/stripe', handler);
            """)
            escribir(base, "db/q.sql", """
                CREATE TABLE pedidos (id uuid PRIMARY KEY DEFAULT gen_random_uuid());
                SELECT * FROM pedidos ORDER BY creado_en LIMIT 20 OFFSET :offset;
            """)
            escribir(base, "k8s/dep.yaml", """
                kind: Deployment
                spec:
                  template:
                    spec:
                      containers:
                        - name: api
            """)
            escribir(base, "node_modules/x/i.js", "for (;;) { await y }\n")
            salida = correr(str(ESCANER), d)
            for titulo in ("Paginación por OFFSET", "UUID aleatorio", "Fan-out concurrente sin límite",
                           "localStorage", "Read-modify-write", "Guardar en BD y publicar",
                           "webhook sin verificación", "sin límite de memoria", "sin readinessProbe",
                           "`await` dentro de un bucle"):
                self.assertIn(titulo, salida)
            self.assertNotIn("node_modules", salida)

    def test_no_marca_patrones_seguros(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            escribir(base, "wh.ts", """
                app.post('/webhooks/stripe', (req) => { stripe.webhooks.constructEvent(raw, sig, secret); });
                for (const b of batches) { enqueue(b); }
                const ok = await Promise.all(limit(5, ids));
                for (const k of keys) log("await-en-bucle");
            """)
            escribir(base, "b.cs", """
                for (int i = 0; i < n; i++) Log(i);
                await Done();
            """)
            escribir(base, "dep.yaml", """
                kind: Deployment
                spec:
                  template:
                    spec:
                      containers:
                        - name: api
                          readinessProbe: {httpGet: {path: /ready, port: 8080}}
                          resources:
                            limits:
                              memory: 512Mi
            """)
            self.assertIn("Sin señales", correr(str(ESCANER), d))

    def test_await_en_bucle_por_lenguaje(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            escribir(base, "a.py", """
                async def f(items):
                    for it in items:
                        await check(it)
                    for it in items:
                        enqueue(it)
                    await flush()
            """)
            escribir(base, "b.cs", """
                foreach (var it in items)
                {
                    await CheckAsync(it);
                }
            """)
            salida = correr(str(ESCANER), d, "--solo", "await-en-bucle")
            self.assertIn("a.py:2", salida)
            self.assertNotIn("a.py:4", salida)
            self.assertIn("b.cs:1", salida)


class Instalador(unittest.TestCase):
    def test_enlaza_copia_y_desinstala_sin_tocar_ajenas(self):
        with tempfile.TemporaryDirectory() as d:
            destino = Path(d) / "skills"
            (destino / "ajena").mkdir(parents=True)
            correr(str(INSTALADOR), "--destino", str(destino), "--categorias", "datos")
            enlace = destino / "datos-persistencia"
            self.assertTrue(enlace.is_symlink())
            self.assertTrue((enlace / "SKILL.md").exists())
            correr(str(INSTALADOR), "--destino", str(destino), "--skills", "datos-persistencia", "--copiar")
            self.assertFalse(enlace.is_symlink())
            self.assertTrue((enlace / "SKILL.md").exists())
            correr(str(INSTALADOR), "--destino", str(destino), "--desinstalar")
            self.assertFalse(enlace.exists())
            self.assertTrue((destino / "ajena").exists())


class Catalogo(unittest.TestCase):
    def test_repositorio_valido_y_generados_al_dia(self):
        self.assertIn("verificado", correr(str(CATALOGO), "--check"))


if __name__ == "__main__":
    unittest.main()
