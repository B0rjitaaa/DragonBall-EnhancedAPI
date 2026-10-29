# Datos y sincronización

El catálogo no se escribe a mano: sale de **Bandai** y de la **web oficial del juego**, y se mantiene al día solo. Aquí se explica de dónde sale cada dato y cómo se actualiza.

## Las cartas: Bandai TCG+

El catálogo completo sale de la **API de Bandai TCG+** (la de la app oficial):
- `/card/list`: la lista de ids, de 500 en 500;
- `/card/{id}`: el detalle de cada carta (textos, atributos, imágenes, cara trasera…).

Para que Bandai no corte las peticiones:
- se piden con aspecto de navegador;
- van a un ritmo de una cada 0,25 s, con 4 hilos;
- si Bandai responde «demasiadas peticiones» (403 o 429), todo se pausa: un minuto la primera vez, el doble cada vez siguiente, hasta 15 minutos;
- si responde con un error de servidor (5xx), se reintenta hasta 8 veces.

### Los dos tipos de sincronización

| Tipo | Cuándo | Qué hace |
|---|---|---|
| **Solo cartas nuevas** | Todos los días a las 04:00 | Descarga solo los ids que aún no están. Es rápida. |
| **Completa** | Domingos a las 05:00 | Vuelve a descargar **todas** las cartas, para detectar cambios de texto, imagen o atributos. |

Detalles:
- **Nunca dos a la vez:** un candado en Redis impide que se solapen.
- **Guarda por lotes:** guarda cada 200 cartas, así que un corte no pierde lo ya descargado.
- **Historial:** cada sincronización queda en el admin (*sync runs*) con su resultado.
- **Novedades:** los cambios que detecta van a [Novedades](novedades.md).
- **Al terminar:** si hay cartas nuevas o cambiadas, se calculan sus huellas para el escáner.

### Lanzarla a mano

- **Desde la línea de comandos:**

  ```bash
  docker compose exec backend python manage.py sync_cards          # solo nuevas
  docker compose exec backend python manage.py sync_cards --full   # completa
  ```

- **Por la API:** `POST /api/sync/ {"full": true}`, con sesión de administrador.

### Del JSON de Bandai a los campos de búsqueda

Al guardar cada carta se procesa su información:
- **Atributos:** se separan en campos (Energy, Power, colores, Special Traits, Character, Era…).
- **Habilidades:** se extraen las que van entre corchetes, distinguiendo las que la carta **tiene** de las que solo **menciona**.
- **Erratas de Bandai:** se corrigen («Doube Strike» → «Double Strike»…) y se unifican las comillas.
- **Texto de búsqueda:** se prepara para que no importen los corchetes ni las mayúsculas.

## La web oficial: ban list, errata, Q&A y keyword skills

De **dbs-cardgame.com** se descargan cuatro listas:

| Lista | Cuándo | Para qué |
|---|---|---|
| **Banned / Limited** | Todos los días a las 03:30 | Marca qué cartas están prohibidas o limitadas, y desde cuándo. Se aplica a **todas las impresiones** del mismo número. |
| **Keyword skills** | Lunes a las 03:45 | Nombres y descripciones oficiales de las habilidades. Agrupa las variantes (Over Realm 3, 4… → Over Realm X). |
| **Errata** | Lunes a las 03:50 | Las erratas oficiales: texto de antes y después. |
| **Card Q&A** | Lunes a las 03:55 | Las preguntas y respuestas oficiales por carta. |

**Si la web oficial falla o cambia de formato, se mantiene lo que ya había.** Por ejemplo, si la ban list sale con menos de 10 cartas prohibidas, se da por rota y no se toca nada.

Cada lista tiene una **copia incluida en el código** (`backend/cards/data/*_snapshot.json`). Así una instalación nueva ya tiene datos desde el principio, y se puede volver a ella con `--snapshot`:

```bash
docker compose exec backend python manage.py sync_banlist --snapshot
```

## Imágenes y miniaturas

- **Imágenes:** las oficiales se descargan una vez a una caché local (`/data/card_images`). El escáner las usa para calcular las huellas.
- **Miniaturas:** la rejilla usa miniaturas **WebP de 320 px**, que se generan la primera vez que se piden. Su dirección lleva un resumen de la imagen original, así que si Bandai cambia la imagen, la miniatura se regenera sola. El navegador las guarda un año.

## Impresiones propias

Hay impresiones que Bandai **no publica** en su API: promos de Event Pack, premios de torneo, foils alternativos… Se pueden añadir a mano a partir de otra impresión de la misma carta:

```bash
docker compose exec backend python manage.py add_printing 5594 \
  --image https://…/imagen.png --set "Event Pack 09 (Alternate Foil)"
```

- **Qué copia:** todo lo de la carta original, con su propia imagen y set. No copia la cara trasera.
- **Su número interno:** a partir de **900.000.000**, así que la sincronización con Bandai nunca la toca ni la borra.
- **Escáner:** se calcula su huella al momento.
- **Copia de seguridad:** su imagen va al volumen `media`, que sí se copia.
- **Precio:** si se creó desde un producto de TCGplayer, su precio sale de ese producto exacto.

## Precios

Cardmarket, TCGplayer y el cambio del dólar se descargan cada día a las 05:15. Ver [De dónde sale cada precio](precios.md).

## Todos los comandos

Se ejecutan con `docker compose exec backend python manage.py <comando>`:

| Comando | Qué hace |
|---|---|
| `sync_cards [--full] [--async]` | Sincroniza con Bandai (por defecto, solo las nuevas). `--async` lo manda a Celery. |
| `import_cards [ruta] [--if-empty]` | Importa cartas desde un JSON (`.json` o `.json.gz`). |
| `export_cards [ruta]` | Vuelca el catálogo (por defecto a `/data/seed/cartas_dbs.json.gz`). |
| `export_prices [ruta]` | Vuelca los precios a `/data/precios_dbs.json` (se hace solo cada día; `.gz`, comprimido). |
| `import_prices [ruta] [--if-empty]` | Carga los precios de un volcado (sustituye los que haya). Sin ruta, el más reciente. |
| `sync_banlist [--snapshot]` | Actualiza la ban list. |
| `sync_errata [--snapshot]` | Actualiza las erratas. |
| `sync_rulings [--snapshot]` | Actualiza las Q&A. |
| `sync_keyword_skills [--snapshot]` | Actualiza las keyword skills y reclasifica las cartas. |
| `add_printing <id_base> --image URL --set "…"` | Añade una impresión propia. |
| `build_thumbs [--collection-only]` | Genera las miniaturas que falten, primero las de tu colección. |
| `build_fingerprints [--force] [--limit N]` | Calcula las huellas del escáner que falten (se lanza solo cuando faltan). |
| `download_card_images` | Descarga las imágenes oficiales que falten. |
| `import_checker <volcado>` | Importa la colección y los mazos del escáner antiguo (DragonBall-CameraCardChecker). |

Atajos del `Makefile`:
- `make install`, `make seed`, `make sync`, `make sync-full`, `make import`, `make export-prices`, `make import-prices`;
- `make shell`, `make psql`, `make migrate`, `make logs`, `make ps`, `make superuser`.

> [!CAUTION]
> `make reset` **borra la base de datos y Redis**.

## Primera instalación

Al arrancar por primera vez, el backend:
1. espera a Postgres;
2. aplica las migraciones, que cargan las copias incluidas de la ban list, la errata, las Q&A y las keyword skills;
3. si la base está vacía, importa el catálogo: `data/cartas_dbs.json` si existe y, si no, el del repositorio (`data/seed/cartas_dbs.json.gz`);
4. si no hay precios, los importa igual: `data/precios_dbs.json` o `data/seed/precios_dbs.json.gz`;
5. si no hay ningún administrador, crea **admin / admin** (o el de `DJANGO_SUPERUSER_*`).

Después, el `scanner_worker` calcula solo las huellas que falten. Sin volcados también funciona: `make sync` descarga el catálogo de Bandai y los precios se descargan solos en cuanto hay catálogo. Paso a paso en [Instalación](instalacion.md).
