# [39] Complejidad Algorítmica explicada fácil (Big O en minutos)

> Fuente: TheDebugDuck — https://youtu.be/vVrI4bQMZhE · notas parafraseadas; «(complemento)» = conocimiento añadido o corrección.
> Estado: elaborado a partir del título y el temario público del video; la transcripción no estuvo disponible (bloqueo de YouTube, 2026-09-28). Lo que no figura en el temario es «(complemento)». Pendiente de contrastar con la transcripción.

- **Síntoma en el código/equipo:** algoritmos que se vuelven lentos al crecer los datos. (complemento) Pasa todas las pruebas con 100 registros y tarda minutos con 100.000; un job nocturno pasa de 5 min a 6 h sin cambios de código; un cliente grande (tenant) provoca timeouts que nadie más ve; CPU al 100 % sin errores en logs; el equipo "resuelve" con más réplicas y el coste crece más rápido que el negocio.
- **Causa raíz (mecanismo):** Big O describe **cómo crece** el coste respecto de n, no cuánto tarda. O(1) no depende de n; O(log n) crece un paso cada vez que n se duplica (búsqueda binaria: ~20 comparaciones para 10⁶ elementos; un índice B-tree: 3–4 páginas); O(n) crece en proporción; O(n²) cuadruplica el coste al duplicar n. (complemento) El cuadrático suele estar **oculto**: una búsqueda lineal (`find`, `includes`, `indexOf`, `List.Contains`) dentro de un bucle es O(n·m) aunque solo se vea un `for`. En desarrollo n=100 da 10⁴ operaciones (invisible); en producción n=10⁵ da 10¹⁰ (minutos).
- **Complejidad espacial y amortizada (complemento):**
  - **Espacial:** memoria auxiliar que usa el algoritmo. Materializar con `ToList()`/`Array.from` 10 M filas de ~100 B son ~1 GB en el heap; recorrer en streaming (`IAsyncEnumerable`, cursores, `for await`) es O(1) auxiliar. La recursión cuesta O(profundidad) de pila: un árbol degenerado o una lista enlazada de 10⁵ nodos basta para desbordarla. Bajar tiempo casi siempre cuesta espacio (índice hash O(n) para pasar de O(n²) a O(n)).
  - **Amortizada:** coste medio por operación sobre una **secuencia** en el peor caso. `push` en un array dinámico es O(1) amortizado porque la capacidad crece por un factor (×1,5–×2); la copia O(n) ocasional aparece como pico de latencia (p99), no en la media. Con crecimiento aditivo (+10) deja de ser O(1) y n inserciones cuestan O(n²).
- **Constantes que importan en la práctica (complemento):** Big O descarta constantes, pero una "operación" no vale lo mismo: comparar enteros en caché ~1 ns, leer RAM ~100 ns, un round-trip de red en el mismo datacenter ~0,5 ms, entre continentes ~150 ms (órdenes de magnitud de las *latency numbers* de Jeff Dean). Un bucle de 1.000 iteraciones con una consulta dentro es O(n) igual que sumar 1.000 enteros, y es 10⁵–10⁶ veces más lento. Para n pequeño, un recorrido lineal sobre un array contiguo gana a un hash o a un árbol; por eso los `sort` de las bibliotecas son híbridos (Timsort, introsort) y usan inserción en tramos cortos.
- **Metáfora visual propia (complemento):** la guía telefónica y la fiesta. Buscar "Pérez" abriendo por la mitad es O(log n); leer todas las páginas es O(n); saludar en una fiesta dándole la mano a cada invitado con cada otro es O(n²): con 10 personas son 45 apretones, con 1.000 casi 500.000. **Dónde se rompe:** la guía solo sirve porque alguien la ordenó antes (ordenar o mantener un índice cuesta O(n log n) y escrituras); y la metáfora trata todos los apretones como iguales, cuando en software uno puede ser un acceso a memoria y otro una llamada de red de 50 ms.
- **Estrategias / solución:**
  1. (complemento) **Indexar antes del bucle** (tiempo por espacio):
     ```ts
     // Antes: O(n·m) — find dentro de map; 10⁴ pagos × 10⁴ movimientos = 10⁸ comparaciones
     const conciliados = pagos.map(p => ({ ...p, mov: movimientos.find(m => m.ref === p.ref) }));
     // Después: O(n + m) tiempo, O(m) memoria extra
     const porRef = new Map<string, Movimiento>();
     for (const m of movimientos) if (!porRef.has(m.ref)) porRef.set(m.ref, m); // conserva el primero, como find
     const conciliados = pagos.map(p => ({ ...p, mov: porRef.get(p.ref) }));
     ```
  2. (complemento) **Sacar la E/S del bucle:** una consulta con `IN (...)`/join o un endpoint por lote en lugar de N llamadas (N+1). El número de round-trips es la n que más duele.
  3. (complemento) **Elegir la estructura por la operación dominante:** `Set`/`HashSet` para pertenencia, `Map`/`Dictionary` para búsqueda por clave, cola de prioridad para "el siguiente más urgente", `StringBuilder` para concatenar en C#/Java.
  4. (complemento) **Streaming y paginación** cuando lo que crece es la memoria; keyset en lugar de OFFSET cuando lo que crece es el recorrido.
  5. (complemento) **Prueba de duplicación** (Sedgewick): mide con n y 2n; si el tiempo se multiplica ×2 es lineal, ×4 cuadrático, ×8 cúbico, casi ×1 logarítmico. Hazlo con fixtures del tamaño de producción, no con 20 filas.
- **Casos reales de producción (complemento):**
  - **N+1:** 1 consulta de pedidos + 1 por cada pedido. Es O(n) en round-trips: 50 ítems × 2 ms = 100 ms; 1.000 ítems = 2 s. Se arregla con fetch join, batch fetch o proyección (ver [06] y [36] en `datos-persistencia`).
  - **OFFSET profundo:** `LIMIT 20 OFFSET 100000` obliga al motor a producir y descartar 100.020 filas; cada página cuesta O(offset) y recorrer toda la tabla por páginas es O(n²/tamaño de página). Keyset con índice cuesta O(log n + página) (ver [01] en `datos-persistencia`).
  - **Regex con backtracking:** cuantificadores anidados o comodines que compiten (`(a+)+$`, `.*(?:.*=.*)`) llevan a coste polinómico o exponencial. Stack Overflow (2016) cayó 34 min por un recorte de espacios O(n²) sobre ~20.000 espacios; Cloudflare (2019) tuvo ~27 min de 502 globales por una regla WAF (ver [10] en `resiliencia-operacion`).
  - **Bucles anidados sobre colecciones que crecen:** conciliaciones, deduplicaciones con `includes`, "diff" de listas, permisos por usuario × recurso. Nacen cuando n es un catálogo pequeño y explotan cuando pasa a ser transacciones.
- **Trade-offs y cuándo NO aplicar:** (complemento) si n está acotado y es pequeño por naturaleza (12 meses, 5 países, 30 estados de pedido), prima la claridad: un `find` es correcto y más legible que un índice. Optimizar constantes sin perfilar es desperdicio: el cuello de botella real suele ser E/S. Un índice en memoria duplica datos y hay que invalidarlo si la fuente cambia. Complejidad asintótica mejor con constantes enormes puede perder para todo n realista.
- **Heurísticas y umbrales:** (complemento)
  - Estima con la n de producción a 12–24 meses, no la de hoy.
  - Orden de magnitud: del orden de 10⁸–10⁹ operaciones simples por segundo y núcleo según lenguaje y localidad de memoria. n ≤ 10³: casi cualquier cosa sirve; n ~10⁵: exige ≤ O(n log n); n ≥ 10⁷: O(n) en streaming y cuidado con la memoria.
  - Cuenta round-trips aparte de operaciones de CPU: ≥ 1 E/S por iteración de un bucle que crece con los datos es un hallazgo por sí solo.
- **Anti-patrones / señales en code review:** (complemento)
  - `.find/.includes/.indexOf/.filter` dentro de un bucle o `.map`; `List<T>.Contains` dentro de `foreach` (usa `HashSet<T>`).
  - `await repo.get(...)` o `fetch` dentro de un `for` o `map`.
  - `reduce((acc, x) => ({ ...acc, [x.id]: x }), {})`: copia el acumulador en cada vuelta, O(n²).
  - `string +=` en bucle en C#/Java; `shift()` como cola sobre arrays grandes (depende del motor: usa índice de cabeza o deque).
  - Múltiple enumeración de un `IEnumerable`/`IQueryable` que reejecuta la consulta; `Count()` dentro de un bucle.
  - Ordenar dentro de un bucle; recursión sin memoización con subproblemas repetidos (Fibonacci ingenuo O(2ⁿ)).
  - `OFFSET` creciente en jobs batch; regex con cuantificadores anidados sobre entrada externa sin límite de longitud ni timeout.
- **Preguntas de revisión:** (complemento)
  1. ¿Cuál es n en producción hoy y en 24 meses, y qué la hace crecer (usuarios, transacciones, tenants)?
  2. ¿Qué operación domina: comparaciones en memoria, asignación de memoria o round-trips de E/S?
  3. ¿Hay una búsqueda lineal o una E/S dentro de un bucle cuya longitud crece con los datos?
  4. ¿El coste por página o por lote crece con la posición (OFFSET) o es constante?
  5. ¿Hay regex sobre entrada no confiable con motor de backtracking, sin límite de longitud ni timeout?
  6. ¿Se midió con volumen realista (prueba de duplicación) o solo con fixtures pequeños?
  7. ¿La memoria auxiliar es O(1) (streaming) o O(n) (materializar todo)?
- **Referencias (complemento):** Knuth, *Big Omicron and Big Omega and Big Theta* (SIGACT News, 1976); Cormen, Leiserson, Rivest y Stein, *Introduction to Algorithms* (análisis amortizado); Tarjan, *Amortized Computational Complexity* (1985); Sedgewick y Wayne, *Algorithms* 4.ª ed. (prueba de duplicación); Russ Cox, *Regular Expression Matching Can Be Simple And Fast* (2007); postmortems de Stack Overflow (20-jul-2016) y Cloudflare (2-jul-2019); documentación de PostgreSQL sobre `OFFSET`.
- **Precisión técnica:**
  - (complemento) Formalmente O es cota superior, Ω inferior y Θ ajustada; en el habla habitual "O(n)" se usa como Θ. Big O compara crecimiento, no tiempos absolutos.
  - (complemento) O(1) no significa rápido: significa independiente de n. Una llamada O(1) de 50 ms es más lenta que un O(n) sobre 1.000 enteros en memoria.
  - (complemento) Una tabla hash es O(1) **esperado**; el peor caso es O(n) por colisiones (O(log n) por cubeta en Java 8+, JEP 180). Por los ataques HashDoS (28C3, 2011) los runtimes aleatorizan el hash por proceso (SipHash en Python ≥ 3.4, Marvin en .NET).
  - (complemento) Amortizado ≠ promedio: el amortizado es una garantía sobre cualquier secuencia; el promedio depende de la distribución de entradas (quicksort: O(n log n) medio, O(n²) peor; introsort lo acota).
  - (complemento) La base del logaritmo es irrelevante en Big O (cambiar de base multiplica por una constante). Ordenar por comparación tiene cota inferior Ω(n log n): faltan en el temario O(n log n), O(2ⁿ) y O(n!).
  - (complemento) En V8, `+=` sobre strings usa *ropes* y no suele ser cuadrático; en C# y Java sí lo es, por inmutabilidad.
  - (complemento) Reemplazar `find` por un `Map` cambia la semántica si hay claves duplicadas: `find` devuelve el primero; `new Map(pares)` conserva el último.
