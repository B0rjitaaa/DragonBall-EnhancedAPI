# Datos

- **`seed/`** (en el repositorio): el catálogo (`cartas_dbs.json.gz`) y los precios (`precios_dbs.json.gz`).
  Con la base de datos vacía, el backend los importa solos al arrancar, así que una instalación nueva tiene
  desde el principio todas las cartas con su precio. Se ponen al día con `make seed` (y un commit).
- **`cartas_dbs.json`** / **`precios_dbs.json`** (fuera de git): volcados más recientes; si existen, se usan en
  lugar de los de `seed/`. El servidor rehace `precios_dbs.json` tras cada descarga diaria de precios (05:15).
- `card_images/`, `scans/`: cachés del escáner (fuera de git).
