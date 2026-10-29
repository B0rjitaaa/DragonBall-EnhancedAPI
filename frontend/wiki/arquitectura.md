# Arquitectura

Cómo está montado DragonBall EnhancedAPI por dentro: qué piezas tiene, dónde corre cada una y cómo hablan entre sí.

## Visión general

```
                         ┌──────────────────────────── servidor (192.168.1.50) ─────────────────────────────┐
  Navegador / móvil ───▶ │ nginx (frontend)  ── /api, /admin ──▶  backend (Django + DRF, gunicorn)          │
   :80 · :443 · :5173    │   SPA React                                │                                     │
                         │                                            ├──▶ Postgres 16  (datos)             │
                         │                                            ├──▶ Redis 7      (caché y colas)     │
                         │   celery_worker   ◀── colas ──  celery_beat (horarios)                           │
                         │   scanner_worker  (reconocimiento de cartas, cola «scanner»)                     │
                         │   camera (opcional: webcam USB)                                                  │
                         │   systemd: copia diaria 03:30 ──▶ (opcional) otro equipo, nube o VPS             │
                         └──────────────────────────────────────────────────────────────────────────────────┘
  Opcional: latido a Healthchecks.io, o vigilante en otro equipo de casa ──▶ avisos por Telegram
  Fuentes externas: Bandai TCG+ API · dbs-cardgame.com · Cardmarket · tcgcsv.com (TCGplayer) · BCE
```

## Las piezas

| Servicio | Tecnología | Qué hace |
|---|---|---|
| **frontend** | React 19 + Vite + TypeScript. En producción, compilado y servido por **nginx 1.27** | La web. nginx también hace de puerta de entrada: pasa `/api/`, `/admin/` y `/static/` al backend y sirve `/media/`. |
| **backend** | **Django 5.2** + Django REST Framework, con **gunicorn** en producción | La API REST, el admin y toda la lógica. |
| **db** | **PostgreSQL 16** | Todos los datos. |
| **redis** | **Redis 7** | Base 0: colas de Celery. Base 1: caché (filtros, keyword skills…). |
| **celery_worker** | Celery 5 | Tareas de fondo: sincronizaciones, precios, avisos, importaciones. Se recicla al pasar de unos 250 MB de memoria. |
| **scanner_worker** | Celery, cola `scanner` | El reconocimiento de cartas del escáner, de una en una. Tiene las huellas cargadas en memoria. |
| **celery_beat** | Celery beat + django-celery-beat | Lanza las [tareas programadas](tareas-programadas.md). |
| **camera** | Servicio propio en Python (opcional, perfil `camera`) | Da acceso a una webcam USB del servidor (`/frame.jpg`, `/preview.jpg`, `/health`). |

## Las aplicaciones de Django

| App | Contenido |
|---|---|
| `cards` | Catálogo: cartas, búsqueda y filtros, sincronización con Bandai, ban list, errata, Q&A, keyword skills, novedades, miniaturas, salud y avisos. |
| `collection` | Ubicaciones y copias (Mi colección). |
| `decks` | Versiones de los mazos, side deck y partidas. |
| `scanner` + `vision` | Escaneos, sesiones, huellas y reconocimiento de imágenes (OpenCV). |
| `prices` | Cardmarket, TCGplayer, emparejamientos, precio de cada carta, historial y revisión. |
| `errorlog` | Registro de errores y sus avisos. |
| `backups` | La página de copias de seguridad del admin. |

## Los servidores

### servidor (producción)

- **Dirección:** `192.168.1.50`, en la red de casa.
- **Qué corre:** todos los servicios, con Docker Compose en modo producción.
- **Proyecto:** `/home/usuario/Development/DragonBall-EnhancedAPI`.
- **Copias:** en `/home/usuario/backups/dbs`.
- **Cómo se entra a la web:**
  - `http://192.168.1.50/` (puerto 80);
  - `http://192.168.1.50:5173/` (se mantiene para los enlaces antiguos);
  - `https://192.168.1.50/` (443, para la cámara del móvil).

### Fuera del servidor (opcional)

- **Copias:** una copia de las copias en otro equipo de casa o en un VPS (rsync), o en la nube (rclone).
- **Vigilancia de caídas:** un latido a Healthchecks.io, o el vigilante (`scripts/watchdog.py`) en otro equipo de casa. Ver [Tareas programadas y avisos](tareas-programadas.md#3-vigilancia-de-caidas-opcional).

Cómo montarlo: [Instalación → Extras](instalacion.md#extras-opcionales).

## Producción frente a desarrollo

Un solo `docker-compose.yml` vale para los dos. En el servidor se le suma `docker-compose.prod.yml`, poniendo en su `.env` `COMPOSE_FILE=docker-compose.yml:docker-compose.prod.yml`.

| | Desarrollo (tu Mac) | Producción (servidor) |
|---|---|---|
| **Backend** | `runserver` con recarga automática | `gunicorn` (1 worker, 4 hilos) |
| **Frontend** | Vite con recarga en caliente, en `:5173` | Compilado y servido por nginx en `:80`, `:443` y `:5173` |
| **Código** | Montado desde tu carpeta | Montado desde el clon del servidor |
| **Copias** | No | Monta las carpetas de copias para la página del admin |

> [!WARNING]
> En `docker-compose.prod.yml`, los cambios de cada servicio tienen que ir **después de todo el bloque `backend:`**. El 26/10/2026 un bloque mal colocado hizo que `celery_worker` heredara el comando de gunicorn.

## nginx

En producción, nginx (`frontend/nginx/`):
- sirve la web compilada; cualquier ruta desconocida devuelve `index.html` para que React la resuelva;
- pasa `/api/`, `/admin/` y `/static/` a Django. Si el backend está caído, `/api/` responde un JSON 503 «El servidor no responde en este momento…»;
- sirve `/media/` (fotos de escaneos, imágenes propias) y `/ca.crt` (el certificado para la cámara del móvil);
- acepta subidas de hasta 15 MB (fotos del escáner);
- tiene sus propias páginas de error (404 y 50x);
- activa **HTTPS** solo si encuentra `server.crt` y `server.key` en `./certs`. Los crea `scripts/local-https.sh` (ver [Usar el escáner](escaner.md#antes-de-empezar-la-camara-del-movil-necesita-https)).

## Variables de entorno

Se configuran en el `.env` de la raíz (hay un `.env.example` de plantilla). **Los valores reales y los secretos solo están en el `.env` de cada equipo.**

| Grupo | Variables |
|---|---|
| Django | `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, `CORS_ALLOWED_ORIGINS`, `LOG_LEVEL`, `API_ANON_RATE` |
| Postgres y Redis | `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`, `REDIS_URL` |
| Bandai y webs oficiales | `BANDAI_API_URL`, `BANDAI_GAME_TITLE_ID`, `BANDAI_REQUEST_DELAY`, `BANDAI_WORKERS`, `BANLIST_URL`, `ERRATA_URL`, `CARD_FAQ_URL`, `KEYWORD_SKILLS_URL`, `IMPORT_ON_START` |
| Escáner | `MATCH_HASH_THRESHOLD`, `MATCH_ORB_CANDIDATES`, `MATCH_MIN_CONFIDENCE`, `AUTO_ADD_MIN_CONFIDENCE`, `SCAN_RETENTION_HOURS`, `SCAN_PHOTOS_MAX_MB`, `SCAN_PHOTOS_TARGET_MB`, `KEEP_WARM_SECONDS`, `CAMERA_URL`, `MEDIA_ROOT`, `CARD_IMAGES_DIR` |
| Webcam (servicio camera) | `CAMERA_DEVICE`, `CAMERA_WIDTH`, `CAMERA_HEIGHT`, `CAMERA_FPS`, `CAMERA_FOURCC`, `CAMERA_CONTROLS`… |
| Copias | `BACKUP_STATUS_FILE`, `BACKUP_DIR`, `BACKUP_REQUEST_DIR`, `BACKUP_DIR_HOST` |
| Precios | `CARDMARKET_GAME_ID` (13), `TCGPLAYER_CATEGORY_ID` (27) |
| Avisos | `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `HEALTHCHECKS_URL` (vigilancia de caídas desde fuera) |
| Compose y build | `COMPOSE_FILE`, `COMPOSE_PROFILES`, `HTTP_PORT`, `HTTPS_PORT`, `VITE_HTTPS_PORT`, `RUN_MIGRATIONS` |
| Despliegue | `SKIP_PULL`, `FORCE`, `SKIP_DEPLOY_HOOK` |

## Seguridad

- **Red:** la web está pensada para la **red de casa** y no está expuesta a Internet.
- **API:** está **abierta**, también para escribir. Solo lanzar una sincronización (`POST /api/sync/`) exige ser administrador.
- **Admin:** exige usuario y contraseña.
- **Pendiente:** cuentas de usuario y endurecer el servidor (puertos de Postgres y del backend publicados, acceso SSH por clave). Hay que hacerlo antes de abrir la web fuera de casa.
