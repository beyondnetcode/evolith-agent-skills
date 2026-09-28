---
name: diseno-de-codigo
description: Criterio para diseñar y revisar código barato de cambiar — SOLID (SRP por actor, OCP, LSP por contratos, ISP, DIP) aplicado con evidencia, abstracción justificada frente a sobreingeniería (YAGNI, regla de tres, singletons, interfaces con una sola implementación, patrones GoF) y complejidad algorítmica (Big O temporal, espacial y amortizada; N+1, OFFSET, regex con backtracking, bucles anidados). Úsala siempre que haya code review de diseño, refactors, abstracciones o interfaces nuevas, herencia y clases base, inyección de dependencias o contenedores IoC, patrones (Strategy, Factory, Observer, Singleton), debates de "código limpio", código generado por IA "extensible", switch/if que crecen con cada funcionalidad, clases gigantes, tests difíciles de escribir o código que se vuelve lento al crecer los datos, aunque el usuario no nombre SOLID ni Big O.
license: MIT
metadata:
  categoria: codigo
  version: "1.0.0"
  idioma: es
  fuentes: "TheDebugDuck: 07, 39, 40, 41, 42, 43, 44, 45"
  relacionadas: "radar-arquitectura, estilos-arquitectonicos, datos-persistencia"
---

# Diseño de código

Conocimiento destilado de TheDebugDuck (videos 07 y 39–45) y ampliado donde el video simplifica. Tesis: **SOLID y los patrones son herramientas para abaratar el cambio que de verdad ocurre, no un dogma.** Cada abstracción cobra desde el primer día (archivos, saltos, conceptos) y solo paga si llega la variación que protege. La complejidad algorítmica es el mismo razonamiento aplicado al crecimiento de los datos: lo invisible con n pequeño es el incidente de mañana.

> Estado de las fuentes: [07] proviene de la transcripción. [39]–[45] se elaboraron a partir del título y el temario público porque la transcripción no estuvo disponible; lo que no figura en el temario está marcado «(complemento)» y queda pendiente de contrastar.

## Cómo usar esta skill

1. Clasifica la pregunta: ¿**coste de cambio** (abstracciones, herencia, dependencias, patrones) o **coste de ejecución** (crecimiento con n)? Muchas revisiones tienen ambas.
2. Reúne evidencia antes de opinar: archivo:línea de la señal; variantes reales hoy en producción; historial del archivo (quién lo cambia y por qué); n de producción y su crecimiento; saltos desde el punto de entrada hasta la regla.
3. Ubica la señal en la matriz y abre **solo** la referencia indicada.
4. Aplica el criterio de abstracción (principio 2) antes de recomendar un patrón o un principio SOLID. Si no se cumple, la recomendación es la versión directa con tests.
5. Entrega con el formato de salida. Para N+1, OFFSET e índices, deriva a `datos-persistencia`; para límites entre módulos o servicios, a `estilos-arquitectonicos`; para ReDoS en producción, a `resiliencia-operacion`; si no sabes por dónde empezar, a `radar-arquitectura`.

## Índice de referencias

| Tema | Archivo | Léelo cuando… |
|---|---|---|
| Sobreingeniería, YAGNI, regla de tres, singletons, interfaz con una implementación | `references/07-codigo-limpio-pragmatico.md` | un PR añade patrones, factories o interfaces "por si acaso"; código de IA "extensible"; debates de "código limpio" |
| Big O temporal, espacial y amortizada; N+1, OFFSET, regex, bucles anidados | `references/39-complejidad-big-o.md` | algo se vuelve lento al crecer los datos; bucles sobre colecciones que crecen; E/S dentro de bucles |
| Panorama SOLID y cuándo no aplicarlo | `references/40-solid-panorama.md` | revisión de diseño general; alguien justifica un cambio "por SOLID" |
| DIP, inyección de dependencias, contenedores IoC, puertos | `references/41-solid-dip.md` | `new` de infraestructura en el dominio; tests que necesitan BD o red; decidir qué inyectar |
| ISP, interfaces por rol de cliente | `references/42-solid-isp.md` | `NotImplementedException`; interfaces grandes; mocks con muchos stubs |
| LSP, contratos y herencia | `references/43-solid-lsp.md` | jerarquías de clases; `instanceof`/`is` en clientes; overrides que lanzan; fakes de test |
| OCP, condicionales por tipo, polimorfismo frente a `switch` | `references/44-solid-ocp.md` | el mismo `switch` en varios sitios; cada feature edita el mismo archivo |
| SRP por actor, clases dios, cohesión | `references/45-solid-srp.md` | clases grandes; conflictos de merge recurrentes; constructores con muchas dependencias |

## Principios (y por qué)

1. **Optimiza el coste del cambio que ocurre, no del que imaginas.** Una abstracción se paga en cada lectura y cada guardia; solo se amortiza si llega la variación que protege. Por eso la evidencia (historial, backlog con fecha, variantes en producción) manda sobre la intuición.
2. **Criterio explícito para abstraer (resuelve la tensión SOLID frente a YAGNI y regla de tres).** Introduce interfaz, patrón o punto de extensión solo si se cumplen las tres condiciones:
   - **≥ 2 variantes reales** hoy (o la segunda con fecha comprometida), no hipotéticas;
   - **eje de cambio observado**: el mismo punto cambió 2–3 veces por la misma razón;
   - **coste de indirección en guardia aceptable**: ≤ 3 saltos desde el punto de entrada hasta la regla, y un compañero los sigue sin que le hagan un tour.

   Si falla alguna, entrega la versión directa con tests y anota el punto de extensión candidato. **Excepción razonada:** fronteras de E/S (BD, red, reloj, proveedor externo) y contratos entre módulos o equipos; ahí el puerto paga por testabilidad y aislamiento aunque exista una sola implementación.
3. **Separa por actor y reúne por razón de cambio (SRP).** Mezclar actores hace que el cambio de uno rompa al otro; separar lo que cambia junto produce *shotgun surgery*. Las dos direcciones cuentan.
4. **Los contratos son de comportamiento (LSP).** El compilador verifica firmas, no promesas. Toda implementación, incluidos los fakes de test, acepta lo que acepta la base y garantiza lo que garantiza.
5. **Depende de poco y de lo estable (ISP + DIP).** Cada método o paquete del que dependes es otra razón para cambiar. La política de negocio posee sus puertos y habla su idioma; la infraestructura se adapta a ella.
6. **Cierra solo contra el cambio que ya viste (OCP).** La clausura es estratégica. El mismo discriminador repetido o la misma función editada en cada feature justifican polimorfismo o un registro; si crecen las operaciones y no las variantes, un `switch` exhaustivo es mejor.
7. **Módulos profundos antes que muchos superficiales.** Interfaz pequeña que esconde mucho (Ousterhout). SOLID aplicado de más produce *classitis*.
8. **Piensa en la n de producción a 24 meses y en qué cuesta una "operación".** Un round-trip de red equivale a 10⁵–10⁶ comparaciones en memoria; un cuadrático oculto en un bucle es un incidente latente. Mide antes de afinar constantes, pero no ignores el orden de crecimiento.

## Matriz "si ves X → considera Y"

| Si ves… | Principio / coste | Considera (refactor) | Cuándo NO |
|---|---|---|---|
| Archivo que editan ≥ 2 equipos por motivos distintos; conflictos de merge recurrentes | SRP | *Extract Class* por actor; duplicar el helper compartido si los actores divergen | un solo actor; la división dejaría clases de 20 líneas y más saltos |
| Constructor con > 5–7 dependencias | SRP | dividir el caso de uso por actor; servicios de fachada | composition root u orquestador delgado sin lógica |
| Un cambio pequeño toca 6–8 clases diminutas | sobredivisión (SRP de más) | *Inline Class*; agrupar por funcionalidad (*vertical slice*) | las clases responden de verdad a actores distintos |
| Mismo `switch`/`if` por tipo en ≥ 2 sitios; cada variante nueva edita el mismo archivo | OCP | *Replace Conditional with Polymorphism*; registro tipado; tabla si solo cambian valores | 2 variantes estables; variantes cerradas con operaciones que crecen (`switch` exhaustivo) |
| `is`/`instanceof`/`GetType()` en el cliente de una abstracción; override que lanza, no hace nada o endurece validaciones | LSP | capacidad en su propia interfaz; composición; resultado explícito en la base; tests de contrato | jerarquía impuesta por el framework con contrato documentado |
| Herencia para reutilizar código, no para sustituir | LSP | *Replace Superclass/Subclass with Delegate* | el framework exige heredar |
| `NotImplementedException`/`NotSupportedException`; mocks con decenas de stubs | ISP (+ LSP) | interfaces por rol de cliente; tipo función si es un solo método | un único cliente usa todo; protocolo con capacidades declaradas (`Stream.CanSeek`) |
| `new SqlConnection`, SDK de proveedor, `DateTime.Now` o `Math.random()` en la regla de negocio; tests que necesitan BD o red | DIP | puerto definido por el dominio + adaptador + inyección por constructor; `TimeProvider`; regla de arquitectura en CI | dependencia estable y pura (biblioteca estándar, value objects); script desechable |
| `GetService<T>()`/`container.resolve()` dentro del dominio | DIP (Service Locator) | inyección por constructor y cableado en el composition root | código de integración del propio framework |
| Par `IFoo`/`FooImpl` sin segunda implementación ni frontera; factory cuya configuración siempre vale lo mismo | YAGNI ([07]) | *Inline*; extraer la interfaz cuando llegue la segunda variante real | frontera de E/S o de módulo; contrato entre equipos |
| Singleton con estado mutable leído en transacciones | [07] | ciclo de vida en el contenedor + configuración inmutable o instantánea por transacción | estado de solo lectura cargado al arranque |
| PR (a menudo generado por IA) que multiplica archivos "para que sea extensible" | YAGNI + indirección | versión directa con tests; aplicar el principio 2 | ≥ 2 variantes reales ya en producción |
| `find`/`includes`/`Contains` dentro de un bucle sobre colecciones que crecen | Big O: O(n·m) | indexar antes con `Map`/`HashSet`: O(n + m) | n acotado y pequeño por naturaleza (meses, países) |
| Consulta o llamada HTTP dentro de un bucle | round-trips O(n) (N+1) | lote, `IN`, join o endpoint por lote; ver `datos-persistencia` | n ≤ 2–3 y fijo |
| `OFFSET` creciente en listados o jobs batch | O(offset) por página | keyset/cursor; ver `datos-persistencia` | tabla pequeña; se necesita saltar a una página arbitraria |
| Regex con cuantificadores anidados o `.*` que compiten, sobre entrada externa | polinómico o exponencial | motor lineal (RE2, .NET `NonBacktracking`), límite de longitud, timeout | entrada interna, corta y confiable |
| `ToList()`/`Array.from` de todo el resultado antes de procesarlo | espacio O(n) | streaming (`IAsyncEnumerable`, cursores) o lotes | volumen acotado que cabe holgado en memoria |
| `reduce` con spread del acumulador; `string +=` en bucle (C#/Java) | O(n²) oculto | acumulador local mutable; `StringBuilder` | decenas de elementos |

## Preguntas de revisión

1. ¿Qué cambio real, con fecha o con historial, abarata este diseño? ¿Cuántas variantes existen hoy en producción?
2. ¿Cuántos saltos hay desde el punto de entrada hasta la regla de negocio? ¿Un compañero los sigue solo durante una guardia?
3. ¿Qué actores o equipos piden cambios a este módulo, y qué muestran los últimos commits?
4. ¿Hay comprobaciones de tipo concreto en clientes, overrides que lanzan o fakes que no cumplen el contrato del adaptador real?
5. ¿Qué implementaciones lanzan o ignoran métodos de su interfaz? ¿Qué métodos usa cada cliente?
6. ¿Quién posee cada interfaz: el módulo que la usa o el que la implementa? ¿El dominio compila y se prueba sin infraestructura?
7. ¿El mismo discriminador se evalúa en más de un sitio? ¿Crecen las variantes o las operaciones?
8. ¿Cuál es n en producción hoy y en 24 meses? ¿Hay búsqueda lineal o E/S dentro de un bucle que crece con los datos?
9. ¿Se midió con volumen realista (prueba de duplicación n → 2n) o solo con fixtures pequeños?
10. ¿Qué borraríamos sin perder funcionalidad?

## Precisiones (no las repitas)

- **SRP no es "una clase hace una sola cosa"**: es "un módulo responde a un único actor" (una razón de cambio). "Hacer una sola cosa" es una guía para funciones.
- **LSP es de comportamiento y contratos, no de firmas**: precondiciones no más fuertes, postcondiciones no más débiles, invariantes y restricción histórica preservadas. Compilar no prueba nada: la covarianza de arrays en C#/Java y la bivarianza de métodos en TypeScript compilan y fallan en ejecución.
- **DIP ≠ inyección de dependencias ≠ contenedor IoC.** DIP trata de la dirección de las dependencias y de quién posee la abstracción; DI es una técnica; el contenedor, una herramienta. Hay DI sin DIP y DIP sin contenedor.
- **OCP no es "no editar nunca"**: ningún código está cerrado contra todo cambio; la clausura es estratégica y el registro o el composition root sí cambian. El polimorfismo facilita variantes nuevas y dificulta operaciones nuevas (problema de la expresión).
- **ISP trata de las dependencias del cliente**, no de "interfaces pequeñas" como fin; una interfaz amplia que su único cliente usa entera es correcta.
- **"Escalable" en SOLID es escalar el desarrollo**, no el throughput: SOLID no hace que un sistema aguante más carga.
- **Una interfaz con una sola implementación no siempre es sobreingeniería**: en fronteras de E/S, de módulo o entre equipos está justificada; en el interior de un módulo, casi nunca.
- **Big O mide crecimiento, no tiempo**: O(1) no es "rápido"; el hash es O(1) esperado con peor caso O(n); amortizado ≠ promedio; las constantes mandan con n pequeño y cuando la "operación" es E/S.
- **SOLID no es exclusivo de la orientación a objetos**: aplica a funciones, módulos, paquetes y servicios. El acrónimo es de Michael Feathers (~2004); OCP viene de Meyer (1988) y LSP de Liskov (1987; con Wing, 1994).
- **La duplicación no siempre es deuda**: DRY trata de conocimiento, no de líneas iguales. Duplicar entre actores cuyas reglas coinciden por casualidad es correcto, y es más barato que la abstracción equivocada (Metz).

## Formato de salida

```
Veredicto: <mantener | simplificar | refactorizar | medir primero>, en una línea.
Evidencia: <archivo:línea de la señal; variantes reales; historial de cambios; n de producción>.
Principio o coste en juego: <SRP | OCP | LSP | ISP | DIP | YAGNI | Big O> y el cambio concreto que abarata o encarece.
Propuesta: <refactor nombrado (Fowler) + antes/después en ≤ 12 líneas>.
Coste de indirección: <archivos y saltos que se añaden o quitan; ¿se sigue en una guardia?>.
Cuándo NO / reversión: <condición en la que esto sobra y cómo deshacerlo>.
Verificación: <tests de contrato, regla de arquitectura en CI, prueba de duplicación con n realista>.
Fuente: <referencia(s) y video(s)>; indica si la referencia se elaboró solo desde el temario.
```
