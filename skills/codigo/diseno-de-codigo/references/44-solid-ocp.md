# [44] SOLID: Open/Closed Principle (OCP)

> Fuente: TheDebugDuck — https://youtu.be/m_suSqqpBG4 · notas parafraseadas; «(complemento)» = conocimiento añadido o corrección.
> Estado: elaborado a partir del título y el temario público del video; la transcripción no estuvo disponible (bloqueo de YouTube, 2026-09-28). Lo que no figura en el temario es «(complemento)». Pendiente de contrastar con la transcripción.

- **Síntoma en el código/equipo:** hay que modificar el mismo código con cada funcionalidad nueva; los `if` se acumulan. (complemento) Cada transportista, medio de pago o régimen fiscal nuevo edita `PagoService.cs`; el mismo `switch (tipo)` aparece en cinco sitios y alguien olvida uno; `if (cliente == "ACME")` para casos especiales; conflictos de merge en el mismo archivo en cada sprint; regresiones en variantes que funcionaban porque se tocó su rama al añadir otra.
- **Causa raíz (mecanismo):** "abierto a extensión, cerrado a modificación": el comportamiento nuevo debería entrar **añadiendo** código, no editando el que ya funciona. Los `if` pueden romper el diseño. (complemento) El problema no es el `if` en sí, sino el **condicional por código de tipo repetido**: el conocimiento de "qué variantes existen" queda disperso, cada variante nueva edita código probado de las demás y el riesgo de regresión crece con cada rama. Un único `switch` en el borde (una fábrica que elige la implementación) es aceptable; el mismo discriminador evaluado en varios lugares no.
- **Metáfora visual propia (complemento):** el tablero de corcho frente a la pared pintada. Para añadir un aviso al corcho clavas una tarjeta nueva (extensión) sin repintar la pared (modificación) ni tocar los otros avisos. **Dónde se rompe:** alguien tuvo que colgar el corcho, y solo acepta cosas con forma de tarjeta: si el siguiente requisito es un video, el corcho no ayuda (la clausura solo protege contra el tipo de cambio que anticipaste). Y un corcho con 200 tarjetas clavadas también se vuelve ilegible.
- **Estrategias / solución:**
  1. Aplicar OCP con abstracción: una interfaz por la que entran las variantes. (complemento) *Replace Conditional with Polymorphism* (Fowler), aquí con un registro tipado:
     ```ts
     // Antes: cada transportista nuevo edita esta función (y sus switch hermanos)
     function costoEnvio(p: Pedido): number {
       switch (p.transportista) {
         case "dhl":   return 10 + p.pesoKg * 1.2;
         case "fedex": return p.pesoKg > 5 ? 25 : 15;
         case "local": return p.distanciaKm * 0.5;
         default: throw new Error(`transportista desconocido: ${p.transportista}`);
       }
     }
     // Después: una variante nueva = una entrada nueva + su test; las demás no se tocan
     type Transportista = "dhl" | "fedex" | "local";
     interface Tarifa { costo(p: Pedido): number; }
     const tarifas: Record<Transportista, Tarifa> = {
       dhl:   { costo: p => 10 + p.pesoKg * 1.2 },
       fedex: { costo: p => (p.pesoKg > 5 ? 25 : 15) },
       local: { costo: p => p.distanciaKm * 0.5 },
     };
     export const costoEnvio = (p: Pedido) => tarifas[p.transportista].costo(p);
     // Añadir "ups" al tipo unión sin su entrada no compila: exhaustividad comprobada
     ```
  2. (complemento) **Si las variantes solo difieren en valores, usa datos, no clases:** tarifas, umbrales o tasas en una tabla o configuración versionada. Una clase por país para cambiar un porcentaje es sobreingeniería.
  3. (complemento) **Eventos o hooks** cuando lo que crece es la lista de reacciones a un hecho (`PedidoConfirmado` → email, inventario, contabilidad) y no las variantes de un cálculo.
  4. (complemento) **Cuando crecen las operaciones y no las variantes, haz lo contrario:** `switch` exhaustivo sobre un tipo cerrado (unión discriminada con `never` en TS, *switch expressions* con patrones en C#). Añadir una operación toca una función; con polimorfismo tocaría todas las clases.
- **Cuándo usarlo y cuándo no:** (complemento) úsalo cuando hay **≥ 3 variantes reales** con lógica distinta (regla de tres, ver [07]) o un eje de cambio observado en el historial. No lo uses con 2 variantes estables (un `if` es más claro), para "puntos de extensión por si acaso" (YAGNI), cuando el conjunto de variantes es cerrado por naturaleza (estados de una máquina bien definida, nodos de un AST) ni cuando lo que cambia son reglas de negocio mejor expresadas como datos. Cada punto de extensión añade indirección que se paga en cada lectura y cada guardia.
- **Heurísticas y umbrales:** (complemento)
  - El mismo discriminador (`tipo`, `pais`, `plan`) en ≥ 2 `switch`/`if` distintos ⇒ candidato a polimorfismo o registro.
  - La misma función editada en ≥ 3 features recientes para añadir variantes ⇒ eje de cambio observado (`git log -L` o `git log --follow`).
  - Switch de ~40 líneas con 6 variantes reales es la señal de Strategy que da [07]; 2 ramas de 3 líneas, no.
  - Si las ramas difieren solo en constantes ⇒ tabla, no jerarquía.
- **Anti-patrones / señales en code review:** (complemento)
  - `switch` por tipo copiado en validación, cálculo, render y exportación (*Repeated Switches*).
  - Nombres de clientes o países en condicionales del dominio.
  - Interfaz `IEstrategia` con una sola implementación "para que sea extensible".
  - Registro de plugins por reflexión o escaneo de ensamblados cuando hay 3 variantes conocidas: nadie sabe qué se ejecuta.
  - Herencia profunda para extender comportamiento (plantilla sobre plantilla) en lugar de composición.
  - Feature flags que nunca se retiran: cada flag es un `if` con fecha de caducidad.
- **Preguntas de revisión:** (complemento)
  1. ¿Contra qué tipo de cambio concreto está cerrado este diseño, y ese cambio ocurrió antes?
  2. ¿Cuántas variantes reales hay hoy y cuántas más con fecha comprometida?
  3. ¿El mismo discriminador se evalúa en más de un sitio?
  4. ¿Las variantes difieren en lógica o solo en valores?
  5. ¿Crecen las variantes o crecen las operaciones sobre ellas?
  6. ¿Qué archivos toca añadir una variante nueva, y alguno contiene lógica de otras variantes?
- **Referencias (complemento):** Meyer, *Object-Oriented Software Construction* (1988), formulación original; Martin, *The Open-Closed Principle* (C++ Report, 1996); Cockburn, *Prioritizing Forces in Software Design* (PLoPD 2, 1996) y Larman, *Protected Variation: The Importance of Being Closed* (IEEE Software, 2001); Fowler, *Refactoring* 2.ª ed. (2018), *Replace Conditional with Polymorphism* y *Repeated Switches*; Wadler, *The Expression Problem* (1998); Ousterhout, *A Philosophy of Software Design* (módulos "algo generales").
- **Precisión técnica:**
  - (complemento) Ningún programa está cerrado contra todo cambio: la clausura es **estratégica** (Martin) y se elige por evidencia. Declarar un módulo "cerrado" contra cambios que nunca llegan es coste puro.
  - (complemento) En Meyer (1988) "cerrado" significaba estable y publicado para sus clientes, y la extensión era por herencia; la versión polimórfica con interfaces es de Martin (1996). No significa "prohibido editar": corregir un bug o simplificar modifica y está bien.
  - (complemento) En la práctica OCP significa que el cambio es **aditivo y localizado**, no "cero líneas modificadas": el registro o el punto de composición sí cambia.
  - (complemento) Problema de la expresión (Wadler): el polimorfismo facilita añadir variantes y dificulta añadir operaciones; el `switch` exhaustivo hace lo inverso. Elegir por el eje que más cambia es el criterio, no "polimorfismo siempre".
  - (complemento) *Protected Variations* es una formulación más útil en revisión: identifica los puntos de variación previstos y pon una interfaz estable alrededor, solo ahí.
