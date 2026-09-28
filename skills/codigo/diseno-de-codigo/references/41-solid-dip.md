# [41] SOLID: Dependency Inversion Principle (DIP)

> Fuente: TheDebugDuck — https://youtu.be/TEuVwJDmmnc · notas parafraseadas; «(complemento)» = conocimiento añadido o corrección.
> Estado: elaborado a partir del título y el temario público del video; la transcripción no estuvo disponible (bloqueo de YouTube, 2026-09-28). Lo que no figura en el temario es «(complemento)». Pendiente de contrastar con la transcripción.

- **Síntoma en el código/equipo:** código difícil de cambiar, probar o escalar porque depende de implementaciones concretas. (complemento) `new SqlConnection(...)`, `new SmtpClient()`, `HttpClient` estático, `DateTime.Now` o el SDK de Stripe/AWS dentro de la lógica de negocio; los tests necesitan una BD real o no existen; cambiar de proveedor de email toca 40 archivos; el proyecto de dominio referencia al de infraestructura; tests lentos e intermitentes porque dependen del reloj o de la red.
- **Causa raíz (mecanismo):** depender de implementaciones en lugar de abstracciones acopla la política al detalle. (complemento) La formulación de Martin tiene dos partes: (A) los módulos de alto nivel no dependen de los de bajo nivel; ambos dependen de abstracciones; (B) las abstracciones no dependen de detalles; los detalles dependen de abstracciones. Lo que se **invierte** es la dirección de la dependencia de código fuente y la **propiedad** de la abstracción: el flujo de control sigue yendo del caso de uso a la BD, pero la interfaz la define y la posee el dominio, en sus términos, y la infraestructura la implementa. Si la interfaz vive junto al adaptador y copia el SDK método a método, no se invirtió nada: solo se añadió un archivo.
- **Metáfora visual propia (complemento):** la ficha técnica del restaurante. El restaurante escribe qué necesita ("harina 000, sacos de 25 kg, entrega martes antes de las 8") y cualquier proveedor que cumpla la ficha puede abastecerlo; el menú no se reescribe según el catálogo de un molino concreto. **Dónde se rompe:** la ficha no captura todo: un proveedor en memoria y uno SQL cumplen la misma firma pero difieren en transacciones, concurrencia y orden (abstracción con fugas). Y si el restaurante tendrá un único proveedor para siempre y no necesita probar sin él, la ficha es burocracia.
- **Estrategias / solución:**
  1. (complemento) **Puerto definido por el caso de uso, adaptador en infraestructura, inyección por constructor, cableado en un único punto de composición:**
     ```csharp
     // Antes: la regla conoce SQL, SMTP y el reloj del sistema
     public class FacturaService {
       public void Emitir(Factura f) {
         if (DateTime.Now > f.Vencimiento) f.MarcarVencida();
         using var db = new SqlConnection(Config.Cs); db.Execute("INSERT ...", f);
         new SmtpClient("smtp.local").Send("facturas@x.com", f.Email, "Factura", "...");
       }
     }
     // Después: el dominio posee IFacturas e INotificador; SqlFacturas y SmtpNotificador
     // viven en Infraestructura y se registran en Program.cs (composition root)
     public interface IFacturas { Task Guardar(Factura f); }
     public interface INotificador { Task FacturaEmitida(Factura f); }
     public sealed class EmitirFactura(IFacturas facturas, INotificador notificador, TimeProvider reloj) {
       public async Task Ejecutar(Factura f) {
         if (reloj.GetUtcNow() > f.Vencimiento) f.MarcarVencida();
         await facturas.Guardar(f);
         await notificador.FacturaEmitida(f);
       }
     }
     ```
  2. (complemento) **Nombra el puerto por el dominio, no por el proveedor:** `INotificador.FacturaEmitida`, no `ISendGridClient.SendTemplate`. Tipos del dominio en la firma; nada de `DbDataReader`, `SqlException` ni `AxiosResponse` cruzando el puerto.
  3. (complemento) **La abstracción no tiene que ser una interfaz:** un tipo función (`(f: Factura) => Promise<void>`), una clase abstracta o un módulo también sirven. En TypeScript, el tipado estructural permite pasar cualquier objeto con la forma correcta sin `implements`.
  4. (complemento) **Haz cumplir la dirección** con reglas de arquitectura en CI: NetArchTest o ArchUnitNET (.NET), ArchUnit (Java), dependency-cruiser o eslint-plugin-boundaries (TS). "Dominio no referencia Infraestructura" como test, no como wiki.
  5. (complemento) **Tests de contrato del puerto:** la misma batería corre contra el fake en memoria y contra el adaptador real (p. ej., con Testcontainers) para detectar las fugas de la metáfora.
- **Trade-offs y cuándo NO aplicar:** reducir acoplamiento tiene precio. (complemento) Cada puerto añade un archivo y un salto. No inviertas dependencias **estables y puras**: la biblioteca estándar, `string`, colecciones, value objects propios, funciones de cálculo sin E/S. Una interfaz con una sola implementación en el interior de un módulo es sobreingeniería (ver [07]); en una frontera de E/S o de módulo, en cambio, el puerto paga por testabilidad y por aislar un proveedor volátil. Si el equipo prueba con la BD real en contenedores y el proveedor no cambiará, el puerto puede esperar.
- **Heurísticas y umbrales:** (complemento)
  - Invierte cuando la dependencia es **E/S** (BD, red, sistema de archivos, reloj, aleatoriedad), **volátil** (proveedor externo, SDK que cambia) o **cruza una frontera** de módulo o capa.
  - No inviertas lo que no cumple ninguna de las tres.
  - Constructor con más de 5–7 dependencias: el problema es de SRP, no de DIP (ver [45]); agrupa en servicios de fachada o divide el caso de uso.
  - El dominio debe compilar y testearse sin referenciar ningún paquete de infraestructura.
- **Anti-patrones / señales en code review:** (complemento)
  - Interfaz en el paquete de infraestructura que copia el SDK 1:1 (*header interface*): se inyecta pero no se invierte.
  - Abstracción con fugas: excepciones, tipos o semántica del proveedor en la firma del puerto.
  - *Service Locator*: `provider.GetService<T>()` o `container.resolve()` dentro del dominio; oculta dependencias y rompe en ejecución.
  - `DateTime.Now`, `Guid.NewGuid()`, `Math.random()` o variables de entorno leídas en la regla de negocio.
  - Mocks de todo, incluso de colaboradores puros: tests acoplados a la implementación que se rompen en cada refactor.
  - Contenedor IoC con registros por convención que nadie entiende; errores de resolución solo en producción.
- **Preguntas de revisión:** (complemento)
  1. ¿Quién posee la interfaz: el módulo que la usa o el que la implementa?
  2. ¿La firma del puerto habla el lenguaje del dominio o el del proveedor?
  3. ¿Se puede ejecutar la regla de negocio en un test sin red, BD ni reloj real?
  4. ¿Qué regla automática impide que el dominio importe infraestructura?
  5. ¿El fake y el adaptador real pasan la misma batería de tests de contrato?
  6. ¿Esta dependencia es de E/S, volátil o de frontera? Si no, ¿por qué se invierte?
- **Referencias (complemento):** Martin, *The Dependency Inversion Principle* (C++ Report, 1996) y *Clean Architecture* (2017, regla de dependencia); Fowler, *Inversion of Control Containers and the Dependency Injection pattern* (2004); Seemann y van Deursen, *Dependency Injection Principles, Practices, and Patterns* (2019; Pure DI y Service Locator como anti-patrón); Cockburn, *Hexagonal Architecture* (2005); Spolsky, *The Law of Leaky Abstractions* (2002); Ousterhout, *A Philosophy of Software Design* (módulos profundos).
- **Precisión técnica:**
  - (complemento) **DIP ≠ inyección de dependencias ≠ contenedor IoC.** DIP es un principio sobre la dirección de las dependencias y la propiedad de las abstracciones; DI es una técnica (recibir las dependencias desde fuera: constructor, parámetro); el contenedor es una herramienta que automatiza DI. Hay DI sin DIP (inyectar un `SqlFacturas` concreto), DIP sin contenedor (cableado manual o *Pure DI*) y contenedores que esconden violaciones de DIP.
  - (complemento) IoC es más amplio que DI: incluye frameworks que llaman a tu código (callbacks, plantillas, eventos).
  - (complemento) DIP no elimina el acoplamiento semántico: si el caso de uso asume que `Guardar` es transaccional con otra escritura, la interfaz no lo expresa ni lo garantiza.
  - (complemento) En TypeScript las interfaces se borran en ejecución: los contenedores (NestJS, InversifyJS) necesitan tokens o clases abstractas como clave de inyección.
  - (complemento) "Escalar" en el temario se entiende como escalar el equipo y los tests; DIP no mejora el rendimiento en ejecución.
