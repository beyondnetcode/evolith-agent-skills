# [42] SOLID: Interface Segregation Principle (ISP)

> Fuente: TheDebugDuck — https://youtu.be/NhivsfJ2GkE · notas parafraseadas; «(complemento)» = conocimiento añadido o corrección.
> Estado: elaborado a partir del título y el temario público del video; la transcripción no estuvo disponible (bloqueo de YouTube, 2026-09-28). Lo que no figura en el temario es «(complemento)». Pendiente de contrastar con la transcripción.

- **Síntoma en el código/equipo:** clases obligadas a implementar métodos que no necesitan; interfaces grandes. (complemento) Implementaciones con `throw new NotImplementedException()` o `throw new Error("no soportado")`; mocks que configuran 15 métodos para probar uno; un cambio en `IUsuarioService.ExportarCsv` obliga a recompilar y redesplegar el adaptador móvil que nunca exporta nada; `IRepository<T>` con 20 métodos cuando el lector solo usa `ObtenerPorId`.
- **Causa raíz (mecanismo):** una interfaz grande mezcla necesidades de clientes distintos. (complemento) Formulación de Martin: los clientes no deben verse obligados a depender de interfaces que no usan. El daño recae en el **cliente**, no solo en el implementador: cada método ajeno es una razón más para recompilar, redesplegar, reconfigurar mocks o romperse cuando cambia algo que no le importa. El implementador que no puede cumplir un método lanza una excepción y así viola además el contrato (LSP, ver [43]).
- **Metáfora visual propia (complemento):** el control remoto universal con 60 botones para alguien que solo quiere subir el volumen: cada botón extra es algo que puede apretarse por error, algo que el fabricante del televisor barato debe "simular" y algo que cambia en cada modelo nuevo. Un control por uso (volumen, canales) es más simple de fabricar y de usar. **Dónde se rompe:** en software dividir cuesta poco pero **buscar** cuesta mucho: 30 interfaces de un método dispersan el concepto, y el que sí necesita todo termina recibiendo 6 parámetros en lugar de uno.
- **Estrategias / solución:**
  1. Dividir la interfaz en otras más pequeñas y específicas. (complemento) Divide **por rol de cliente** (*role interfaces*, Fowler), no por método ni por capricho; una misma clase puede implementar varias:
     ```ts
     // Antes: la caché local "implementa" versionado y ACL que no tiene
     interface Almacenamiento {
       subir(k: string, b: Buffer): Promise<void>;
       descargar(k: string): Promise<Buffer>;
       borrar(k: string): Promise<void>;
       listarVersiones(k: string): Promise<string[]>;
       cambiarAcl(k: string, acl: Acl): Promise<void>;
     }
     class CacheLocal implements Almacenamiento {
       /* ... */
       listarVersiones(): Promise<string[]> { throw new Error("no soportado"); }
       cambiarAcl(): Promise<void> { throw new Error("no soportado"); }
     }
     // Después: interfaces por rol; cada cliente pide solo lo que usa
     interface Lector { descargar(k: string): Promise<Buffer>; }
     interface Escritor { subir(k: string, b: Buffer): Promise<void>; borrar(k: string): Promise<void>; }
     interface Versionado { listarVersiones(k: string): Promise<string[]>; }
     class S3Almacen implements Lector, Escritor, Versionado { /* ... */ }
     class CacheLocal implements Lector, Escritor { /* ... */ }
     async function generarMiniatura(origen: Lector, clave: string) { /* ... */ }
     ```
  2. (complemento) **Declara la interfaz donde se consume:** con tipado estructural (TypeScript, Go) el cliente puede definir o derivar su tipo estrecho (`Pick<Almacenamiento, "descargar">`) sin tocar al proveedor.
  3. (complemento) **Interfaz de un método ⇒ considera un tipo función** (`(k: string) => Promise<Buffer>`, `Func<string, Task<byte[]>>`).
  4. (complemento) **Lectura y escritura separadas** en repositorios (`ILeerPedidos`, `IGuardarPedidos`): el reporte no depende de métodos que mutan y su mock es trivial.
  5. (complemento) Para interfaces publicadas que no se pueden romper: añade las interfaces de rol nuevas, haz que la grande las extienda, migra clientes y depreca la grande.
- **Trade-offs y cuándo NO aplicar:** (complemento) demasiadas interfaces pequeñas fragmentan el concepto y empeoran el descubrimiento (Ousterhout: interfaces superficiales que no esconden nada). No dividas si un único cliente usa todos los métodos, ni si la interfaz es un **protocolo cohesivo** publicado: .NET `Stream` mantiene un contrato amplio y expone `CanRead`/`CanWrite`/`CanSeek` más `NotSupportedException` como decisión consciente; las "operaciones opcionales" de las colecciones de Java son el mismo compromiso. Es aceptable si el contrato **declara** la capacidad y los clientes la consultan; es un defecto si la excepción sorprende.
- **Heurísticas y umbrales:** (complemento)
  - Mapa cliente × método: si los clientes usan subconjuntos disjuntos o casi disjuntos, esos subconjuntos son las interfaces.
  - Cualquier `NotImplementedException`/`NotSupportedException` en una implementación es una señal que exige explicación.
  - Un mock que configura métodos que el test no ejercita indica que el cliente depende de demasiado.
  - Proverbio de Go (Rob Pike, 2015): «The bigger the interface, the weaker the abstraction».
- **Anti-patrones / señales en code review:** (complemento)
  - Interfaz "dios" que refleja todos los métodos públicos de una clase (*header interface*).
  - Implementaciones vacías o que devuelven `null`/`default` para cumplir la firma (*refused bequest*).
  - Flags booleanos en la interfaz para "activar" partes (`soportaVersiones: boolean`) sin que el cliente los consulte.
  - Dividir por número de métodos (una interfaz por método en todo el código) en lugar de por cliente.
  - DTO o endpoint único que sirve a web, móvil y batch con campos que cada uno ignora (ISP a nivel de API: BFF o campos seleccionables).
- **Preguntas de revisión:** (complemento)
  1. ¿Qué clientes consumen esta interfaz y qué métodos usa cada uno?
  2. ¿Alguna implementación lanza, ignora o devuelve un valor vacío en algún método?
  3. ¿Un cambio en un método obliga a recompilar o redesplegar clientes que no lo usan?
  4. ¿La división sigue roles de cliente o es arbitraria?
  5. Si la interfaz declara capacidades opcionales, ¿todos los clientes las consultan antes de llamar?
- **Referencias (complemento):** Martin, *The Interface Segregation Principle* (C++ Report, 1996) y *Agile Software Development: Principles, Patterns, and Practices* (2002); Fowler, *RoleInterface* y *HeaderInterface* (bliki, 2006) y *Refactoring* 2.ª ed. (*Refused Bequest*, *Extract Superclass*); Ousterhout, *A Philosophy of Software Design* (profundidad de módulos); Rob Pike, *Go Proverbs* (2015); Liskov y Wing (1994) para el vínculo con LSP.
- **Precisión técnica:**
  - (complemento) ISP trata de las **dependencias del cliente**, no de "interfaces pequeñas" como fin. Una interfaz grande usada completa por su único cliente no viola ISP.
  - (complemento) Martin lo formuló a partir de un caso en Xerox: una clase `Job` compartida por impresión, grapado y fax hacía que cualquier cambio recompilara todo; hoy el coste equivalente es redesplegar, reconfigurar mocks y leer ruido.
  - (complemento) `NotImplementedException` en .NET significa "pendiente de implementar"; `NotSupportedException`, "no soportado por diseño". Ambas rompen la sustitución (LSP) salvo que el contrato declare la capacidad.
  - (complemento) ISP aplica más allá de las interfaces del lenguaje: paquetes (depender de una biblioteca entera para usar una función), APIs HTTP (BFF, GraphQL) y eventos (consumidores que deserializan un payload enorme para leer un campo).
