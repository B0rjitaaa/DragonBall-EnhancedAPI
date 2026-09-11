# DragonBall-EnhancedAPI

Buscador avanzado de cartas de **Dragon Ball Super Card Game** (BT1–BT31, promos, starter decks, expansiones…)
con filtros por todos los atributos de `card_config`, por habilidades (`[Activate: Main]`, `[Limit 1]`,
`[Counter: Play]`…) y búsquedas anidadas **Y / O / NO**.

| Servicio        | Tecnología                         | Puerto |
|-----------------|------------------------------------|--------|
| `frontend`      | React 19 + Vite + TypeScript       | 5173   |
| `backend`       | Django 5.2 + Django REST Framework | 8000   |
| `celery_worker` | Celery (tareas en segundo plano)   | —      |
| `celery_beat`   | Celery Beat (tareas programadas)   | —      |
| `db`            | PostgreSQL 16                      | 5432   |
| `redis`         | Redis 7 (broker + caché)           | 6379   |

## Arranque

```bash
cp .env.example .env              # ajusta DJANGO_SECRET_KEY si vas a exponerlo
cp /ruta/a/cartas_dbs.json data/  # opcional: importación inicial sin esperar a Bandai
make up                           # = docker compose up -d --build
```

- Web: <http://localhost:5173>
- API: <http://localhost:8000/api/> · Swagger: <http://localhost:8000/api/docs/>
- Admin: <http://localhost:8000/admin/> (crea usuario con `make superuser`)

Si `data/cartas_dbs.json` existe y la BD está vacía, se importa solo al arrancar.
Si no, lanza `make sync` y el worker descargará todo desde Bandai.

## Actualizar tras un `git pull` (migraciones incluidas)

```bash
make deploy   # git pull + rebuild si cambian dependencias + migraciones + reinicio de backend/Celery
```

Para que ocurra solo en cada `git pull` sobre `main` (recomendado en el servidor / Raspberry Pi),
activa una vez el hook del repositorio:

```bash
make hooks    # = git config core.hooksPath .githooks
```

A partir de ahí, `git pull` ejecuta `scripts/deploy.sh`: reconstruye imágenes solo si cambian
`requirements.txt`, `package.json` o los Dockerfiles, aplica migraciones y reinicia backend y Celery.
Para saltarlo puntualmente: `SKIP_DEPLOY_HOOK=1 git pull`.

## Sincronización con Bandai (Celery)

Programado en `config/settings.py → CELERY_BEAT_SCHEDULE` (editable luego desde `/admin` → *Periodic tasks*):

| Tarea                    | Cuándo              | Qué hace                                  |
|--------------------------|---------------------|-------------------------------------------|
| `sync-new-cards-daily`   | Todos los días 04:00 | Descarga solo las cartas nuevas          |
| `sync-all-cards-weekly`  | Domingos 05:00       | Vuelve a descargar todas (erratas, textos)|
| `sync-banlist-daily`     | Todos los días 03:30 | Lista oficial Banned/Limited              |
| `sync-keyword-skills-weekly` | Lunes 03:45      | Keyword skills oficiales y sus textos     |

El cliente (`cards/bandai.py`) usa `curl_cffi` (huella de Chrome), limita el ritmo
(`BANDAI_REQUEST_DELAY`, `BANDAI_WORKERS`) y, si Bandai devuelve 403/429, pausa y reintenta.
Guarda cada 200 cartas, así que un corte no pierde lo descargado. Historial en `GET /api/sync/`.

## Cartas prohibidas y limitadas (Ban / Limit)

La lista oficial (<https://www.dbs-cardgame.com/us-en/rule/banned-limited-cards.php>) se descarga cada día
a las 03:30 (`sync-banlist-daily`) y marca `legality` = `banned` | `limited` | `legal` en todas las
impresiones de cada `card_number`. La migración carga una copia incluida en el proyecto
(`cards/data/banlist_snapshot.json`, actualizada a 19/06/2026) para que funcione desde el primer arranque.

```bash
docker compose exec backend python manage.py sync_banlist             # forzar actualización
docker compose exec backend python manage.py sync_banlist --snapshot  # volver a la copia local
```

`GET /api/banlist/` devuelve la lista; en búsquedas: `{"field": "legality", "operator": "in", "value": ["banned"]}`.

## Keyword skills (nombres y textos oficiales)

Las habilidades se clasifican como en <https://www.dbs-cardgame.com/us-en/rule/keyword-skills.php>:
**Activate Timing** (`timing`), **Keyword Skills** (`keyword_skill`) y **Keywords** (`keyword_rule`),
con el nombre oficial (`Over Realm X`, `Once per Turn`, `Counter : Play`…) y su texto, que la web
muestra al pasar el ratón. La variante exacta sigue disponible en `keyword` (`Over Realm 3`).

- Solo cuentan las habilidades **propias** de la carta (al inicio de línea o encadenadas). Las que
  se mencionan dentro de una frase ("it gains [Barrier]", "activates [Revive]") van a `keyword_mention`.
- Lo que no está en la web oficial (p. ej. `Z-Stack`, posterior a su última actualización) aparece
  en Keyword Skills sin descripción.
- Se actualiza cada lunes a las 03:45 (`sync-keyword-skills-weekly`); la migración carga una copia local.

```bash
docker compose exec backend python manage.py sync_keyword_skills             # forzar actualización
docker compose exec backend python manage.py sync_keyword_skills --snapshot  # volver a la copia local
```

`GET /api/keyword-skills/` devuelve las skills con su texto, sus variantes y el mapa de alias.

## API

### Campos filtrables — `GET /api/fields/`

| Tipo     | Campos                                                                                   | Operadores                          |
|----------|------------------------------------------------------------------------------------------|-------------------------------------|
| texto    | `name`, `text` (ambas caras), `card_number`                                               | `contains`, `eq`, `startswith`      |
| número   | `energy`, `power`, `back_power`, `combo_energy`, `combo_power`, `z_energy_cost`           | `eq`, `ne`, `lt`, `lte`, `gt`, `gte`, `between`, `isnull` |
| enum     | `type`, `rarity`, `series`, `set_code`, `card_set`, `legality`                            | `eq`, `in`                          |
| lista    | `color`, `color_cost`, `character`, `special_trait`, `era`, `timing`, `keyword_skill`, `keyword_rule`, `keyword`, `keyword_mention`, `keyword_family`, `regulation` | `has`, `has_any`, `has_all`, `is_empty` |
| booleano | `has_back`                                                                                | `eq`                                |

- `keyword`: habilidad exacta normalizada (`Activate: Main`, `Limit 1`, `Counter: Play`, `Once Per Turn`…).
  `[Activate : Main/Battle]` cuenta también como `Activate: Main` y `Activate: Battle`.
- `keyword_family`: agrupa variantes (`Limit 1`/`Limit 2` → `Limit`, `Counter: Play`/`Counter: Attack` → `Counter`).
- `special_trait`, `character`, `era`, `color` se separan por `/` (`Saiyan/Earthling` → `Saiyan` + `Earthling`).

### Búsqueda anidada — `POST /api/cards/search/`

```json
{
  "q": "goku",
  "ordering": "-power",
  "page": 1,
  "query": {
    "op": "and",
    "children": [
      {"field": "type", "operator": "in", "value": ["BATTLE", "Z-BATTLE"]},
      {"field": "energy", "operator": "lte", "value": 3},
      {"op": "or", "children": [
        {"field": "keyword", "operator": "has", "value": "Counter: Play"},
        {"field": "keyword_family", "operator": "has_all", "value": ["Barrier", "Blocker"]}
      ]},
      {"field": "color", "operator": "has", "value": "Black", "not": true}
    ]
  }
}
```

Cualquier nodo admite `"not": true`. Límites: 6 niveles y 60 condiciones.
Ordenación: `number` (natural: BT1, BT2… BT10), `name`, `energy`, `power`, `newest`; prefijo `-` para descendente.

### Filtros rápidos por querystring — `GET /api/cards/`

`/api/cards/?color=Red&color=Blue&energy_max=3&keyword=Barrier&keyword=Blocker&keyword_match=all&q=vegeta`

Números: `campo`, `campo_min`, `campo_max`. Listas: varios valores = O (`campo_match=all` para Y).
También acepta `query=<árbol JSON>`.

### Facetas — `GET|POST /api/facets/`

Valores y recuentos de cada atributo (cacheados en Redis, se invalidan tras cada importación/sync).
`POST {q, query, only?}` devuelve los recuentos dentro de una búsqueda.

## Comandos útiles

```bash
make import      # importar data/cartas_dbs.json
make sync        # encolar sync (solo nuevas) · make sync-full para todas
make test        # tests del backend
make logs        # logs de todos los servicios
make reset       # borra BD y Redis (¡cuidado!)
```

## Estructura

```
backend/
  config/            settings, urls, celery
  cards/
    models.py        Card (atributos normalizados + JSON original) y SyncRun
    parsing.py       card_config → campos; extracción y normalización de habilidades
    query.py         árbol AND/OR/NOT → Q de Django (con validación)
    facets.py        recuentos por atributo (Postgres unnest) + caché Redis
    bandai.py        cliente de Bandai TCG+ (ritmo, reintentos, pausa ante bloqueos)
    tasks.py         sync_cards (Celery)
    importer.py      upsert masivo
frontend/src/
  App.tsx            estado, búsqueda y URL compartible
  components/        FacetPanel, QueryBuilder, CardGrid, CardModal
  lib/               tipos, cliente API, construcción de la query
```

## Pendiente / siguientes pasos

- `docker-compose.prod.yml` (gunicorn + build estático del front con nginx)
- Agrupar alt-arts por `card_number`
- Mazos / colecciones de usuario
