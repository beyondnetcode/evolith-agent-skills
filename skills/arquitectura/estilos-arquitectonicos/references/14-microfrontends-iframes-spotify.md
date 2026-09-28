# [14] La polémica arquitectura de Spotify: Microfrontends con IFRAMES

> Fuente: TheDebugDuck — https://youtu.be/fQbzSQosVh8 · notas parafraseadas; «(complemento)» = conocimiento añadido o corrección.

- **Síntoma en producción:** la misma feature (p. ej., búsqueda) se implementa dos veces: web player (2 días) y desktop (~1,5 semanas, release en tiendas, adopción lenta). Cambiar entre vistas recarga JS/CSS; bugs entre iframes difíciles de rastrear; cambiar la tipografía global exige tocar ~15 lugares; stacks heterogéneos (React, librerías viejas, soluciones propias).
- **Causa raíz (mecanismo):** microfrontends por **iframe por vista** (search, player, home) en web y en desktop (app nativa con CEF, Chromium Embedded Framework). Aislamiento total da autonomía a muchos equipos, pero: cada iframe tiene su runtime (re-parseo/re-ejecución de bundles, frameworks duplicados, memoria), comunicación solo por `postMessage`, estado no compartido, y autonomía tecnológica sin gobierno → divergencia de stacks (Conway: muchos equipos autónomos = muchos stacks). Dos plataformas con velocidades de release distintas duplicando trabajo.
- **Metáfora visual del video:** sin analogía cotidiana explícita; la imagen es "dos mundos distintos bajo pantallas que se ven iguales", con Conway como espejo del organigrama.
- **Estrategias / solución:**
  - 2016: dos caminos en paralelo (mejorar iframes vista por vista vs prototipo de app única inspirado en la app de Spotify para TV); ganó el prototipo.
  - Reescritura del web player en **React + Redux**: un árbol de componentes, estado compartido, sin iframes. De >40 (equipos/vistas aisladas; ASR ambiguo) a un equipo dedicado de 5; MVP en semanas; ganó en A/B testing; un commit llega a usuarios en horas.
  - **Platform APIs**: capa TypeScript que abstrae el origen de datos (desktop: motor de playback nativo en C++; web: servicios web), consumida por React hooks → la misma capa React corre en ambos contenedores (puertos y adaptadores en frontend).
    ```
    [UI React única] → hooks → [Platform APIs (TS)] → { Desktop: C++ nativo vía CEF | Web: servicios HTTP }
    ```
  - **Des-riesgo antes del rewrite**: spike de 3 meses con ingenieros de varios equipos (¿cabe el web player en el contenedor desktop? playback, autenticación, empaquetado); ayudó tener ambos en el mismo monorepo. El video lo llama "risk delivery" (probablemente ASR de *de-risking*).
  - Si se mantienen fronteras de deploy por equipo: **Shadow DOM** (encapsulación CSS) y **Module Federation** (Webpack 5) con shell que carga remotos en runtime; marcar librerías core como `shared` + `singleton` para no descargar React varias veces; contratos de CSS e **integration tests con todos los módulos juntos** antes de producción.
- **Trade-offs y cuándo NO aplicar:** microfrontends no son mala idea: sirven cuando muchos equipos deben desplegar sin pisarse. Cuando el coste de carga, mantenimiento y velocidad supera el beneficio, unificar. Unificar concentra propiedad (riesgo de cuello de botella) y exige disciplina de modularización interna. Module Federation añade complejidad de versionado en runtime y fallos que no aparecen en local.
- **Heurísticas y umbrales:** 2 días (web) vs 1,5 semanas (desktop) por feature; ~15 puntos para un cambio de tipografía; >40 → 5 personas; spike de 3 meses; commit → producción en horas; riesgo de React ×3 sin `shared singleton`. Pregunta rectora: ¿necesitas **separar el deploy o separar el código**? Son cosas distintas.
- **Anti-patrones / señales de alerta:**
  - Un iframe por vista en la misma app con estado que debe sincronizarse vía `postMessage`.
  - Cada microfrontend eligiendo framework sin gobierno de plataforma.
  - Module Federation sin `shared`/`singleton` para React/design system (bundle con framework duplicado).
  - Clases CSS globales genéricas (`.highlight`) sin encapsulación ni prefijos.
  - Tests solo por módulo; ninguna prueba de composición completa.
  - Copiar el diagrama de otra empresa sin leer lo que realmente publicó.
- **Preguntas de revisión arquitectónica:**
  1. ¿Qué necesitamos independizar: el despliegue, el código, la propiedad o el runtime?
  2. ¿Cuántos equipos modifican la misma UI y con qué frecuencia chocan?
  3. ¿Qué dependencias se comparten como singleton y quién gobierna sus versiones?
  4. ¿Cómo se aísla el CSS y quién es dueño del design system?
  5. ¿Existe una capa de plataforma que abstraiga diferencias de entorno (web/desktop/móvil)?
  6. ¿Qué spike o prototipo valida el rewrite antes de comprometerse?
- **Caso real / empresa citada:** Spotify (web player y desktop con CEF, 2016–2018; unificación en un codebase React); Telia (Module Federation en producción, según el video; no verificado).
- **Precisión técnica:**
  - "No hay caché compartida entre vistas" es impreciso: la caché HTTP del navegador sí se reutiliza para la misma URL cacheable; lo que no se comparte es el runtime JS (parseo, ejecución, instancias de framework, memoria) (complemento).
  - Shadow DOM: "lo de afuera no entra" no es absoluto: propiedades heredadas (font, color) y custom properties CSS atraviesan el shadow boundary; tampoco aísla JS global (complemento).
  - Spotify no adoptó Module Federation; convergió a un único codebase React. Microfrontends como patrón ≠ la decisión final de Spotify (el video lo aclara correctamente).
  - (complemento) Alternativas actuales: Module Federation 2.0 (Rspack/Vite), single-spa, import maps.
  - ASR: "Macaba CF" = "que usaba CEF"; "Redox" = Redux; "domal" = DOM global.
