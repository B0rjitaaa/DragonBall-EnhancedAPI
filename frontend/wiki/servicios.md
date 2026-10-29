# Qué tiene que estar en marcha

La lista completa de todo lo que debe estar ejecutándose para que la web funcione entera, dónde corre cada cosa y cómo comprobarla. Sirve de **repaso tras instalar** y de **primera parada cuando algo falla**.

## Resumen

```
Servidor
├── Docker Compose ── 7 contenedores siempre arriba (+ «camera» si hay webcam)
│   ├── db · redis · backend · frontend
│   └── celery_worker · scanner_worker · celery_beat ── 11 tareas programadas
├── systemd ── dbs-backup.timer (03:30) · dbs-backup-request.path («Hacer copia ahora»)
└── git ── hook post-merge (despliega en cada git pull)

Fuera del servidor (opcional; ver «Extras» en Instalación)
├── copias ── otro equipo de casa (rsync) · la nube (rclone) · un VPS
└── vigilancia ── Healthchecks.io (latido cada 5 min) · watchdog.py en otro equipo de casa
```

## 1. Contenedores de Docker

Los siete, en el servidor y en local, tienen que salir como `running` en `docker compose ps`. Si alguno se cae, se reinicia solo (`restart: unless-stopped`).

| Contenedor | Qué hace | Si se para… | Cómo comprobarlo |
|---|---|---|---|
| **`db`** (PostgreSQL 16) | Guarda todos los datos. | No funciona nada. Franja roja: «La base de datos no responde». | `docker compose exec db pg_isready` |
| **`redis`** (Redis 7) | Caché y colas de las tareas. | Paran el escáner y las tareas. Franja roja. | `docker compose exec redis redis-cli ping` → `PONG` |
| **`backend`** (Django) | La API y el admin. En producción, gunicorn con 1 proceso y 4 hilos. | La web carga, pero vacía: «El servidor no responde ahora mismo». | `curl -s localhost:8000/api/fields/ \| head -c 80` |
| **`frontend`** | La web. En local, Vite en el 5173. En producción, nginx en 80, 443 y 5173, y además reparte `/api` y `/admin` al backend. | No se abre la web. | Abrir la web en el navegador |
| **`celery_worker`** | Tareas de fondo: sincronizaciones, precios, avisos, importaciones. Se recicla al pasar de ~250 MB. | No se actualiza nada ni llegan avisos. Franja roja: «Las tareas en segundo plano… están paradas». | `docker compose exec celery_worker celery -A config inspect ping` |
| **`scanner_worker`** | Reconoce las fotos del escáner (cola `scanner`, de una en una). Carga las huellas en memoria al arrancar. | El escáner no identifica. Franja roja: «El escáner no está disponible». | `docker compose logs --tail 20 scanner_worker` |
| **`celery_beat`** | El reloj: lanza las tareas programadas. | No se ejecuta nada programado (sync, precios, avisos…), aunque todo parezca ir bien. | `docker compose logs --tail 20 celery_beat` |
| `camera` (opcional) | Webcam USB del servidor. Solo con `COMPOSE_PROFILES=camera`. | Solo falla «Webcam del escáner»; el móvil sigue funcionando. | `docker compose exec camera curl -s localhost:8080/health` |

> [!WARNING]
> Si **`celery_beat`** se para, no salta ningún aviso de salud por sí mismo: los avisos los lanza precisamente beat. Lo notarás porque los datos dejan de actualizarse (Novedades, precios) y, al cabo de 2 días, por los avisos 🟡 de «sync de cartas» y «precios». Si configuras la **vigilancia de caídas** (el latido a Healthchecks.io o el vigilante en otro equipo), sí te enterarás enseguida: el latido deja de llegar en cuanto beat se para.

### Arrancar, parar y reiniciar

```bash
docker compose ps                         # estado de todos
docker compose up -d                      # arranca lo que falte (y aplica cambios del .env o de volúmenes)
docker compose restart backend            # reinicia uno
docker compose restart backend celery_worker celery_beat scanner_worker   # lo que reinicia un despliegue
docker compose logs -f --tail 100 backend # logs en directo de uno
docker compose down                       # para todo (los datos se conservan)
```

## 2. Tareas programadas (dentro de `celery_beat`)

Las lanza `celery_beat` y las ejecutan los workers (las del escáner, `scanner_worker`). **No hay que arrancarlas a mano**: basta con que los tres contenedores de Celery estén arriba. Horas de Madrid.

| Tarea | Cuándo | Qué hace |
|---|---|---|
| `check-health-alerts` | Cada 5 min | Revisa la salud y avisa por Telegram |
| `scanner-keep-warm` | Cada 60 s | Mantiene el reconocimiento cargado |
| `scanner-cleanup-old-scans` | Cada hora (min. 10) | Borra fotos de escaneos de más de 24 h, o si pasan de 2 GB |
| `sync-banlist-daily` | 03:30 | Ban list oficial |
| `sync-new-cards-daily` | 04:00 | Cartas nuevas de Bandai |
| `sync-prices-daily` | 05:15 | Cardmarket, TCGplayer, dólar y precios; después rehace `data/precios_dbs.json` |
| `purge-resolved-errors` | 05:30 | Limpia errores resueltos hace más de 90 días |
| `sync-keyword-skills-weekly` | Lunes 03:45 | Keyword skills oficiales |
| `sync-errata-weekly` | Lunes 03:50 | Erratas oficiales |
| `sync-rulings-weekly` | Lunes 03:55 | Card Q&A oficial |
| `sync-all-cards-weekly` | Domingos 05:00 | Vuelve a descargar todo el catálogo |

Además, hay tareas que se lanzan solas cuando toca, sin horario:
- **`identify_card`**, con cada foto del escáner;
- **`build_fingerprints`**, tras un sync con cartas nuevas y al arrancar el `scanner_worker` si faltan huellas (instalación nueva);
- **`notify_error`**, con cada error nuevo.

Más en [Tareas programadas y avisos](tareas-programadas.md).

## 3. Servicios del sistema en el servidor (systemd)

Fuera de Docker, en el propio servidor:

| Unidad | Qué hace | Cómo comprobarlo |
|---|---|---|
| **`dbs-backup.timer`** | Lanza la copia de seguridad cada día a las 03:30 (o al encender, si estaba apagado). | `systemctl list-timers dbs-backup.timer` → debe salir la próxima ejecución |
| **`dbs-backup-request.path`** | Lanza una copia cuando se pulsa «Hacer copia ahora» en el admin. | `systemctl status dbs-backup-request.path` → `active (waiting)` |
| `dbs-backup.service` | La copia en sí (`scripts/backup.sh`). No está «en marcha»: se ejecuta y termina. | `journalctl -t dbs-backup -n 30` |
| **`docker.service`** | Docker. Tiene que arrancar con el equipo. | `systemctl is-enabled docker` → `enabled` |

## 4. Fuera del servidor (opcional)

Solo si has configurado alguno de los [extras](instalacion.md#extras-opcionales):

| Qué | Qué hace | Cómo comprobarlo |
|---|---|---|
| **Copia fuera del servidor**: otro equipo, la nube o un VPS | Guarda otra copia de las copias, por si se rompe el disco del servidor. | En el admin, **Copias de seguridad** → «Copia fuera del servidor: ✅ copiada» |
| **Healthchecks.io** | Avisa si el latido del servidor deja de llegar. | El check está en **Up** en healthchecks.io |
| **cron: `watchdog.py`** en otro equipo | Comprueba que el servidor responde y avisa por Telegram si no. | `crontab -l` · `tail ~/dbs-watchdog/watchdog.log` |

## 5. Una sola vez, al instalar

No se quedan ejecutándose, pero sin ellas falta algo:

| Ejecución | Para qué | Cuándo repetirla |
|---|---|---|
| `docker compose up -d` (o `make install`; en un servidor, `make install SERVER=<ip>`) | Servicios, catálogo y precios del repositorio y el usuario del admin (admin / admin en local). En un servidor, además, el `.env` con claves aleatorias, HTTPS y la actualización con `git pull` | Nunca: luego todo va solo |
| `make superuser` | Otro usuario del admin | Si quieres más de uno |
| `scripts/local-https.sh <ip>` (lo hace `make install SERVER=`) | Certificado HTTPS para la cámara del móvil | Si cambia la IP, o a los ~2 años (caduca a los 825 días) |
| Instalar `ca.crt` en cada móvil | Que el móvil confíe en el certificado | En cada móvil nuevo |
| `make backups` | Copias diarias y bajo demanda (systemd) | Si cambian los ficheros de `scripts/systemd/` |
| (Opcional) `~/.config/dbs-backup.env` con `BACKUP_REMOTE` o `BACKUP_RCLONE` | Copia fuera del servidor | Si cambia el destino |
| (Opcional) `HEALTHCHECKS_URL` en el `.env`, o el cron del vigilante | Avisos cuando el servidor cae | Si cambia `watchdog.py` (volver a bajarlo con `curl`) |

## Comprobación rápida (todo de una vez)

Desde el servidor:

```bash
cd ~/Development/DragonBall-EnhancedAPI
docker compose ps --format '{{.Service}}: {{.State}}'
curl -s localhost/api/health/ | python3 -m json.tool | grep -E '"(status|label|ok)"'
systemctl list-timers dbs-backup.timer --no-pager
systemctl is-active dbs-backup-request.path
```

Lo que debes ver:
- **los 7 contenedores** en `running`;
- **la salud** con `"status": "ok"` y cada comprobación en `"ok": true`;
- **el temporizador** con su próxima ejecución;
- **la ruta de peticiones** en `active`.

Si algo no cuadra, ve a [Preguntas frecuentes y problemas](preguntas-frecuentes.md#problemas).
