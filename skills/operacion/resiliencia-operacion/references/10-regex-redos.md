# [10] Esta Regex de 11 caracteres tumbó medio Internet

> Fuente: TheDebugDuck — https://youtu.be/G_nth-0hbLA · notas parafraseadas; «(complemento)» = conocimiento añadido o corrección.

- **Síntoma en producción:**
  - 502 masivos en sitios detrás de Cloudflare (Discord, Shopify, etc.) y CPU al 100 % en los servidores del edge en todo el mundo, con orígenes sanos. Se sospecha de un DDoS o del DNS.
  - Stack Overflow (2016): el sitio no responde durante 34 min; un hilo calcula sin lanzar excepción.
  - No hay error ni excepción: solo CPU saturada hasta que algo externo corta.
- **Causa raíz (mecanismo):**
  - Los motores con *backtracking* (PCRE, Irregexp de V8, `re` de Python, Java, .NET) guardan un punto de control en cada cuantificador y retroceden al fallar.
  - Con cuantificadores ambiguos o anidados (varios `.*` que compiten por los mismos caracteres, `(a+)+`) y entradas largas que *casi* coinciden, el número de caminos crece de forma superlineal (polinómica o exponencial).
  - Cloudflare desplegó una regla WAF anti-XSS cuyo núcleo era equivalente a `.*(?:.*=.*)`. Con cookies o user-agents largos de tráfico normal, sin ningún ataque, el motor probaba todas las particiones posibles entre los comodines y agotó la CPU de toda la red. El WAF evalúa cada request, así que el fallo fue global e inmediato.
- **Metáfora visual del video:** estacionamiento subterráneo buscando la rampa de salida: entras por un pasillo, pared, reversa, pruebas el siguiente. Con pocos pasillos es trivial; con un laberinto enorme nunca sales. Una regex es una plantilla perforada; el motor juega al ajedrez guardando posiciones para deshacer.
- **Estrategias / solución:**
  1. **Timeout activo por evaluación** (10–15 ms en el video): abortar con una excepción controlada para que el hilo siga atendiendo.
  2. **Motor de tiempo lineal** (RE2, `regexp` de Go, `regex` de Rust, Hyperscan; autómatas sin backtracking): peor caso O(n) garantizado. Pierde backreferences y lookarounds, lo cual es aceptable para validar input o inspeccionar tráfico.
  3. **Pruebas adversariales:** strings largos (100+ caracteres) que casi coinciden y fallan al final, no solo casos felices.
  4. Checklist antes del commit: ¿comodines abiertos? ¿input no controlado (usuario, cabeceras, payloads de terceros)? ¿timeout? ¿probada con near-miss largos?
  ```text
  # .NET:   new Regex(p, RegexOptions.NonBacktracking)       // .NET 7+, lineal
  #         new Regex(p, opts, TimeSpan.FromMilliseconds(15)) // timeout
  # Node:   usar binding RE2 (paquete re2) o motor lineal experimental de V8 (flag /l)
  # Java:   RE2/J; Python: google-re2 o módulo `regex` con timeout
  # Diseño: anclar ^...$, clases negadas [^=]* en lugar de .*, cuantificadores acotados {1,64},
  #         limitar longitud del input ANTES de hacer el match
  ```
  5. (complemento, del postmortem de Cloudflare) Rollout escalonado también para reglas y configuración (no solo para binarios), protección de CPU por regla y un kill switch global probado.
  6. (complemento) Linters/CI con detección de ReDoS (safe-regex, recheck, consultas de CodeQL).
- **Trade-offs y cuándo NO aplicar:**
  - RE2 restringe la sintaxis y puede consumir más memoria (DFA) o ser algo más lento en patrones simples.
  - El timeout produce falsos negativos. (complemento) En un WAF obliga a decidir entre fail-open (seguridad) y fail-closed (disponibilidad), y solo funciona si el motor es interrumpible.
  - Backtracking sigue siendo válido sobre input confiable y acotado (herramientas internas, búsqueda en el IDE).
- **Heurísticas y umbrales:**
  - Timeout de regex de 10–15 ms en el camino caliente; Stack Overflow lo cita con 100 ms.
  - Con crecimiento exponencial, 30 caracteres superan 10⁹ caminos y 50 superan 10¹⁵.
  - Cloudflare: despliegue a las 13:42 UTC; WAF desactivado globalmente hacia las 14:07–14:09 (unos 27 min).
  - Stack Overflow: 20-jul-2016, 34 min.
  - Cita: "¿quién tiene el interruptor para cortarla en tu servicio?"
- **Anti-patrones / señales de alerta:**
  - Patrones con `.*` repetidos o anidados, `(x+)+`, `(.*=.*)*`, alternancias solapadas `(a|ab)*`; `\s+$` sobre texto largo.
  - Regex copiada de Stack Overflow o de un LLM directo a producción, sin tests adversariales.
  - Regex aplicada a input no confiable sin límite de longitud ni timeout (cabeceras, cookies, cuerpos, logs de terceros).
  - Configuración o reglas (WAF, feature rules) que se despliegan globalmente en segundos sin canary.
- **Preguntas de revisión arquitectónica:**
  1. ¿Qué motor de regex usa este componente y cuál es su peor caso?
  2. ¿El input es controlado por terceros? ¿Se limita su longitud antes del match?
  3. ¿Hay timeout o kill switch por evaluación, y qué hace el sistema al dispararse (fail-open o fail-closed)?
  4. ¿CI incluye casos near-miss largos o un analizador de ReDoS?
  5. ¿Las reglas y la configuración siguen el mismo rollout progresivo que el código?
- **Caso real / empresa citada:** Cloudflare (2-jul-2019, regla WAF anti-XSS, 502 globales); Stack Overflow (20-jul-2016, 34 min fuera de servicio).
- **Precisión técnica:**
  - Stack Overflow no fue exponencial ni se resolvió con un timeout. (complemento) Según su postmortem, la regex recortaba espacios en blanco (`^[\s‌]+|[\s‌]+$`) y un post con unos 20.000 espacios consecutivos provocó un coste cuadrático O(n²). Como la home renderizaba ese post y el health check del balanceador apuntaba a la home, el LB sacó todos los servidores de rotación; se resolvió reemplazando la regex por código de substring. Conecta con [19]: un health check acoplado a lógica pesada.
  - En Cloudflare el crecimiento fue superlineal (polinómico, por los comodines consecutivos), no el exponencial clásico de cuantificadores anidados. El efecto práctico fue el mismo. (complemento) El postmortem también reconoce que una protección de CPU del WAF se había eliminado semanas antes en un refactor, y que las reglas se propagaban globalmente sin despliegue escalonado.
  - "Cloudflare migró a RE2" está simplificado. (complemento) Anunció pasar a un motor con garantías de tiempo de ejecución (RE2 o el de Rust) y reintrodujo límites de CPU y rollout escalonado de reglas.
  - "NFA = motor con backtracking" es impreciso. El NFA es el autómata; lo peligroso es simularlo con backtracking. RE2 simula NFA/DFA sin backtracking (Thompson/Pike VM).
  - PCRE no es el motor de Node (V8 Irregexp) ni de Python (`re` propio): todos hacen backtracking, pero son motores distintos.
  - La regex de email del video limita el TLD a 2–6 letras. (complemento) Hoy existen TLD más largos, así que produce falsos rechazos.
