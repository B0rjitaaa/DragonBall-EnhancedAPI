# Tareas programadas y avisos

Casi todo el mantenimiento es automático: sincronizaciones, precios, limpieza y copias. Si algo se rompe, te llega un **Telegram**. Aquí está la lista completa de lo que se ejecuta solo y de cuándo avisa.

## Lo que se ejecuta solo

Todas las horas son de Madrid.

| Hora | Tarea | Qué hace |
|---|---|---|
| **Cada 5 min** | Avisos de salud | Comprueba el sistema y avisa por Telegram si algo falla (ver abajo). |
| **Cada minuto** | Mantener el escáner caliente | Mantiene el reconocimiento cargado en memoria, para que el primer escaneo no tarde. |
| **Cada hora, en el minuto 10** | Limpiar fotos de escaneos | Borra las de más de 24 h y, si ocupan más de 2 GB, las más antiguas hasta bajar a 1,5 GB. |
| **03:30** | Ban list | Descarga la lista Banned/Limited oficial. |
| **03:30** | Copia de seguridad | La lanza systemd en el servidor, no Celery. Ver [Copias de seguridad](copias-de-seguridad.md). |
| **04:00** | Cartas nuevas | Sincronización rápida con Bandai. |
| **05:15** | Precios | Cardmarket, TCGplayer, cambio del dólar y recálculo de precios e historial. |
| **05:30** | Limpiar errores | Borra los errores resueltos hace más de 90 días. |
| **Lunes 03:45 / 03:50 / 03:55** | Keyword skills / Errata / Q&A | Listas oficiales de dbs-cardgame.com. |
| **Domingo 05:00** | Sincronización completa | Vuelve a descargar todas las cartas de Bandai. |

Las tareas que fallan por un problema pasajero (la ban list, los precios…) se **reintentan** solas hasta 3 veces, esperando entre intentos. Ninguna tarea puede durar más de 3 horas.

**Dónde están los horarios:**
- **Celery:** en `backend/config/settings.py` (`CELERY_BEAT_SCHEDULE`). Se ven, pero no se cambian, en el admin, en *Periodic tasks*.
- **Copia de seguridad:** en `scripts/systemd/dbs-backup.timer`.

> [!IMPORTANT]
> Para cambiar un horario hay que tocar `settings.py` y desplegar. Lo que cambies en el admin se pierde al reiniciar los servicios.

## Salud

La dirección **`/api/health/`** devuelve el estado de cada pieza del sistema:

| Comprobación | Tipo | Falla cuando… |
|---|---|---|
| Database (base de datos) | **Crítica** | No responde. |
| Redis (cache and queues) | **Crítica** | No se puede escribir y leer. |
| Celery worker | **Crítica** | No contesta en 1,5 s. |
| Scanner worker (worker del escáner) | **Crítica** | No contesta. |
| Bandai card sync (sync de cartas con Bandai) | Aviso | El último sync correcto tiene más de 2 días, o el último falló. |
| Official banlist | Aviso | Tiene más de 2 días. |
| Official errata | Aviso | Tienen más de 8 días. |
| Official Card Q&A | Aviso | Tiene más de 8 días. |
| Cardmarket prices (precios de Cardmarket) | Aviso | Tienen más de 2 días. |
| Backup (copia de seguridad) | Aviso | La última falló, tiene más de 30 h o falló la copia fuera del servidor (si está configurada). |
| Fixed station camera (cámara de la estación fija) | Informativa | No cuenta para el estado. |

El estado general es:
- **`ok`**: todo bien;
- **`degraded`**: falla algún aviso;
- **`down`**: falla algo crítico. En ese caso la dirección responde con el código 503.

**En la web**, solo los fallos **críticos** se ven, como una franja roja bajo el menú (ver [Enlaces, direcciones y atajos](enlaces-y-navegacion.md#el-menu-y-los-avisos)).

## Avisos por Telegram

Todos los avisos llegan al bot de Telegram del proyecto. Hay tres fuentes.

### 1. Avisos de salud (cada 5 minutos)

- **🔴 Crítico:** algo crítico lleva **10 minutos** caído. Llega con **sonido**: «🔴 **Celery worker** for 12 min».
- **🟡 Aviso:** un aviso (por ejemplo, la copia de seguridad) avisa a la primera, en **silencio**.
- **✅ Working again (vuelve a funcionar):** cuando se arregla: «It was failing for X».

Cada problema se avisa **una sola vez**, no cada 5 minutos.

### 2. Errores nuevos

Del [Registro de errores](registro-de-errores.md):
- **🐞 New error** (error nuevo);
- **🐞 A resolved error is back** (vuelve un error resuelto).

Llegan en silencio y con el enlace al admin.

### 3. Vigilancia de caídas (opcional)

Los avisos de salud los manda el propio servidor, así que **si el servidor se cae, no puede avisar**. Lo mismo pasa si se paran Redis, el worker o `celery_beat`, que son quienes lanzan los avisos. Para cubrirlo hay dos opciones, que se pueden usar juntas.

#### Con un servicio externo: latido a Healthchecks.io

Si en el `.env` está `HEALTHCHECKS_URL`, cada 5 minutos el servidor manda un **latido** a Healthchecks.io (o a otro servicio compatible), y es el servicio el que te avisa:
- **si el latido deja de llegar**: servidor apagado, sin Internet, o Redis, el worker o beat caídos;
- **si llega marcado como fallo** (`/fail`): algo crítico ha caído, y el mensaje dice qué.

No hace falta abrir puertos: es el servidor quien llama. Cómo darlo de alta: [Instalación → Vigilancia con un servicio externo](instalacion.md#vigilancia-con-un-servicio-externo-healthchecksio).

#### Con otro equipo de casa: el vigilante

El **vigilante** es un script (`scripts/watchdog.py`, solo con la librería estándar de Python). Corre en otro equipo de la red y cada 5 minutos consulta `http://192.168.1.50/api/health/`. Avisa de:
- **The server is not responding** (el servidor no responde);
- **The backend is not responding (the web loads, but without data)** (el backend no responde: la web carga, pero sin datos);
- **Redis is down (scanner and tasks stopped)** o **Celery worker is down (sync and alerts stopped)** (Redis o el worker de Celery caídos).

Como el resto, avisa si dura 10 minutos, una sola vez, y otra al arreglarse. Sus mensajes terminan en «(watchdog alert)» (aviso del vigilante).

**Instalación en el otro equipo:**

```bash
mkdir -p ~/dbs-watchdog && cd ~/dbs-watchdog
curl -fsSLO https://raw.githubusercontent.com/B0rjitaaa/DragonBall-EnhancedAPI/main/scripts/watchdog.py
# watchdog.env (permisos 600): HEALTH_URL, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
python3 watchdog.py watchdog.env --test   # «👀 Watchdog active»
crontab -e
# */5 * * * * /usr/bin/python3 /home/usuario/dbs-watchdog/watchdog.py /home/usuario/dbs-watchdog/watchdog.env >> /home/usuario/dbs-watchdog/watchdog.log 2>&1
```

Paso a paso en [Instalación](instalacion.md#vigilancia-con-otro-equipo-de-casa). El registro del vigilante está en `~/dbs-watchdog/watchdog.log`.

> [!NOTE]
> El token del bot y el chat están en el `.env` del servidor (y en `watchdog.env` si usas el vigilante). Sin ellos, simplemente no se envía nada.
