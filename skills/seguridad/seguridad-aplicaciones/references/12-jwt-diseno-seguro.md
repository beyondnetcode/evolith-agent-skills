# [12] El grave error de diseño con JWT que expone tus contraseñas

> Fuente: TheDebugDuck — https://youtu.be/DjwejUgsu5I · notas parafraseadas; «(complemento)» = conocimiento añadido o corrección.

- **Síntoma en producción:** tras detectar uso ajeno de la cuenta, el usuario cambia la contraseña (200 OK) y pulsa "cerrar sesión en todos los dispositivos" (200 OK), pero los logs muestran al atacante haciendo GET/POST/DELETE exitosos con el token robado hasta que expire.
- **Causa raíz (mecanismo):** el JWT (header + payload con claims + firma) se verifica **localmente** (stateless): no se consulta un registro central, por eso escala, pero tampoco hay dónde invalidarlo. Cambiar la contraseña solo afecta a futuros logins; el logout de una SPA solo borra el token de ese navegador. Agravantes: un único JWT de larga vida (2 h) usado para todo (mezcla de access y refresh), almacenado en `localStorage` y exfiltrable por cualquier script inyectado (`getItem`); el backend no distingue al dueño del ladrón.
- **Metáfora visual del video:** hotel: el guardia que consulta el libro de recepción en cada pasillo (sesiones, seguro pero no escala) vs la tarjeta programada con firma (JWT, sin consultas). Un token robado es un pasaporte robado con sello auténtico.
- **Estrategias / solución:** los tres movimientos:
  1. **Access token corto** (minutos; ejemplo de 15 min), verificado localmente en cada request.
  2. **Refresh token revocable en servidor**, usado solo contra el servidor de autorización (`POST /oauth/token`), guardado en un store rápido (Redis). "Cerrar sesión en todos" = revocar los refresh del usuario; revocarlos también al cambiar contraseña (no es automático, hay que configurarlo).
  3. **Cookie `HttpOnly` + `Secure`** en lugar de `localStorage` (recomendación OWASP).
  ```
  Cliente ─(access JWT 5–15 min, cookie HttpOnly/Secure)→ API: verify(firma) local, sin BD
  Cliente ─(refresh)→ Auth Server /oauth/token ─lookup→ Redis (revocable, rotación)
  Evento seguridad (cambio pwd / "salir de todo") → revocar todos los refresh del usuario
  Ventana residual de exposición = TTL del access token
  ```
  - Se descarta la tabla `revoked_tokens` consultada en cada request (select por `jti`): reintroduce el coste de estado central + crecimiento de la lista.
  - (complemento) Alternativas más finas: denylist de `jti` en Redis con TTL = vida restante del token (acotada y barata); `token_version`/`password_changed_at` por usuario cacheado y comparado con `iat`; tokens opacos + introspección (RFC 7662) en el gateway; **rotación de refresh con detección de reuso** (RFC 9700, OAuth 2.0 Security BCP); DPoP (RFC 9449) para atar el token al cliente; patrón BFF para SPAs (el navegador nunca ve tokens).
- **Trade-offs y cuándo NO aplicar:** access corto implica más tráfico de refresh y manejo de expiración en el cliente; la revocación nunca es instantánea (queda la ventana del TTL). Cookies introducen **CSRF** → `SameSite` + token anti-CSRF (complemento). `HttpOnly` evita la exfiltración pero no que un XSS haga peticiones autenticadas desde la página (complemento). Para un monolito web con un solo backend, sesiones de servidor en Redis suelen ser más simples y revocables al instante; JWT paga más en arquitecturas multi-servicio o federadas (complemento).
- **Heurísticas y umbrales:** access en minutos, no 2 horas ni un día; refresh revocable en store en memoria; "stateless donde hay volumen, stateful donde necesitas sacar a alguien de verdad". Latencias ilustrativas del video: 3–4 ms por request sin consulta central.
- **Anti-patrones / señales de alerta:**
  - Un solo JWT de larga vida para todo, sin refresh.
  - `localStorage.setItem('token', ...)`.
  - Logout que solo borra el token del cliente; cambio de contraseña sin revocar refresh.
  - Tabla de blacklist en BD relacional consultada en cada request.
  - Refresh token enviado a APIs de negocio (debería ir solo al servidor de autorización).
  - (complemento) Datos sensibles en el payload: está en base64url, no cifrado.
- **Preguntas de revisión arquitectónica:**
  1. ¿Cuál es el TTL del access token y cuál es la ventana máxima aceptable de exposición tras un robo?
  2. ¿Qué eventos (cambio de contraseña, logout global, alerta de fraude) revocan qué tokens y dónde?
  3. ¿Dónde se almacenan los tokens en el cliente y qué protección hay contra XSS y CSRF?
  4. ¿Se rotan los refresh tokens y se detecta su reutilización?
  5. ¿Realmente necesitamos JWT o bastan sesiones de servidor?
  6. ¿Qué contiene el payload y es aceptable que sea legible?
- **Caso real / empresa citada:** no hay empresa concreta; referencias normativas: OAuth 2.0 (access vs refresh, revocación de refresh) y OWASP (no usar `localStorage` para tokens).
- **Precisión técnica:**
  - El título ("expone tus contraseñas") es engañoso: el problema tratado es la **revocación**, no la exposición de contraseñas. Lo que sí se expone es el payload (codificado, no cifrado).
  - "Redis cerca del borde" es impreciso: el refresh se valida en el servidor de autorización; lo relevante es un store rápido y revocable, no la ubicación en el edge.
  - Las sesiones de servidor no son inherentemente inescalables: un store en memoria (Redis) sostiene alto tráfico; la tabla SQL por clic es el anti-patrón, no el modelo stateful en sí (complemento).
  - Revocación de tokens: RFC 7009 (complemento).
  - ASR: "stakeless" = stateless; "Oout" = OAuth; "JWP" = JWT; "Reis" = Redis; "Oasp" = OWASP; "cookiet only" = cookie HttpOnly.
