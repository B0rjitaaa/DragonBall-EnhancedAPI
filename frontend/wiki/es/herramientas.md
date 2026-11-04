# Herramientas (Tools)

La página **«Tools»** (herramientas, `/tools`) reúne lo de mantenimiento, para que no estorbe en las páginas de uso diario. Está en el menú de arriba, junto a «Wiki»; en el móvil, dentro de **«More»** (más).

## Collection data (datos de la colección)

Los cuatro botones para sacar y meter datos de tu colección:

| Botón | Qué hace |
|---|---|
| **«Download backup»** | Descarga una copia completa en JSON: ubicaciones, mazos, wants y todas las copias. |
| **«Restore backup»** | Vuelve tu colección al estado de esa copia (**sustituye**), con vista previa. |
| **«Download CSV»** | Descarga tu colección en una hoja de cálculo. |
| **«Import CSV»** | Suma a tu colección las copias de un CSV, con vista previa. |

Cómo funciona cada uno: [Importar, exportar y copia](importar-exportar.md).

## System status (estado del sistema)

Las mismas comprobaciones que `/api/health/`, cada una con un punto de color:

- **verde**: va bien;
- **ámbar**: atrasado (p. ej. los precios o la errata llevan días sin actualizarse) o sin configurar en esta máquina;
- **rojo**: algo crítico está caído (base de datos, Redis, workers);
- **gris**: opcional y sin configurar (la cámara fija).

Se vuelve a comprobar sola cada minuto, o con **«↻ Check again»**. Cuando algo crítico cae, la franja roja de arriba de la web lleva a esta página. Qué mira cada comprobación: [Tareas programadas](tareas-programadas.md#salud).

## Bandai sync (sincronización con Bandai)

Las 10 últimas sincronizaciones del catálogo: cuándo empezaron, si fue completa (**«Full»**) o solo de cartas nuevas (**«New cards»**), el resultado, cuánto tardaron y cuántas cartas había, nuevas, actualizadas y fallidas. Si una falló, pasa el ratón por encima para ver el error. **«See what changed →»** lleva a [Novedades](novedades.md).

Las sincronizaciones se lanzan solas cada día, y también puedes lanzar una ahora:

- **«↻ Sync new cards»** (sincronizar cartas nuevas): solo las que aún no están en el catálogo, p. ej. el día que sale una colección. Tarda unos segundos.
- **«Full sync…»** (completa): vuelve a descargar todas las cartas y recoge cambios de texto, imagen y errata. Tarda hora y media, así que pide confirmación (**«Yes, full sync»**).

Mientras hay una en marcha los botones se desactivan y la tabla se actualiza sola. Más en [Datos y sincronización](datos-y-sincronizacion.md).

## Recent errors (últimos errores)

Los últimos errores del servidor, de las tareas y de la web, **agrupados** (el mismo fallo sale una vez, con **×N** veces). Pulsa uno para ver la petición, dónde saltó y el detalle completo (traceback). Por defecto salen solo los pendientes; quita **«Only open ones»** para ver también los resueltos.

Se marcan como resueltos en el admin: ver [Registro de errores](registro-de-errores.md).
