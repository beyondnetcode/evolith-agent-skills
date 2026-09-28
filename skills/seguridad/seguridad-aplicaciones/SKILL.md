---
name: seguridad-aplicaciones
description: Criterio de diseño seguro para aplicaciones — validación de archivos subidos (magic bytes, Content-Type decidido por el servidor, nosniff, attachment, dominio sandbox, cuarentena, políglotas, SVG/HTML/Office/PDF) y autenticación con tokens (JWT de vida corta, refresh revocable y rotado, cookies HttpOnly/Secure/SameSite, BFF, sesiones de servidor, revocación al cambiar contraseña o cerrar sesión en todos los dispositivos). Úsala siempre que un diseño, PR o incidente toque carga o descarga de archivos, previsualización de adjuntos, login, logout, JWT, OAuth, almacenamiento de tokens en el navegador, "el usuario cambió la contraseña y el atacante sigue dentro", o código de autenticación o subida generado por IA, aunque el usuario no hable de seguridad.
license: MIT
metadata:
  categoria: seguridad
  version: "1.0.0"
  idioma: es
  fuentes: "TheDebugDuck: 02, 12"
  relacionadas: "contratos-api, resiliencia-operacion, consistencia-distribuida"
---

# Seguridad de aplicaciones

Conocimiento destilado de TheDebugDuck (videos 02 y 12) con correcciones. Tesis común: **la forma válida no garantiza un contenido ni un estado válidos**. Una extensión correcta no hace segura una "imagen"; una firma JWT correcta no hace legítimo a quien la presenta. El control se pone donde está la confianza (el servidor, el contenido real, un estado revocable), no donde lo declara el cliente.

## Cómo usar esta skill

1. Identifica el activo y quién lo consume después: ¿quién abre el archivo y con qué sesión? ¿qué puede hacer un token robado y durante cuánto tiempo?
2. Recorre la matriz y lee la referencia del caso.
3. Entrega con el formato de salida, incluyendo **la ventana de exposición residual** y **la prueba que lo demuestra** (curl con MIME falsificado, token robado tras logout).

## Índice de referencias

| Tema | Archivo | Léelo cuando… |
|---|---|---|
| Validación y servicio de archivos subidos | `references/02-validacion-de-archivos.md` | uploads, adjuntos, previsualizaciones, buckets, URLs prefirmadas |
| JWT, refresh tokens, revocación, almacenamiento en el cliente | `references/12-jwt-diseno-seguro.md` | login/logout, "cerrar sesión en todos", cambio de contraseña, SPA con tokens |

Temas de seguridad cubiertos en otras skills: ReDoS y reglas WAF → `resiliencia-operacion`; firma HMAC de webhooks → `consistencia-distribuida`; IDs expuestos y autorización por objeto (BOLA/IDOR) → `datos-persistencia`; códigos 401/403 y errores → `contratos-api`.

## Principios (y por qué)

1. **Todo lo que viaja en la petición lo decide quien la envía**: nombre, extensión, MIME, `accept`, claims no verificados. Trátalo como no confiable; el atacante no usa tu formulario, usa curl.
2. **Inspecciona el contenido, no la etiqueta**: magic bytes con una librería de firmas, y decodificar/re-codificar si vas a procesarlo. Aun así, estructura válida ≠ contenido seguro (políglotas, PDF con acciones, XLSX con fórmulas).
3. **El servidor decide cómo se sirve**: `Content-Type` del tipo detectado, `X-Content-Type-Options: nosniff`, `Content-Disposition: attachment` para formatos complejos y, idealmente, un dominio separado sin cookies de sesión. La mayoría del daño ocurre al **servir**, no al subir.
4. **Diseña la revocación antes que el login.** Un token stateless no se puede invalidar: la ventana de exposición es su TTL. Access en minutos + refresh revocable en servidor + evento de seguridad que revoca.
5. **Tokens fuera del alcance de JavaScript**: cookie `HttpOnly` + `Secure` + `SameSite` (con defensa CSRF) o patrón BFF. `localStorage` es legible por cualquier script inyectado.
6. **Elige el modelo por la arquitectura, no por la moda**: sesiones de servidor en un store en memoria son más simples y revocables al instante para un solo backend; JWT paga en entornos multi-servicio o federados.
7. **El código generado por IA reproduce el tutorial promedio** (check de extensión + MIME; JWT largo en `localStorage`): revísalo con estos criterios, no porque "pasa los tests con el navegador".

## Matriz "si ves X → considera Y"

| Si ves… | Riesgo | Considera… |
|---|---|---|
| `originalname.endsWith('.jpg')`, `file.mimetype ===` como validación | archivo activo (HTML/SVG) almacenado | magic bytes + allowlist + re-codificar imágenes + nombre generado por el servidor |
| Servir el archivo con el `Content-Type` recibido o previsualizarlo en `<iframe>` | XSS almacenado con la sesión interna | tipo detectado + `nosniff` + `attachment` + dominio sandbox / `CSP: sandbox` |
| Subida directa a bucket con URL prefirmada | el backend nunca ve el archivo | bucket de cuarentena + escaneo asíncrono por evento antes de publicar |
| Office/PDF que deben abrirse internamente | macros, fórmulas, enlaces de phishing, XXE, zip bombs | CDR, extracción de datos estructurados, límites de descompresión |
| JWT de horas usado para todo, sin refresh | token robado válido hasta que expira | access 5–15 min + refresh revocable y rotado con detección de reuso |
| Logout o cambio de contraseña que solo borra el token local | el atacante sigue dentro | revocar refresh del usuario; `token_version`/`password_changed_at` comparado con `iat` |
| `localStorage.setItem('token', …)` | exfiltración por XSS | cookie HttpOnly/Secure/SameSite + anti-CSRF, o BFF |
| Tabla SQL de tokens revocados consultada en cada request | coste de estado central sin sus ventajas | denylist de `jti` en Redis con TTL = vida restante, o introspección de tokens opacos en el gateway |
| Datos sensibles en el payload del JWT | payload legible (base64url) | solo identificadores y claims mínimos |
| Monolito web con un backend y necesidad de expulsar usuarios al instante | complejidad innecesaria de JWT | sesiones de servidor en Redis |

## Preguntas de revisión

1. ¿Dónde se inspecciona el contenido real del archivo y quién decide el `Content-Type` al servirlo?
2. ¿Quién abre los archivos después, con qué privilegios de sesión y desde qué dominio?
3. ¿Hay pruebas que atacan la API directamente con MIME/extensión falsificados y archivos políglotas?
4. ¿Cuál es el TTL del access token y la ventana máxima aceptable tras un robo?
5. ¿Qué eventos (cambio de contraseña, logout global, alerta de fraude) revocan qué tokens y dónde?
6. ¿Dónde se guardan los tokens en el cliente y cuál es la defensa contra XSS y CSRF?
7. ¿Se rotan los refresh tokens y se detecta su reutilización?

## Precisiones que los videos simplifican (no las repitas)

- Un SVG en `<img>` **no** ejecuta scripts; el riesgo es abrirlo directamente o embeberlo en `<iframe>`, `<object>` o `<embed>`.
- Vía HTTP el navegador decide por `Content-Type` (y sniffing), no por la extensión. `archivo.jpg.html` no pasa un `endsWith('.jpg')` bien anclado; el problema son validaciones débiles o almacenes que infieren el tipo por la última extensión.
- `.xlsx` no contiene macros (eso es `.xlsm`); su firma ZIP la comparten DOCX, JAR y APK.
- El problema del JWT es la **revocación**, no que "exponga contraseñas"; lo que se expone es el payload.
- `HttpOnly` impide leer el token, no que un XSS haga peticiones autenticadas desde la página; las cookies traen CSRF, que se mitiga con `SameSite` y token anti-CSRF.
- Las sesiones de servidor escalan con un store en memoria; el anti-patrón es la tabla SQL consultada en cada clic. Referencias: RFC 7009 (revocación), RFC 7662 (introspección), RFC 9700 (OAuth 2.0 Security BCP), RFC 9449 (DPoP).

## Formato de salida

```
Riesgo: <qué puede hacer un atacante y a quién afecta>, en una línea.
Control: <dónde se pone la confianza y el mecanismo concreto>.
Ventana residual: <qué sigue expuesto y cuánto tiempo>.
Prueba: <petición o test que demuestra que el control funciona>.
Trade-offs: <UX, latencia, complejidad, CSRF>.
Fuente: <referencia(s) y video(s)>.
```
