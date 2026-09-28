# [43] SOLID: Liskov Substitution Principle (LSP)

> Fuente: TheDebugDuck — https://youtu.be/DAlfu9_h6FE · notas parafraseadas; «(complemento)» = conocimiento añadido o corrección.
> Estado: elaborado a partir del título y el temario público del video; la transcripción no estuvo disponible (bloqueo de YouTube, 2026-09-28). Lo que no figura en el temario es «(complemento)». Pendiente de contrastar con la transcripción.

- **Síntoma en el código/equipo:** código que compila pero falla en ejecución al reemplazar una clase por otra; errores comunes con herencia. (complemento) `if (x is CuentaPlazoFijo)`, `instanceof` o `GetType()` en el código cliente; overrides que lanzan, no hacen nada o añaden validaciones que la base no tenía; tests que pasan con la clase base y fallan con una subclase; bugs que solo aparecen con una implementación (el repositorio en memoria de los tests ignora mayúsculas y el de SQL no, o viceversa).
- **Causa raíz (mecanismo):** una subclase o implementación que no puede reemplazar a su tipo base sin romper al cliente. (complemento) El compilador solo verifica **firmas**; LSP exige **comportamiento**. Liskov y Wing (1994): toda propiedad demostrable de los objetos del tipo base debe seguir siendo cierta para los del subtipo. En términos de contrato (Meyer, diseño por contrato):
  - **Precondiciones:** el subtipo no puede exigir más (no puede rechazar entradas que la base aceptaba).
  - **Postcondiciones:** el subtipo no puede garantizar menos (no puede devolver o dejar menos de lo prometido).
  - **Invariantes:** se preservan.
  - **Restricción histórica:** el subtipo no permite cambios de estado que la base prohibía (un subtipo mutable de un tipo inmutable la viola).
  - **Excepciones:** no lanza tipos nuevos que el cliente no espera.
- **Metáfora visual propia (complemento):** la pieza de repuesto que encaja en los mismos tornillos (firma) pero soporta menos presión (precondición más fuerte) o entrega menos caudal (postcondición más débil): el mecánico la monta sin problemas y revienta en la autopista. **Dónde se rompe:** en ingeniería la presión nominal está escrita en la pieza; en software el contrato casi nunca está escrito y vive en lo que los clientes asumen (ley de Hyrum), así que "cumplir la especificación" no basta. Además sugiere que "más fuerte siempre es seguro", y un subtipo que hace más (registra en un servicio remoto, añade estado) puede añadir latencia, fallos o mutaciones que el cliente no esperaba.
- **Estrategias / solución:**
  1. (complemento) **Detectar:** busca comprobaciones de tipo en clientes, overrides que lanzan o endurecen validaciones, y documentación del estilo "funciona igual excepto si…".
  2. (complemento) **Separar la capacidad en lugar de heredarla**, para que el tipo diga qué puede hacer cada objeto:
     ```csharp
     // Antes: el subtipo endurece la precondición de Retirar
     public class Cuenta {
       public decimal Saldo { get; protected set; }
       public virtual void Retirar(decimal monto) => Saldo -= monto;
     }
     public class CuentaPlazoFijo : Cuenta {
       public DateTime Vencimiento { get; init; }
       public override void Retirar(decimal monto) {
         if (DateTime.UtcNow < Vencimiento) throw new InvalidOperationException("Bloqueada");
         base.Retirar(monto);
       }
     }
     void CobrarComision(IEnumerable<Cuenta> cuentas) { foreach (var c in cuentas) c.Retirar(5m); } // explota en ejecución
     // Después: solo las cuentas retirables prometen Retirar; el compilador impide el error
     public interface IRetirable { void Retirar(decimal monto); }
     public sealed class CuentaCorriente : Cuenta, IRetirable { public void Retirar(decimal m) => Saldo -= m; }
     public sealed class CuentaPlazoFijo : Cuenta { public void Liquidar(DateTimeOffset hoy) { /* ... */ } }
     void CobrarComision(IEnumerable<IRetirable> cuentas) { foreach (var c in cuentas) c.Retirar(5m); }
     ```
  3. (complemento) **Alternativa: hacer explícito el contrato en la base** para que todos los clientes lo manejen: `Resultado Retirar(decimal monto)` con motivo de rechazo, en lugar de una excepción que solo lanza una subclase.
  4. (complemento) **Composición en lugar de herencia** cuando la subclase hereda para reutilizar código y no para ser sustituible (*Replace Subclass/Superclass with Delegate*, Fowler).
  5. (complemento) **Tests de contrato:** una batería abstracta que se ejecuta contra cada implementación (incluidos los fakes de test); con pruebas basadas en propiedades si el contrato es algebraico (p. ej., "guardar y luego leer devuelve lo mismo").
- **Trade-offs y cuándo NO aplicar:** (complemento) separar capacidades multiplica tipos; si solo existe una implementación y ningún cliente polimórfico, no hay sustitución que proteger. Algunos frameworks imponen jerarquías (controladores, componentes de UI): respeta su contrato documentado. Los contratos con capacidades declaradas (`Stream.CanSeek`) son aceptables si los clientes las consultan; el problema es la sorpresa, no la variación.
- **Heurísticas y umbrales:** (complemento)
  - Cualquier `is`/`instanceof`/`switch` sobre el tipo concreto en un cliente de una abstracción es una violación hasta que se demuestre lo contrario.
  - Override que lanza una excepción nueva, añade un `if` de validación o deja el cuerpo vacío: revisar.
  - Prefiere clases `sealed`/`final` por defecto; abre la herencia solo con el contrato de extensión documentado.
  - Pregunta "¿es-un?" en términos de **comportamiento** ("¿se comporta como?"), no de taxonomía del mundo real.
- **Anti-patrones / señales en code review:** (complemento)
  - Cuadrado que hereda de Rectángulo mutable con `SetAncho`/`SetAlto` independientes.
  - Colecciones de solo lectura que implementan la interfaz mutable y lanzan en `Add` (`ReadOnlyCollection<T>` vía `ICollection<T>`, `List.of` o `Arrays.asList` en Java).
  - Herencia por reutilización: `Stack extends Vector` y `Properties extends Hashtable` en Java permiten operaciones que rompen su propio concepto.
  - Fakes de test que no respetan el contrato del adaptador real (orden, unicidad, transacciones).
  - Subclase que cambia unidades, zona horaria o redondeo del resultado de la base.
- **Preguntas de revisión:** (complemento)
  1. ¿Qué asume el cliente sobre este método (entradas aceptadas, resultado, efectos, excepciones)? ¿Está escrito?
  2. ¿Alguna implementación acepta menos, promete menos o lanza algo distinto?
  3. ¿Hay comprobaciones de tipo concreto en el código que usa la abstracción?
  4. ¿La herencia existe para sustituir o solo para reutilizar código?
  5. ¿Todas las implementaciones, incluidos los fakes, pasan la misma batería de tests de contrato?
- **Referencias (complemento):** Liskov, *Data Abstraction and Hierarchy* (keynote OOPSLA 1987; SIGPLAN Notices, 1988); Liskov y Wing, *A Behavioral Notion of Subtyping* (ACM TOPLAS 16(6), 1994); Meyer, *Object-Oriented Software Construction* (1988; 2.ª ed. 1997), diseño por contrato; Martin, *The Liskov Substitution Principle* (C++ Report, 1996); Fowler, *Refactoring* 2.ª ed. (2018), *Refused Bequest* y *Replace Superclass with Delegate*; Bloch, *Effective Java* ("favorecer composición sobre herencia"); Gamma et al., *Design Patterns* (1994), cap. 1.
- **Precisión técnica:**
  - (complemento) LSP es de **comportamiento y contratos**, no de firmas. Las reglas de firma (parámetros contravariantes, retornos covariantes) son necesarias pero no suficientes, y el compilador no verifica las de comportamiento.
  - (complemento) "Compila pero falla" también ocurre en el propio lenguaje: la covarianza de arrays en C# y Java permite `object[] a = new string[1]; a[0] = 1;`, que lanza `ArrayTypeMismatchException`/`ArrayStoreException` en ejecución.
  - (complemento) En TypeScript, `strictFunctionTypes` no se aplica a **métodos** (se comparan de forma bivariante): una clase puede implementar `alimentar(a: Animal)` como `alimentar(p: Perro)`, compila y falla al recibir un `Gato`. Declarar el miembro como propiedad función (`alimentar: (a: Animal) => void`) sí lo detecta.
  - (complemento) Cuadrado/Rectángulo solo viola LSP si el rectángulo es **mutable** con lados independientes; con tipos inmutables, un cuadrado es un rectángulo válido.
  - (complemento) LSP aplica a toda implementación de una interfaz, no solo a la herencia de clases; los dobles de test son el caso más olvidado.
  - (complemento) LSP no prohíbe sobrescribir ni especializar: prohíbe **sorprender** al cliente que programa contra el tipo base.
