# [01] El error de paginar con OFFSET cuando tu tabla supera el millón de registros

> Fuente: TheDebugDuck — https://youtu.be/Es25hxA4A64 · notas parafraseadas; «(complemento)» = conocimiento añadido o corrección.

- **Síntoma en producción:**
  - Páginas 1–2 responden en < 1 s; `page=5000` (size 20 → offset 100 000) tarda segundos o da timeout. CPU de la BD al 100 % sin joins pesados ni procesos raros.
  - La latencia del endpoint crece con la profundidad de página. El promedio/p50 se ve sano porque casi todo el tráfico está en las primeras páginas; el problema sólo aflora al segmentar por nº de página (ejemplo del video: p1 ≈ 50 ms, p1000 cientos de ms, p5000 timeouts).
  - Soporte recibe quejas de lentitud al buscar pedidos antiguos; no salta ninguna alerta.
  - Feeds con muchas inserciones: elementos repetidos o faltantes entre páginas.
  - Jobs batch que reutilizan el helper de paginación: se ralentizan progresivamente durante horas, suben CPU y provocan timeouts en consultas ajenas que compiten por recursos.
- **Causa raíz (mecanismo):**
  - `OFFSET N` no es un salto directo: el motor debe producir las filas en el orden pedido, recorrer y descartar N, y sólo entonces devolver `LIMIT`. Coste por página ∝ offset + limit; recorrer toda la tabla página a página es O(n²).
  - Un índice sobre la columna de orden evita el sort, pero no el recorrido de las N entradas. (complemento) En PostgreSQL/InnoDB, además, cada fila descartada suele requerir visitar el heap/índice agrupado salvo index-only scan o índice cubriente. Sin índice: sort top-N que retiene offset+limit filas.
  - Consistencia: paginar por posición sobre un conjunto mutable. Una inserción arriba desplaza todo una posición → duplicados; un borrado o una fila que deja de cumplir el filtro → saltos.
  - Las abstracciones (helper genérico, `findAll(pageable)`, `skip/take`, código generado por IA) ocultan el coste: el servicio sólo ve `page=5000,size=20`.
- **Metáfora visual del video:** ventanilla con una pila de tickets; con offset el empleado cuenta uno a uno desde arriba hasta 100 000; con keyset le enseñas tu último ticket y pides los 20 siguientes.
- **Estrategias / solución:**
  1. Keyset / seek pagination con clave de orden **única y estable**: `(created_at, id)`; el `id` desempata marcas de tiempo iguales.
  2. Índice compuesto alineado exactamente con el `ORDER BY` (mismas columnas, mismo sentido).
  3. Contrato de API con cursor opaco (`next_cursor` = última clave codificada y, opcionalmente, firmada) en lugar de `page`.
  4. Jobs batch: recorrer por PK con keyset y checkpoint; nunca reutilizar la paginación de la UI.
  5. Si el negocio exige números de página: mantenerlos en UI pero limitar la profundidad máxima, exigir filtros (rango de fechas) e impedir consultar todo el historial de golpe.
  6. Observabilidad: histogramas de latencia por bucket de profundidad/offset.
  ```sql
  -- Índice alineado con el orden de lectura
  CREATE INDEX ix_orders_created_id ON orders (created_at DESC, id DESC);

  -- Primera página
  SELECT id, created_at, total FROM orders
  ORDER BY created_at DESC, id DESC
  LIMIT 20;

  -- Páginas siguientes: continuar desde la última clave vista (PostgreSQL / MySQL 8)
  SELECT id, created_at, total FROM orders
  WHERE (created_at, id) < (:last_created_at, :last_id)
  ORDER BY created_at DESC, id DESC
  LIMIT 20;

  -- Forma expandida (SQL Server/Oracle, o sentidos de orden mixtos)
  WHERE created_at < @c OR (created_at = @c AND id < @id)
  ```
  ```text
  // Job batch sobre tabla grande
  last_id = 0
  loop:
    rows = SELECT ... WHERE id > :last_id ORDER BY id LIMIT 1000
    if rows vacío: break
    procesar(rows); last_id = rows.último.id; persistir checkpoint(last_id)
  ```
  (complemento) Paliativo cuando hay que mantener offset (MySQL): "deferred join" — paginar sólo sobre un índice cubriente de IDs y luego unir por PK; abarata la constante, no cambia la complejidad.
- **Trade-offs y cuándo NO aplicar:**
  - Keyset pierde el salto aleatorio a la página N y el "total de páginas"; navegar hacia atrás exige invertir la query; los cursores se invalidan si cambian orden o filtros; ordenar por columnas no únicas o nullable complica el predicado.
  - OFFSET sigue siendo correcto con volumen acotado: catálogos, roles, provincias, configuración, paneles internos (~2 000 registros) donde nadie pasa de la página 5–10.
  - (complemento) `COUNT(*)` para mostrar el total también es O(n): usar estimaciones o "hay más resultados".
- **Heurísticas y umbrales:**
  - Pregunta de corte: "¿Qué pasa si alguien llega muy lejos?" — si el listado puede tener páginas profundas → keyset; si no → offset.
  - Candidatas por defecto a keyset: pedidos, transacciones, logs, eventos, feeds (crecen durante años).
  - Página 5 000 × 20 = 100 000 filas descartadas para entregar 20.
  - (complemento) Regla práctica: si el offset máximo alcanzable supera ~10⁴–10⁵ filas o la tabla no tiene cota, usar keyset.
- **Anti-patrones / señales de alerta:**
  - Helper/repositorio de paginación genérico aplicado a toda entidad sin mirar volumen.
  - `ORDER BY created_at` sin desempate único.
  - Parámetro `page` sin máximo; endpoints que listan todo el historial sin filtro obligatorio.
  - Jobs con `page++` / `skip += size`. (complemento) Peor: job que marca registros como procesados y filtra `WHERE processed = false` con offset creciente → se salta la mitad de las filas.
  - Dashboards sólo con latencia media.
  - "Ya tiene índice, está bien" frente a un `OFFSET` enorme.
- **Preguntas de revisión arquitectónica:**
  1. ¿Volumen esperado a 1–3 años y profundidad máxima navegable?
  2. ¿La clave de orden es única y existe un índice en el mismo orden y sentido?
  3. ¿El conjunto cambia mientras el usuario navega? ¿Son aceptables duplicados/saltos?
  4. ¿Algún job recorre la tabla reutilizando la paginación de la UI?
  5. ¿La API expone `page` o un cursor opaco? ¿Se puede migrar sin romper clientes?
  6. ¿Se mide p95/p99 por profundidad de página y no sólo el promedio?
- **Caso real / empresa citada:** ninguno.
- **Precisión técnica:**
  - "En producción tienes 3,000" es error de ASR/narración: el título y el offset de 100 000 implican millones de filas.
  - "El índice no corrige la paginación": correcto en complejidad; matiz: un índice cubriente/index-only scan reduce mucho la constante.
  - Comparación por tupla `(a,b) < (x,y)`: PostgreSQL y MySQL ≥ 5.7 la soportan y la resuelven con índice; SQL Server y Oracle no → forma expandida. Con sentidos mixtos (`a ASC, b DESC`) la tupla no aplica. (complemento)
  - (complemento) Keyset no evita anomalías si la clave de orden es mutable (p. ej. `updated_at`): una fila puede reaparecer.
