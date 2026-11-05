# Herramientas (Tools)

La página **«Tools»** (herramientas, `/tools`) reúne el **histórico de cambios** y lo de mantenimiento, para que no estorbe en las páginas de uso diario. Está en el menú de arriba, junto a «Wiki»; en el móvil, dentro de **«More»** (más).

## History (histórico de cambios)

Todo lo que cambia en tu colección queda apuntado, una línea por acción, para verlo y **deshacerlo**:

- copias que sumas o quitas a mano (**−** / **+**), que mueves o marcas como falsas, y sus notas;
- el escáner (cada sesión de ráfaga es una línea) y lo que se cambie desde el admin;
- ubicaciones creadas, cambiadas o borradas, el orden («My order») y el archivador (mover un bolsillo, apilar copias, páginas);
- los mazos: importarlos, guardar o borrar listas, hacer principal una versión, el side, las cartas «missing», archivarlos o volver a usarlos;
- importar un CSV y restaurar una copia de seguridad.

Las wants y las partidas aún no entran. El histórico empieza a contar desde que se instaló: lo de antes no está.

En **Tools** salen los últimos cambios; **«Open the full history →»** abre la página completa (`/tools/history`), con buscador (una carta por nombre o número), tipo de cambio, ubicación o mazo, origen (web, escáner, admin) y fechas. Cada línea dice qué pasó, cuántas copias entran (**+**), salen (**−**) o se mueven (**⇄**) y cuándo. Los clics seguidos sobre la misma carta (por ejemplo, cinco **+**) se juntan en una sola línea.

**Pulsa una línea** para ver el detalle: carta a carta, cuántas copias había en cada sitio antes y después, y la posición del archivador si cambió; y lo demás (mazo creado, lista nueva, side…).

### Deshacer

**«↶ Undo…»** en un cambio lo deja todo como estaba: cada copia vuelve a su sitio exacto, **con su posición en el archivador**. Deshacer una importación de mazo, por ejemplo, devuelve las cartas a los archivadores y cajas de los que salieron, borra el mazo creado, su lista y su lista de recogida, y quita las versiones que guardaron los mazos que cedieron cartas.

Se puede deshacer **cualquier cambio**, no solo el último, con una protección: si después tocaste esas mismas cartas, no se deshace a ciegas. Te avisa de qué cambios posteriores las modificaron para que los deshagas antes (del más reciente al más antiguo). Deshacer queda también como una línea más del histórico (**UNDO**), y el cambio deshecho sale marcado **undone**.

### Puntos de restauración

Justo antes de **restaurar una copia de seguridad**, **importar un CSV** o **importar un mazo**, se guarda sola una foto completa de la colección (**⟲ point** en su línea). Al final de la página, **«Restore to this point…»** enseña cuántas cartas cambiarían y, al confirmar, lo deja todo como estaba en ese momento, **también lo que hiciste después**. Es para cuando algo salió muy mal; para lo normal basta con «Undo». Volver a un punto también se puede deshacer. Se guardan **90 días** (el histórico, siempre).

### En la ficha de una carta y en un mazo

- La ficha de cada carta tiene **«History of this card»** (plegado): los cambios de sus copias, de cualquier impresión.
- La vista de un mazo tiene **«History of this deck»** al final: lo que entró y salió de su caja, sus listas y su side.

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
