# Revisar precios en el admin

El emparejamiento automático con Cardmarket acierta casi siempre, pero hay casos que no puede decidir solo: promos, cartas que Cardmarket nombra distinto, varias impresiones con el mismo nombre… Esos casos van a una página de revisión en el admin:

**`/admin/prices/pricereview/`** (en el admin: *Prices (Cardmarket) → Review matches*, revisar emparejamientos)

![Review matches: pestañas arriba y, por carta, sus candidatos de Cardmarket y las demás opciones](../img/admin-precios.jpg)

> [!NOTE]
> La revisión **solo incluye cartas de las que tienes copias auténticas**: son las que afectan al valor de tu colección.

## Las pestañas

| Pestaña | Qué hay |
|---|---|
| **Your unmatched cards** (tus cartas sin emparejar) | Cartas sin producto de Cardmarket: no se encontró ninguno o había varios y no se pudo decidir. |
| **Suspect prices** (precios dudosos) | Cartas con un solo anuncio desproporcionado para su rareza (ver [precios sospechosos](precios.md#precios-sospechosos)). No cuentan en el valor hasta que las revises. |
| **Expensive cards with no sales** (cartas caras sin ventas) | Cartas de 10 € o más que solo tienen un anuncio, sin ventas. Muchas veces la carta está bien emparejada y simplemente es rara; otras, tu copia es otra edición. |
| **Matched by order** (emparejados por orden) | Grupos de impresiones con el mismo nombre en un set, emparejadas por orden de rareza, donde algo no cuadra (una rareza alta sale más barata que una baja), y cartas emparejadas con «Automatic (cheapest of several)» (la más barata de varias). |

Cada pestaña muestra cuántas cartas tiene. Las cartas van de 25 en 25, ordenadas por set y número.

## Qué puedes elegir para cada carta

En las tres primeras pestañas, cada carta muestra su imagen, número, rareza y set, y estas opciones:

| Opción | Qué hace |
|---|---|
| **Un producto candidato** | Los productos de Cardmarket que podrían ser esta carta, con su precio, su nombre, «its set» (su set) o la expansión, y ↗ para abrirlo en Cardmarket. «· current price» (precio actual) marca el que tiene ahora. |
| **Not on Cardmarket** (no está en Cardmarket) | La carta no tiene producto. Se queda sin precio de Cardmarket (si tiene TCGplayer, se usa ese). |
| **by hand [ ] €** (a mano) | Pon tú el precio, por ejemplo `3.50` (también vale con coma decimal). Al escribir en la casilla, la opción se marca sola. |
| **My copies are fake** (mis copias son falsas) | Tus copias pasan a [falsas](mi-coleccion.md#copias-falsas) y dejan de contar en el valor. |
| **I have another edition:** (tengo otra edición; en «Expensive cards with no sales») | Muestra las otras impresiones del mismo número con su precio. Al elegir una, **tus copias pasan a esa impresión**, en la misma ubicación y con sus notas y su marca de falsa. Es para cuando el escáner o la importación apuntaron a la edición equivocada. |

> [!TIP]
> Antes de elegir, abre el candidato con **↗**: en Cardmarket verás la foto y podrás comprobar que es tu edición (sello de torneo, foil, idioma…).

## Guardar

Abajo hay una **barra fija** con **«Clear all»** (desmarcar todo) y **«Save changes (N)»** (guardar los cambios). Puedes marcar muchas cartas y guardarlas de una vez. Si intentas salir con cambios sin guardar, la página avisa.

**Al guardar:**
- Tus elecciones **quedan fijas**: la actualización diaria no las cambia.
- Se aplican también a las **reimpresiones idénticas**: mismo número, rareza y set.
- El precio de esas cartas **se recalcula al momento**.
- Arriba aparece un resumen: «Saved N cards (and their identical reprints): …».

## La pestaña «Matched by order»

Aquí no se va carta a carta, sino **por grupos**: las impresiones de un mismo nombre en un set (normal, alt-art, SPR…). Para cada impresión hay un desplegable con los productos de ese nombre en la expansión.

- **«They are fine as they are»** (están bien así): confirma el grupo tal cual. Pasa a «Chosen by hand» (elegido a mano) y no vuelve a salir.
- **«Save changes»** (guardar cambios): guarda lo que hayas cambiado en los desplegables.

## Cómo se emparejó cada carta

En el admin, *Cardmarket links* (enlaces con Cardmarket) muestra el **método** de cada carta:

| Método | Significado |
|---|---|
| Automatic (only one) | Solo había un producto con ese nombre en su set. |
| Automatic (by order) | Varias impresiones con el mismo nombre: se ordenaron por rareza y precio. |
| Automatic (like its regular version) | Reimpresión: copia el producto de la impresión original. |
| Automatic (cheapest of several) | Varios productos posibles: se tomó el más barato con ventas. |
| Chosen by hand | Lo elegiste tú en la revisión. |
| Not on Cardmarket | Lo marcaste tú. |
| Price set by hand | Pusiste el precio tú. |

Los tres últimos son **manuales** y la actualización diaria los respeta siempre.

## Cada cuánto revisar

No hace falta entrar a diario. Revisa la página:
- cuando salga un **set nuevo** y lo hayas escaneado;
- cuando un precio de tu colección te parezca raro;
- de vez en cuando, para ver si hay **precios dudosos** nuevos (pestaña «Suspect prices»).
