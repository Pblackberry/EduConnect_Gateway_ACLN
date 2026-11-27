# EduConnect: PoC de API Gateway con Kong

Prueba de concepto reproducible en contenedores que expone cuatro servicios REST simulados (Estudiantes, Matrículas, Pagos y Certificados) a través de **un único punto de entrada**: Kong Gateway. El gateway valida credenciales de los consumidores (API Key), limita el tráfico y enruta las solicitudes sin modificar los backends.

> Laboratorio de Arquitectura Aplicada, Integración de Sistemas (ISWZ3104).
> Todas las credenciales de este repositorio son **ficticias** y solo sirven para la PoC.

---

## 1. Arquitectura

```
                       ┌──────────────────── red Docker "educonnect" ─────────────────────┐
 Cliente / Postman     │                                                                  │
 (X-API-Key)  ───────► │  Kong Gateway 3.9.5 (DB-less)          ┌─► estudiantes:8000      │
   :8000               │   ├─ key-auth (X-API-Key)              ├─► matriculas:8000       │
                       │   ├─ rate-limiting 5/min por consumer  ├─► pagos:8000            │
                       │   └─ rate-limiting 2/min (certificados)└─► certificados:8000     │
                       └──────────────────────────────────────────────────────────────────┘
 Admin API: 127.0.0.1:8001 (solo local)          Los backends NO publican puertos
```

| Ruta pública (gateway) | Backend interno | Política |
|---|---|---|
| `GET /api/estudiantes` | `http://estudiantes:8000/estudiantes` | API Key + 5 req/min por consumer |
| `GET /api/matriculas` | `http://matriculas:8000/matriculas` | API Key + 5 req/min por consumer |
| `GET /api/pagos` | `http://pagos:8000/pagos` | API Key + 5 req/min por consumer |
| `GET /api/certificados` | `http://certificados:8000/certificados` | API Key + **2 req/min** por consumer |

Kong localiza los backends por **nombre de servicio**: el DNS interno de Docker lo resuelve a la IP actual del contenedor, sin IPs fijas.

## 2. Requisitos

- Docker Engine o Docker Desktop, con Docker Compose v2 (`docker compose`).
- Postman (o cualquier cliente HTTP) y `curl`.
- Puertos libres en tu máquina: **8000** y **8001**.
- Acceso a internet la primera vez, para descargar las imágenes.

En Windows usa `curl.exe` (en PowerShell `curl` es un alias de otro comando).

## 3. Versión de Kong elegida

**`kong:3.9.5`**, fijada en `docker-compose.yml` (nunca `latest`).

- **Modo DB-less**: la configuración vive en un único archivo (`kong/kong.yml`), sin base de datos. Es versionable y reproducible. Costo: Kong lee el archivo solo al arrancar, así que cada cambio requiere `docker compose restart kong`.
- **Por qué 3.9 y no 3.10 LTS**: según la política oficial de soporte, 3.10 LTS corresponde a Kong Gateway Enterprise. Según fuentes de la comunidad, la imagen open source `kong:` termina en la serie 3.9, y el caso de estudio prefiere tecnologías de código abierto. La contrapartida es un núcleo más antiguo, sin parches futuros. Para producción se evaluaría una versión con soporte vigente o alternativas como Apache APISIX.
- `_format_version: "3.0"` en `kong.yml` es la versión del **esquema del archivo declarativo**, no la versión de Kong.

## 4. Estructura del repositorio

```
.
├── docker-compose.yml      # Kong + 4 mocks + red (punto único de arranque)
├── kong/
│   └── kong.yml            # Services, Routes, Consumer y plugins
├── estudiantes/            # Mock (FastAPI) + Dockerfile
├── matriculas/
├── pagos/
├── certificados/
└── tests/
    └── EduConnect.postman_collection.json   # colección de pruebas
```

Cada mock responde HTTP 200 con JSON, escucha en el puerto interno 8000 y agrega la cabecera `X-Servicio` para identificar qué servicio respondió. Registra en consola las solicitudes que recibe.

> Los `docker-compose.yml` que pudieran existir dentro de cada carpeta de mock son de uso individual y **no forman parte** de esta PoC. El arranque oficial es el de la raíz.

## 5. Arranque

```bash
docker compose up -d --build
docker compose ps
```

Resultado esperado: los cinco contenedores (`kong`, `estudiantes`, `matriculas`, `pagos`, `certificados`) en estado `Up`. Solo `kong` muestra puertos publicados.

Evidencias del despliegue:

```bash
docker exec kong kong version              # 3.9.5
docker exec kong getent hosts estudiantes  # IP interna asignada por Docker
curl.exe -i http://localhost:8001/status   # Admin API responde 200
```

| URL | Qué es |
|---|---|
| `http://localhost:8000` | Proxy de Kong, único punto de entrada para los consumidores |
| `http://localhost:8001` | Admin API, accesible **solo desde tu máquina** (`127.0.0.1`) |

## 6. Autenticación (API Key)

| Dato | Valor |
|---|---|
| Consumer | `socio-externo-demo` |
| Header | `X-API-Key` |
| Key (ficticia) | `demo-key-educonnect-2026` |

La key solo se acepta por header (no en la URL) y Kong la quita antes de reenviar la solicitud al backend.

```bash
# Sin key              -> 401
curl.exe -i http://localhost:8000/api/estudiantes

# Key incorrecta       -> 401
curl.exe -i -H "X-API-Key: clave-incorrecta" http://localhost:8000/api/estudiantes

# Key válida           -> 200
curl.exe -i -H "X-API-Key: demo-key-educonnect-2026" http://localhost:8000/api/estudiantes
```

## 7. Rate limiting

- **Rutas de estudiantes, matrículas y pagos:** 5 solicitudes por minuto para el consumer, **compartidas entre las tres rutas** (el plugin está asociado al consumer, no a una ruta).
- **Certificados:** 2 solicitudes por minuto, con contador propio.
- Política `local`: el contador vive en la memoria de esta instancia de Kong y se pierde al reiniciarla.

Secuencia reproducible de 7 solicitudes (PowerShell). Espera al menos un minuto desde tu última prueba para partir de un contador en cero:

```powershell
1..7 | ForEach-Object { $c = curl.exe -s -o NUL -w "%{http_code}" -H "X-API-Key: demo-key-educonnect-2026" http://localhost:8000/api/estudiantes; "$_ -> $c  $(Get-Date -Format HH:mm:ss)" }
```

Resultado esperado: `200` en las primeras 5 y `429` en la 6ª y 7ª. Cada respuesta incluye `X-RateLimit-Limit-Minute` y `X-RateLimit-Remaining-Minute`.

## 8. Pruebas con Postman

Importa `tests/EduConnect.postman_collection.json`. Define las variables de colección `baseUrl` = `http://localhost:8000` y `apiKey` = `demo-key-educonnect-2026`.

| Carpeta | Esperado |
|---|---|
| Positivas | 200 y `X-Servicio` correcto en las tres rutas |
| AuthN | 401 sin key y con key incorrecta |
| RutaNoRegistrada | 404 de Kong (`no Route matched`) |
| RateLimiting | 200 en las 5 primeras, 429 después |
| Certificados | 200, 200, 429; luego estudiantes conserva su cuota (contadores independientes); 401 sin key |
| BackEndCaido | 5xx de Kong (ver abajo, **ejecución manual**) |

**Orden recomendado:** Positivas → AuthN → RutaNoRegistrada → RateLimiting → Certificados.

- Las solicitudes con key válida **consumen cuota**. Las carpetas RateLimiting y Certificados esperan los valores exactos de `X-RateLimit-Remaining-Minute`, por lo que deben ejecutarse con el contador en cero (espera un minuto desde la última prueba con key válida).
- Si ejecutas la colección completa con el Runner, deja el delay en 0 y **desmarca BackEndCaido**.

### Prueba de backend no disponible (manual)

Postman no puede detener contenedores, por eso esta prueba se hace a mano:

```bash
docker compose stop matriculas
curl.exe -i -H "X-API-Key: demo-key-educonnect-2026" http://localhost:8000/api/matriculas
docker logs kong --tail 5
curl.exe -i -H "X-API-Key: demo-key-educonnect-2026" http://localhost:8000/api/estudiantes   # sigue en 200
docker compose start matriculas
```

Kong debe responder con un error 5xx propio (no 404, porque la Route existe pero el destino no responde). El código exacto depende de la causa que registre el log de Kong. Los demás servicios siguen respondiendo.

## 9. Detener la solución

```bash
docker compose down
```

## 10. Solución de problemas

Revisa en este orden, y mira los logs antes de cambiar varias cosas a la vez:

1. `docker compose ps`: ¿los contenedores están `Up`?
2. `docker logs kong --tail 30`: Kong valida el archivo `kong.yml` al arrancar y rechaza campos desconocidos (por ejemplo, un `_format_version` mal escrito).
3. `curl.exe http://localhost:8001/routes`: si devuelve `"data":[]`, Kong no cargó las Routes. Guarda `kong.yml` y ejecuta `docker compose restart kong`.
4. ¿El mock responde dentro de la red? `docker logs <servicio> --tail 10`.
5. ¿Coincide la ruta, la key y el límite de tráfico? Compara tu solicitud con las tablas de las secciones 1, 6 y 7.

Si el contenedor de Kong aparece en `Restarting`, es casi siempre un error en `kong.yml`: el log indica el campo o la línea.

## 11. Límites de la PoC

- No resuelve **autorización de negocio** ni identidad de usuarios finales: una API Key válida identifica al consumer, pero no demuestra que pueda ver un recurso concreto (por ejemplo, una matrícula ajena). Esa verificación debe hacerla cada backend.
- No incluye monitoreo distribuido integral ni alta disponibilidad: hay una sola instancia de Kong, que es un punto único de falla.
- Rate limiting con contador local: con varias instancias del gateway el límite real se multiplicaría. En una arquitectura empresarial se usaría un contador compartido (por ejemplo, `policy: redis`).
- La API Key está en el repositorio (aceptable solo por ser ficticia), el tráfico es HTTP sin TLS y el Admin API no tiene autenticación (solo está ligado a `localhost`).
- Datos y backends simulados, sin persistencia.

## 12. Mejoras para un despliegue productivo

- Varias instancias de Kong detrás de un balanceador, con contador de rate limiting compartido.
- TLS en el borde y Admin API protegido o no expuesto.
- Secretos en un gestor de secretos, con rotación de credenciales; evaluar OAuth 2.0 / JWT en lugar de API Keys.
- Health checks, timeouts y reintentos hacia los backends.
- Observabilidad centralizada: logs, métricas y trazas.
- Configuración versionada en Git y desplegada con decK o GitOps, usando una versión de Kong con soporte vigente.

## 13. Uso de IA y fuentes

Se usó un asistente de IA (Claude) como apoyo para investigar conceptos, discutir decisiones de arquitectura y depurar la configuración. Cada decisión se contrastó con documentación técnica.

Fuentes: documentación oficial de Kong Gateway (<https://developer.konghq.com/gateway/>), modo DB-less, plugins Key Authentication y Rate Limiting, política de soporte de versiones de Kong, documentación de Docker Compose y de Postman, y OWASP API Security.
