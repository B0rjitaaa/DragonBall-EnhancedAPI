# API REST

Todo lo que hace la web pasa por una **API REST en JSON**, y se puede usar directamente: para scripts, para otras aplicaciones o para consultar datos.

- **Documentación interactiva (Swagger):** `/api/docs/`. Por ejemplo, `http://localhost:8000/api/docs/` en local.
- **Esquema OpenAPI:** `/api/schema/`.

> [!WARNING]
> - **Abierta:** la API no pide usuario, ni siquiera para escribir (añadir copias, anotar partidas…). Solo lanzar una sincronización exige ser administrador. Está pensada para la red de casa.
> - **Límite:** 1.000 peticiones por minuto (`/api/errors/`, 30).
> - **CSRF:** si tienes sesión iniciada en el admin, Django exige el token CSRF en las peticiones que escriben.

## Cartas y catálogo

| Método y ruta | Qué hace |
|---|---|
| `GET /api/cards/` | Listado con filtros por parámetros: `q`, `ordering`, `color=Red`, `energy_max=3`, `keyword=Barrier`… |
| `GET /api/cards/{id}/` | Detalle de una carta, con precio, impresiones e historial de precio. |
| `POST /api/cards/search/` | **Búsqueda completa**, igual que la del Buscador. Ver abajo. |
| `GET /api/cards/ref/{ref}/` | Convierte un enlace (`BT20-149-2`) en el id de la carta. |
| `GET /api/cards/export/?updated_since=…` | Los registros originales de Bandai, en el mismo formato que `cartas_dbs.json`. |
| `GET /api/fields/` | Campos que se pueden filtrar y sus operadores. |
| `GET /api/facets/` · `POST /api/facets/` | Recuentos por valor de cada campo: globales o dentro de una búsqueda. |
| `GET /api/banlist/` | La lista Banned/Limited. |
| `GET /api/keyword-skills/` | Keyword skills oficiales, sus variantes y las reglas de construcción. |
| `GET /api/changes/?kind=&page=` | [Novedades](novedades.md), 60 por página. |
| `GET /api/changes/count/?since=` | Cuántas novedades hay desde una fecha. |
| `GET /api/sync/` · `POST /api/sync/ {"full": true}` | Historial de sincronizaciones · lanzar una (solo administradores). |
| `GET /api/health/` | [Estado del sistema](tareas-programadas.md#salud). 503 si algo crítico falla. |
| `GET /api/thumbs/{id}/{versión}.webp` | Miniatura de una carta. |
| `GET /api/prices/radar/?days=7\|30\|90&scope=collection\|all` | Lo de la página [Precios](pagina-precios.md): suben, bajan, las más caras y la evolución del valor. |

### La búsqueda: `POST /api/cards/search/`

```json
{
  "q": "goku -\"super combo\"",
  "query": {
    "op": "or",
    "children": [
      {"op": "and", "children": [
        {"field": "type", "operator": "eq", "value": "LEADER"},
        {"field": "color", "operator": "has", "value": "Red"}
      ]},
      {"op": "and", "children": [
        {"field": "keyword_skill", "operator": "has", "value": "Counter : Play"},
        {"field": "energy", "operator": "lte", "value": 2}
      ]}
    ]
  },
  "ordering": "-power",
  "page": 1,
  "page_size": 48
}
```

**Parámetros:**
- **`q`**: el texto libre, con la misma sintaxis que en la web.
- **`query`**: el árbol del [Modo avanzado](modo-avanzado.md):
  - **grupos:** `{"op": "and"|"or", "not": false, "children": […]}`;
  - **condiciones:** `{"field", "operator", "value", "not"}`.
- **`ordering`**: `number`, `name`, `energy`, `power`, `newest`; con `-` delante, al revés.
- **`page`** y **`page_size`**: página y tamaño, hasta 200.
- **`scope: "collection"`**: busca solo en Mi colección. Añade a cada carta sus copias, a la respuesta el valor, y permite ordenar por `quantity` o `position` (con `location`). También acepta `include_fakes` y `fake`.

**Operadores por tipo de campo:**
- **texto:** `contains`, `eq`, `startswith`;
- **número:** `eq`, `ne`, `lt`, `lte`, `gt`, `gte`, `between`, `isnull`;
- **uno entre varios:** `eq`, `in`;
- **lista:** `has`, `has_any`, `has_all`, `is_empty`.

**Límites:** 6 niveles, 60 condiciones y 100 valores por condición.

## Mi colección

| Método y ruta | Qué hace |
|---|---|
| `GET /api/my-collection/` | Resumen de la colección. |
| `POST /api/my-collection/adjust/` | `{card_id, delta, location?, fake?}`: suma o quita copias (delta entre −10 y 10). Responde **409** si la carta está en varias ubicaciones y no se dice cuál. |
| `POST /api/my-collection/move/` | `{card_id, source, target, quantity, source_fake?, target_fake?, note_line?}`: mueve copias. |
| `POST /api/my-collection/note/` | Cambia la nota de las copias de una carta en una ubicación. |
| `POST /api/my-collection/reorder/` | «Mi orden» de una ubicación (de 1 a 500 ids). |
| `GET /api/my-collection/csv/` · `GET /api/my-collection/backup/` | Descargas en [CSV y JSON](importar-exportar.md). |
| `POST /api/my-collection/import/` | `{csv, apply}`: sin `apply` devuelve la vista previa; con `apply: true` suma las copias. |
| `POST /api/my-collection/restore/` | `{backup, apply}`: restaura la copia JSON **sustituyendo** la colección. Sin `apply`, la vista previa (antes/después, cambios por ubicación y carta, ubicaciones nuevas o vacías); con `apply: true`, lo aplica de una vez. |
| `GET` · `POST /api/my-collection/locations/` | Lista las ubicaciones (con Leader, avisos y valor) o crea una. |
| `PATCH` · `DELETE /api/my-collection/locations/{id}/` | Edita o borra una ubicación. |

## Mazos

Todas cuelgan de `/api/my-collection/`:

| Método y ruta | Qué hace |
|---|---|
| `GET decks/{id}/` | La caja, las versiones y las estadísticas contra cada Leader rival. |
| `POST decks/{id}/versions/` | Guarda una versión nueva de la lista. |
| `POST decks/{id}/plan/` | Calcula qué copias habría que mover para hacer principal una lista. |
| `POST decks/{id}/side/` | Cambia las copias del side deck. |
| `POST decks/{id}/matches/` | Anota una partida. |
| `GET` · `POST decks/{id}/to-history/` | Vista previa · pasar el mazo al histórico. |
| `POST decks/{id}/back-in-use/` | Vuelve a usar un mazo del histórico. |
| `GET` · `PATCH` · `DELETE deck-versions/{id}/` | Una versión: verla, renombrarla o borrarla. |
| `GET` · `POST deck-versions/{id}/restore/` | Plan · hacer principal una versión (mueve copias). |
| `PATCH` · `DELETE matches/{id}/` | Editar o borrar una partida. |

## Escáner

Todas cuelgan de `/api/scanner/`:

| Método y ruta | Qué hace |
|---|---|
| `GET scans/` | Escaneos, 30 por página. Filtros: `status`, `source`, `session`, `needs_review`, `added_to_collection`. |
| `POST scans/` | Con `image` (multipart), reconoce esa foto. Sin ella, captura de la webcam del servidor. Responde **202** y el reconocimiento sigue en segundo plano: consulta `GET scans/{id}/` hasta que termine. |
| `GET scans/{id}/` | El escaneo y su resultado. |
| `POST scans/{id}/confirm/` | `{card_id, copies?}`: confirma o corrige la carta, y el escáner aprende de la foto. |
| `POST scans/{id}/copies/` | Cambia cuántas copias suma (ráfaga). |
| `POST scans/{id}/undo/` | Deshace un escaneo añadido. |
| `GET` · `POST sessions/` · `GET sessions/{id}/` | Sesiones de ráfaga o archivador. |
| `POST sessions/{id}/end/` | Termina una sesión. |
| `GET camera/preview/` | Imagen JPEG de la webcam del servidor, o 503. |

## Otros

| Método y ruta | Qué hace |
|---|---|
| `POST /api/errors/` | La web informa de sus errores de JavaScript (ver [Registro de errores](registro-de-errores.md)). |
| `/media/…` | Fotos de escaneos e imágenes de impresiones propias. |

## Ejemplos

```bash
# Las 5 cartas rojas con más Power
curl -s -X POST http://192.168.1.50/api/cards/search/ \
  -H 'Content-Type: application/json' \
  -d '{"query":{"op":"and","children":[{"field":"color","operator":"has","value":"Red"}]},"ordering":"-power","page_size":5}'

# ¿Qué carta es BT20-149-2?
curl -s http://192.168.1.50/api/cards/ref/BT20-149-2/

# Estado del sistema
curl -s http://192.168.1.50/api/health/
```
