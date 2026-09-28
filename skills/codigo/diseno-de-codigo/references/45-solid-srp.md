# [45] SOLID: Single Responsibility Principle (SRP)

> Fuente: TheDebugDuck — https://youtu.be/1pXHglGZY9A · notas parafraseadas; «(complemento)» = conocimiento añadido o corrección.
> Estado: elaborado a partir del título y el temario público del video; la transcripción no estuvo disponible (bloqueo de YouTube, 2026-09-28). Lo que no figura en el temario es «(complemento)». Pendiente de contrastar con la transcripción.

- **Síntoma en el código/equipo:** código que se vuelve difícil de mantener con el tiempo; clases mal diseñadas. (complemento) `PedidoService` de 2.000 líneas con 15 dependencias en el constructor; equipos distintos (finanzas, logística, marketing) editan el mismo archivo y chocan en cada merge; corregir una regla fiscal rompe un reporte; probar un cálculo exige montar BD, email y colas; nombres como `Manager`, `Helper`, `Utils` o `ProcesarYEnviar`; el historial muestra commits por motivos que no tienen nada que ver entre sí.
- **Causa raíz (mecanismo):** una clase con más de una razón para cambiar. (complemento) Martin afinó la definición con los años: "razón para cambiar" significa **actor**, es decir, la persona o grupo que pide el cambio (*Clean Architecture*, 2017: un módulo responde a un único actor). Cuando código de dos actores convive y comparte piezas, el cambio pedido por uno altera el comportamiento del otro sin que nadie lo note. El ejemplo canónico: una clase `Empleado` con `CalcularPago()` (Finanzas), `ReporteHoras()` (Recursos Humanos) y `Guardar()` (plataforma/DBA), que comparten un helper `HorasRegulares()`; Finanzas ajusta el helper y el reporte de RR. HH. sale mal. La raíz es la de Parnas (1972): descomponer por **decisiones que pueden cambiar**, no por pasos del proceso.
- **Metáfora visual propia (complemento):** el empleado con tres jefes. Finanzas, RR. HH. y Sistemas le piden cambios por su cuenta; cuando cumple el pedido de uno, incumple sin querer lo que prometió a otro. Con un jefe por puesto, cada cambio tiene un único dueño. **Dónde se rompe:** en software "contratar" dos clases más casi no cuesta, pero cada división añade navegación y coordinación; y una persona arbitra conflictos entre jefes mientras que el código no. Además, en un equipo de tres personas donde todos son "todos los actores", el criterio por actor se degrada: usa entonces la frecuencia y el motivo de cambio observados.
- **Estrategias / solución:**
  1. Identificar las razones de cambio y refactorizar aplicando SRP. (complemento) Lista los actores que piden cambios; agrupa métodos y campos por actor; *Extract Class* (Fowler) por cada grupo; si hace falta mantener la API existente, deja una fachada delgada que delega:
     ```csharp
     // Antes: tres actores, un archivo, un helper compartido
     public class Empleado {
       public decimal CalcularPago() => HorasRegulares() * Tarifa;          // Finanzas
       public string ReporteHoras() => $"{Nombre}: {HorasRegulares()} h";   // RR. HH.
       public void Guardar() { /* SQL */ }                                    // Plataforma
       private decimal HorasRegulares() { /* regla compartida */ }
     }
     // Después: datos simples + una clase por actor; cada una con su propia regla de horas
     public sealed record Empleado(string Id, string Nombre, decimal Tarifa, IReadOnlyList<Jornada> Jornadas);
     public sealed class CalculadoraDePago   { public decimal Calcular(Empleado e) { /* ... */ } }  // Finanzas
     public sealed class ReporteDeHoras      { public string Generar(Empleado e) { /* ... */ } }    // RR. HH.
     public sealed class EmpleadoRepositorio { public Task Guardar(Empleado e) { /* ... */ } }      // Plataforma
     ```
  2. (complemento) **Acepta la duplicación entre actores** cuando sus reglas solo coinciden hoy por casualidad (duplicación accidental): unificar el helper vuelve a acoplarlos.
  3. (complemento) **Agrupa además de separar:** lo que cambia por la misma razón va junto aunque esté en capas distintas (cohesión por funcionalidad o *vertical slice*); separar una regla en controlador, servicio, mapper y repositorio que siempre cambian a la vez es el problema inverso.
  4. (complemento) Constructor con muchas dependencias: divide el caso de uso por actor o agrupa colaboradores en servicios de fachada (Seemann).
- **Trade-offs y cuándo NO aplicar:** (complemento) dividir de más produce *classitis* (Ousterhout) y el síntoma inverso, *shotgun surgery*: un cambio pequeño toca 8 clases diminutas (ver [07]). No dividas un módulo con un solo actor aunque "haga varias cosas", ni una clase cohesiva de 150 líneas en seis de 25. Un archivo largo no es por sí mismo una violación: lo es si cambia por motivos de actores distintos.
- **Heurísticas y umbrales:** (complemento)
  - ≥ 2 actores o equipos distintos editaron el mismo archivo por motivos distintos en el último trimestre ⇒ candidato.
  - Grupos de métodos que usan subconjuntos disjuntos de campos (baja cohesión, métrica LCOM) ⇒ clases escondidas.
  - Más de 5–7 dependencias en el constructor ⇒ probablemente varios actores.
  - Prueba del "y": si describir la clase exige "calcula el pago **y** genera el reporte **y** persiste", hay varias responsabilidades.
  - *Hotspots* (Tornhill): archivos con mucho *churn* y mucha complejidad son el primer sitio donde buscar.
- **Anti-patrones / señales en code review:** (complemento)
  - Clase dios o `*Manager`/`*Utils` que crece en cada PR.
  - Método privado compartido por reglas de actores distintos.
  - Entidad que se valida, se persiste, se serializa a JSON y se envía por email.
  - Separar por capa técnica cosas que siempre cambian juntas (controlador, servicio y repositorio con un solo método cada uno que se pasan el mismo DTO).
  - Dividir por tamaño (máximo de líneas) en lugar de por razón de cambio.
- **Preguntas de revisión:** (complemento)
  1. ¿Quién pide cambios a este módulo? Nombra actores o equipos, no funciones.
  2. ¿Qué commits recientes lo tocaron y por qué motivo cada uno?
  3. ¿Hay código compartido entre reglas de actores distintos que podría divergir?
  4. ¿Un cambio típico toca solo este módulo o también otros cinco (sobredivisión)?
  5. ¿Se puede probar la regla de un actor sin preparar las de los demás?
- **Referencias (complemento):** Martin, *Agile Software Development: Principles, Patterns, and Practices* (2002); Martin, *The Single Responsibility Principle* (blog Clean Coder, 2014); Martin, *Clean Architecture* (2017), cap. 7; Parnas, *On the Criteria To Be Used in Decomposing Systems into Modules* (CACM, 1972); Dijkstra, *On the role of scientific thought* (1974, separación de asuntos); Fowler, *Refactoring* 2.ª ed. (2018), *Extract Class*, *Divergent Change* y *Shotgun Surgery*; Ousterhout, *A Philosophy of Software Design* (classitis, módulos profundos); Chidamber y Kemerer, *A Metrics Suite for Object Oriented Design* (IEEE TSE, 1994), LCOM; Tornhill, *Your Code as a Crime Scene* (2015; 2.ª ed. 2024).
- **Precisión técnica:**
  - (complemento) **SRP no es "una clase hace una sola cosa".** "Hacer una sola cosa" es una guía para **funciones** (*Clean Code*); SRP habla de **razones de cambio = actores**. Una clase puede tener diez métodos y cumplir SRP si todos responden al mismo actor.
  - (complemento) SRP incluye **reunir**, no solo separar: juntar lo que cambia por las mismas razones (a nivel de componentes, el *Common Closure Principle*).
  - (complemento) *Divergent change* (un módulo cambia por muchos motivos) es la señal de SRP; *shotgun surgery* (un motivo cambia muchos módulos) es la señal contraria, a menudo producida por aplicar SRP de más.
  - (complemento) Aplica a cualquier módulo (función, clase, paquete, servicio), no solo a clases.
  - (complemento) La duplicación entre actores no siempre es un defecto: DRY trata de conocimiento, no de líneas iguales.
