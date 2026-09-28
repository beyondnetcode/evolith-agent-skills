# [07] Por qué tu código "Limpio" está ARRUINANDO el proyecto

> Fuente: TheDebugDuck — https://youtu.be/NTA6Nt2TSNw · notas parafraseadas; «(complemento)» = conocimiento añadido o corrección.

- **Síntoma en producción:** un requisito de 10 líneas (costo de envío premium vs estándar) llega como 12 archivos (interface Strategy, 2 implementaciones, Context, Factory, Singleton registry, 3 interfaces extra). En un incidente de madrugada, llegar al `if` que devuelve 9.99/14.99 exige 5 archivos y 4 saltos de navegación (~10 min + 5 min entendiendo qué estrategia inyectó la factory). Integrar un endpoint nuevo de Stripe obliga a tocar interfaz, abstracta, impl y factory. Tests que pasan o fallan según el orden (singleton con estado).
- **Causa raíz (mecanismo):** abstracción especulativa: se aplican patrones GoF sin que exista el problema que resuelven (variabilidad real, acoplamiento presente). Cada capa de indirección añade **complejidad cognitiva** = número de saltos mentales para seguir el flujo, no número de `if`. Los asistentes de IA amplifican esto porque se entrenaron con código "enterprise" y asocian "extensible y bien estructurado" con árboles de clases. Casos específicos:
  - **Singleton con estado mutable global:** un batch que cambia el IVA a medianoche altera una transacción de checkout en curso; los tests comparten estado y dependen del orden.
  - **Singleton en Android que guarda una Activity:** al rotar el teléfono la Activity se destruye, pero el singleton (vida = proceso) mantiene la referencia → el GC no la libera → OOM en gama baja.
  - **Interfaz + Impl con una única implementación** ("por si mañana cambiamos"): duplica archivos (500 clases de dominio → 1000 archivos) y añade un clic en cada navegación.
  - **Abstracción prematura por similitud superficial** (email builder con flags para casos que no son el mismo problema).
- **Metáfora visual del video:** el "tour guiado": si un compañero necesita que le hagan un tour para seguir el flujo en una guardia, hay demasiada indirección (también "el pasillo de adaptadores" de healthcare.gov).
- **Estrategias / solución:**
  - Empezar con la versión directa: `calculateShipping(customerType)` en el propio servicio, con tests.
    ```
    function calculateShipping(type):
      return type == PREMIUM ? EXPRESS_WITH_DISCOUNT : STANDARD
    # Extraer Strategy solo cuando: N transportistas reales, switch creciendo (~40 líneas),
    # cambios en una rama que arriesgan las otras.
    ```
  - Singleton → delegar el ciclo de vida al contenedor DI (Spring, NestJS, .NET) con scope singleton e inyectar por constructor; en tests pasar instancias limpias.
  - Android: los objetos de vida larga no referencian objetos de vida corta; usar `applicationContext`.
  - Pagos: una clase `StripeClient` que envuelve el SDK; extraer la interfaz cuando PayPal sea necesidad real con fecha.
  - **Regla de tres:** 1.ª vez directo, 2.ª tolerar duplicación, 3.ª abstraer con información suficiente. "Duplicar es más barato que la abstracción equivocada" (Sandi Metz).
  - YAGNI: pensar a futuro sí, escribir hoy el código del futuro no.
  - Casos donde el patrón sí paga: **Strategy** con 6 transportistas (FedEx, UPS, DHL, courier nacional, 2 regionales); **Observer/eventos** cuando `OrderConfirmed` debe disparar email, inventario, depósito y registro contable sin que checkout conozca a los cuatro.
- **Trade-offs y cuándo NO aplicar:** no es anti-patrones; es exigir que el costo resuelva algo concreto hoy. (complemento) Contrapesos legítimos a la "interfaz de una sola impl": puertos en arquitectura hexagonal en fronteras de módulo/infraestructura, fronteras de un monolito modular (ver [08]), lenguajes donde no es posible hacer doble de prueba de clases concretas, y contratos publicados entre equipos. La duplicación tolerada debe ser local; duplicar reglas de negocio críticas (p. ej., cálculo fiscal) en N lugares es otro riesgo.
- **Heurísticas y umbrales:**
  - Tres preguntas antes de abstraer: (1) ¿resuelve un acoplamiento **de hoy**? (2) ¿hay **más de una variante real ahora**? 0–1 → no hay patrón; (3) ¿un compañero sigue el flujo solo durante una guardia? Si necesita tour → exceso de indirección.
  - Interfaz justificada cuando hay ≥2 implementaciones en producción.
  - Regla de tres para duplicación.
  - Señal de Strategy: switch de ~40 líneas con 6 variantes.
- **Anti-patrones / señales de alerta:**
  - Factory "fantasma" cuya variable de entorno siempre vale lo mismo.
  - Implementaciones que lanzan `NotImplementedException` (exportadores Excel/PDF "para el futuro").
  - Pares `UserService`/`UserServiceImpl` sin lógica en la interfaz.
  - `getInstance()` con estado mutable leído en transacciones; singletons que retienen objetos con ciclo de vida corto.
  - Helpers con flags booleanos para "apagar" partes (abstracción equivocada).
  - PR generado por IA con "hazlo extensible" que multiplica archivos sin variantes reales.
  - Recorrido de depuración > 3 saltos para llegar a una regla trivial.
- **Preguntas de revisión arquitectónica:**
  1. ¿Qué variante real, existente hoy, justifica esta interfaz/patrón?
  2. ¿Cuántos saltos hay desde el punto de entrada hasta la regla de negocio?
  3. ¿Qué estado comparte este singleton y quién lo muta en tiempo de ejecución?
  4. ¿Qué referencia retiene este objeto de vida larga y cuál es el ciclo de vida del referenciado?
  5. Si el requisito futuro llega, ¿esta abstracción encaja o habrá que romper el contrato igual?
  6. ¿Qué borraríamos sin perder funcionalidad?
- **Caso real / empresa citada:** GoF *Design Patterns* (1994); guía oficial de Android (fugas por Context); EJB 2.x (Home + Remote interface + bean + XML por entidad) y la respuesta de Rod Johnson (*Expert One-on-One J2EE Design and Development*, 2002 → Spring); Knight Capital (2012, ~45 min, ~US$440 M); healthcare.gov (2013, 6 inscripciones el primer día, >50 contratistas, >US$2.000 M); Sandi Metz (*The Wrong Abstraction*, 2016; autora de POODR).
- **Precisión técnica:**
  - Singleton gestionado por DI resuelve **testabilidad y construcción**, no la carrera del IVA: si el objeto sigue siendo mutable y compartido, el problema persiste. La corrección es configuración **inmutable/versionada** o una instantánea por transacción (complemento).
  - GoF: la advertencia sobre no aplicar patrones indiscriminadamente está en el capítulo 1 ("How to Use a Design Pattern"), no exactamente en el prefacio; los ejemplos eran C++/Smalltalk (el caso de estudio es el editor Lexi), no solo compiladores.
  - Knight Capital: la causa documentada por la SEC fue **código muerto (Power Peg) reactivado por reutilizar un flag** + despliegue manual que omitió 1 de 8 servidores + falta de controles de riesgo; es más un fallo de despliegue/configuración y deuda que de "patrones". Pérdida: ~US$440 M anunciados por Knight; la SEC habla de >US$460 M. Fue rescatada y luego fusionada con Getco (KCG).
  - healthcare.gov: el equipo de rescate (origen de USDS) atacó sobre todo monitoreo, capacidad, base de datos y coordinación; "eliminar capas" es una simplificación. Costes reportados varían (US$1.700–2.100 M).
  - (complemento) La regla de tres se atribuye a Don Roberts, popularizada en *Refactoring* (Fowler).
  - ASR: "Gang of War" = Gang of Four; "Eric Gama" = Erich Gamma; "Night Capital/Smarts" = Knight Capital/SMARS; "KISA" = "quizá"; "CSB" = CSV.
