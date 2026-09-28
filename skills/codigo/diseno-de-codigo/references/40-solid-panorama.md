# [40] SOLID explicado en 10 minutos

> Fuente: TheDebugDuck — https://youtu.be/0XBA8X4qvEA · notas parafraseadas; «(complemento)» = conocimiento añadido o corrección.
> Estado: elaborado a partir del título y el temario público del video; la transcripción no estuvo disponible (bloqueo de YouTube, 2026-09-28). Lo que no figura en el temario es «(complemento)». Pendiente de contrastar con la transcripción.

- **Síntoma en el código/equipo:** código difícil de mantener, rígido y que no escala con el proyecto (SOLID se presenta como el camino a código mantenible, flexible y escalable). (complemento) Se nota en dos direcciones opuestas:
  - **Falta de diseño:** un cambio pequeño toca 8 archivos (*shotgun surgery*); un archivo que todos los equipos editan y genera conflictos de merge cada semana; tests imposibles sin base de datos; miedo a tocar "la clase de 3.000 líneas".
  - **Exceso de diseño:** SOLID usado como checklist produce 12 archivos para un `if` (ver [07]); PRs con interfaces de una sola implementación "porque SOLID lo dice".
- **Causa raíz (mecanismo):** los cinco principios (SRP, OCP, LSP, ISP, DIP). (complemento) Son heurísticas para **gestionar dependencias** alineando acoplamiento y cohesión con los ejes por los que el código cambia de verdad. Cada uno ataca un tipo de coste:

  | Principio | Pregunta que hace | Coste que evita |
  |---|---|---|
  | SRP | ¿Cuántos actores piden cambios a este módulo? | Que el cambio de un actor rompa a otro |
  | OCP | ¿Añadir una variante exige editar código estable? | Regresiones en variantes que ya funcionaban |
  | LSP | ¿Cualquier implementación cumple el contrato que el cliente asume? | Fallos en ejecución que el compilador no ve |
  | ISP | ¿El cliente depende de métodos que no usa? | Recompilar, redesplegar o mockear lo irrelevante |
  | DIP | ¿La política de negocio conoce detalles de E/S? | No poder probar ni cambiar proveedor sin tocar el dominio |

- **Metáfora visual propia (complemento):** la instalación eléctrica de una casa. **SRP:** circuitos separados en el tablero (cocina, iluminación) para que un cortocircuito en uno no apague el otro. **OCP:** una regleta: añades aparatos sin recablear la pared. **LSP:** un adaptador que encaja en el enchufe pero entrega 220 V a un aparato de 110 V: "compila" y quema. **ISP:** nadie instala un conector de 20 pines para una lámpara. **DIP:** la casa define el enchufe estándar y cualquier fabricante se adapta a él, no al revés. **Dónde se rompe:** en una casa el estándar ya existe y es gratis; en software el enchufe lo diseñas tú, y si lo diseñas antes de tener dos aparatos reales, diseñas el enchufe equivocado. Además cada enchufe añade un salto que alguien tendrá que seguir durante una guardia.
- **Estrategias / solución:**
  1. (complemento) **Úsalo como diagnóstico, no como receta de construcción:** parte de un síntoma observado y busca el principio que lo explica (ver la matriz del `SKILL.md`), nunca al revés.
  2. (complemento) **Orden práctico:** SRP primero (separar por actor suele bastar); DIP en las fronteras de E/S; OCP solo en el eje de variación observado; ISP cuando los clientes de una interfaz divergen; LSP como verificación en cada herencia o implementación.
  3. (complemento) Ejemplo mínimo de los cinco a la vez:
     ```csharp
     // Antes: un servicio que calcula, persiste, notifica y decide por tipo
     public class PedidoService {
       public void Confirmar(Pedido p) {
         p.Total = p.Tipo == "B2B" ? p.Subtotal * 0.9m : p.Subtotal;   // regla de Ventas
         using var db = new SqlConnection(Config.Cs); db.Execute("UPDATE ...", p); // detalle de E/S
         new SmtpClient("smtp.local").Send("ventas@x.com", p.Email, "Confirmado", "..."); // otro actor
       }
     }
     // Después: regla pura por actor, puertos definidos por el dominio, variantes solo si existen
     public sealed class ConfirmarPedido(IPedidos pedidos, IAvisos avisos, IPolitica politica) {
       public async Task Ejecutar(Pedido p) {
         p.FijarTotal(politica.Total(p));   // IPolitica solo si hay ≥ 2 políticas reales
         await pedidos.Guardar(p);         // IPedidos: puerto del dominio, adaptador SQL fuera
         await avisos.PedidoConfirmado(p); // IAvisos: lo que el caso de uso necesita, no el SDK
       }
     }
     ```
  4. (complemento) Mide el resultado en coste de cambio: archivos tocados por feature, conflictos de merge, tiempo de los tests, saltos hasta la regla de negocio.
- **Trade-offs y cuándo NO aplicar:** (complemento) cada principio añade tipos e indirección; aplicados en exceso producen *classitis* (Ousterhout): muchas clases superficiales cuya interfaz es casi tan compleja como su implementación. Los principios chocan entre sí y con YAGNI/KISS: maximizar OCP multiplica abstracciones que SRP y la legibilidad pagan. No aplican con igual peso en scripts, prototipos, código desechable ni dominios estables. En código funcional o módulos pequeños, funciones y tipos ya dan buena parte de estas propiedades sin ceremonia.
- **Heurísticas y umbrales:** (complemento)
  - Aplica un principio solo si puedes nombrar **el cambio concreto que abarata**: ≥ 2 variantes reales hoy, o un eje de cambio observado en `git log` (el mismo punto editado ≥ 3 veces por la misma razón).
  - Si el refactor sube de 3 los saltos desde el punto de entrada hasta la regla, justifica el coste por escrito (ver [07]).
  - Alternativa de lectura: CUPID (Dan North, 2022) propone propiedades del código (componible, filosofía Unix, predecible, idiomático, basado en el dominio) en lugar de reglas.
- **Anti-patrones / señales en code review:** (complemento)
  - "Lo hice así por SOLID" sin decir qué cambio abarata.
  - Pares `IFoo`/`FooImpl` en todo el proyecto; factories con una sola variante.
  - Lo contrario: clases dios, `switch` por tipo repetidos, `new` de infraestructura dentro del dominio, `instanceof` en clientes.
  - Revisión que discute nombres de principios en lugar de coste de cambio y evidencia.
- **Preguntas de revisión:** (complemento)
  1. ¿Qué cambio real (con fecha o historial) se vuelve más barato con este diseño?
  2. ¿Qué actores piden cambios a este módulo y cuántos equipos lo editan?
  3. ¿Cuántas variantes existen hoy en producción?
  4. ¿Qué detalle de infraestructura conoce la lógica de negocio?
  5. ¿Cuántos saltos hay desde el punto de entrada hasta la regla, y un compañero los sigue solo en una guardia?
- **Referencias (complemento):** Martin, *Design Principles and Design Patterns* (2000) y *Agile Software Development: Principles, Patterns, and Practices* (2002); Martin, *Clean Architecture* (2017); Meyer, *Object-Oriented Software Construction* (1988); Liskov y Wing, *A Behavioral Notion of Subtyping* (ACM TOPLAS, 1994); Parnas, *On the Criteria To Be Used in Decomposing Systems into Modules* (CACM, 1972); Fowler, *Refactoring* 2.ª ed. (2018); Ousterhout, *A Philosophy of Software Design* (2018; 2.ª ed. 2021); Dan North, *CUPID — for joyful coding* (2022).
- **Precisión técnica:**
  - (complemento) Martin recopiló y nombró los principios (artículos de 1996 y el ensayo de 2000); el acrónimo SOLID lo propuso Michael Feathers hacia 2004. OCP es de Meyer (1988) y LSP de Liskov (1987; formalizado con Wing en 1994).
  - (complemento) "Escalable" en SOLID es escalabilidad **del desarrollo** (más personas y funcionalidades con coste de cambio acotado), no rendimiento bajo carga. SOLID no hace que un sistema aguante más peticiones; para eso ver [39] y las skills de datos y operación.
  - (complemento) SOLID no es exclusivo de la orientación a objetos: se traduce a módulos, funciones y servicios (DIP ≈ puertos y adaptadores; ISP ≈ APIs por cliente o BFF; SRP ≈ límites por capacidad de negocio).
  - (complemento) No son leyes ni se maximizan a la vez; son heurísticas con coste. Tratarlos como reglas binarias es la causa de la sobreingeniería que describe [07].
