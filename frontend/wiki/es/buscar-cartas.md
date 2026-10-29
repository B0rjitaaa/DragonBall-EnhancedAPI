# Buscar cartas

El buscador, **«Search»** (`/`), es la página principal. Tiene todo el catálogo de Dragon Ball Super Card Game (Masters), con más de 9.000 impresiones. Desde aquí se busca por texto, se filtra con el panel lateral, se ordena y se abre la ficha de cualquier carta.

![«Search»: cabecera con la búsqueda, panel de filtros a la izquierda y la rejilla de resultados](../img/buscador.jpg)

## La cabecera

| Elemento | Qué hace |
|---|---|
| **★ DragonBall EnhancedAPI** | Vuelve al estado inicial. Borra el texto, los filtros y el árbol avanzado, pone «Advanced mode» en OFF, el orden en «Card number» y la página 1. También cierra la ficha abierta y sube al principio. |
| **☰** | Abre el panel de filtros. Solo aparece en pantallas estrechas (móvil o tableta, hasta 900 px). |
| **Caja de búsqueda** | Búsqueda por texto libre (ver abajo). |
| **Selector de orden** | Cambia el orden de los resultados. |
| **«Advanced mode OFF» / «ON»** | Muestra u oculta el constructor de búsquedas avanzadas. Ver [Modo avanzado](modo-avanzado.md). |

## Búsqueda por texto

La caja busca a la vez en el **nombre** (también el de la cara trasera de los Leaders), en el **número de carta** y en el **texto** de las dos caras.

- **Varias palabras: tienen que aparecer todas** (Y), en cualquier orden. `goku barrier` devuelve las cartas que tienen «goku» y también «barrier».
- **Trozos de palabra valen**: no distingue mayúsculas, así que `gok` ya encuentra a Goku.
- **`"frase exacta"` entre comillas**: las palabras tienen que ir juntas y en ese orden. `"draw 1 card"`.
- **`-palabra` para excluir**: quita las cartas que la contienen. También vale con frases: `-"Super Combo"`.
- **Corchetes y espacios no importan**: `it gains Barrier` encuentra «it gains **[Barrier]**», y `activate:main` encuentra «[Activate : Main]».
- **Busca solo cuando dejas de escribir** (150 ms después) y vuelve a la página 1.
- **Máximo 200 caracteres.** Si te pasas, aparece un error en rojo junto al contador.

> [!TIP]
> Mientras escribes, debajo de la caja aparece un recordatorio de la sintaxis: «Searches by words: **all** must appear. `"exact phrase"` in quotes · `-word` to exclude.»

> [!NOTE]
> El texto libre no tiene **O**. Para «una cosa u otra» usa los valores del panel (dentro de un mismo campo se combinan con O) o el [Modo avanzado](modo-avanzado.md).

## El panel de filtros

A la izquierda está el panel **«Filters»** (filtros). Cada apartado es un campo de la carta, y cada valor lleva al lado **cuántas cartas** lo cumplen.

![Panel de filtros con Color: Red y Type: BATTLE marcados, y las etiquetas de filtros activos sobre los resultados](../img/buscador-filtros.jpg)

### Los apartados

Arriba del todo hay dos casillas: **«Has errata»** y **«Has Q&A»**. Debajo, en este orden (los nombres de los campos van en inglés, como en las cartas):

| Apartado | Cómo se elige | Abierto de entrada |
|---|---|---|
| **Banned / Limited** | Botones: Banned, Limited, Legal | Sí |
| **Type** | Botones: BATTLE, LEADER, EXTRA, UNISON, Z-BATTLE… | Sí |
| **Color** | Botones con el color | Sí |
| **Energy** | Botones por coste | Sí |
| **Power** | Rango mín – máx | Sí |
| **Activate Timing** | Botones con su explicación oficial | Sí |
| **Keyword Skills** | Lista con explicación y variantes | Sí |
| **Keywords** | Lista con explicación y variantes | Sí |
| **Special Trait** | Lista | No |
| **Character** | Lista | No |
| **Rarity** | Lista | No |
| **Era** | Lista | No |
| **Series** | Botones, y debajo los sets de cada serie | No |
| **Color Cost** | Botones | No |
| **Combo Energy** · **Combo Power** · **Z-Energy Cost** | Botones | No |
| **Power (Back Side)** | Rango mín – máx | No |

Un apartado cerrado se abre solo si tiene algo marcado. Cuando un apartado está activo, en su cabecera aparece **«clear (N)»** para quitar todo lo que tiene marcado.

### Cómo se combinan los valores

- **Dentro de un mismo campo, por defecto es O**: con Red y Blue marcados salen las rojas *o* las azules.
- **En los campos de lista** (Color, Activate Timing, Keyword Skills, Keywords, Special Trait, Character, Era y Color Cost), al marcar dos o más valores aparece el selector **«Any (OR)» / «All (AND)»** (cualquiera / todos). Con «All (AND)» y Red + Blue salen solo las cartas que son rojas **y** azules a la vez.
- **Campos distintos siempre se combinan con Y**: Color Red **y** Type BATTLE.
- **En los rangos** (Power) puedes rellenar solo el mínimo o solo el máximo.

### Los recuentos

Cada número dice cuántas cartas saldrían **dentro de tu búsqueda actual**. Un detalle útil: cada campo se cuenta *sin su propio filtro*. Así, con «Color: Red» marcado sigues viendo cuántas hay de Blue, Green…, y puedes ampliar la selección sabiendo lo que vas a añadir. Los valores con 0 cartas salen atenuados, pero se pueden marcar igual.

### Listas largas

Si un apartado tiene más de 10 valores:
- Arriba aparece una caja **«Search N…»** para filtrar la lista.
- Solo se ven los 10 primeros y los que tengas marcados. **«Show all (N)»** despliega el resto y **«Show less»** lo recoge.

### Keyword skills y sus variantes

En **Activate Timing**, **Keyword Skills** y **Keywords**:
- Al pasar el ratón por un valor ves su **explicación oficial**, la de la página de reglas de Bandai.
- Si una habilidad es más nueva que esa página, el aviso dice «Not listed on the official keyword skills page (it's newer than its last update).»
- El icono **ⓘ** abre la página oficial de keyword skills.
- Las habilidades con número (**Over Realm X**, **Burst X**, **Limit X**…) tienen un botoncito, **«Pick specific values»**, para elegir valores concretos (Over Realm 3, 4, 5…). Esos valores se combinan siempre con O.

### Series y sets

Al marcar una serie (por ejemplo **BT**), debajo aparecen sus sets: «BT · N sets» (BT1, BT2…). Así puedes quedarte con uno o varios sets concretos. Las series sin numeración (P, XD…) no tienen esta segunda fila. Al desmarcar la serie se quitan también sus sets.

### Filtros activos y «Clear all»

- **Etiquetas sobre los resultados:** cada filtro del panel aparece como una etiqueta «Campo: valor ×». La **×** quita ese valor. Los rangos se ven como «Power: 10000 – …».
- **«Clear all»** (limpiar todo, arriba del panel) aparece cuando hay algo activo. Borra el texto, los filtros y las condiciones avanzadas. No apaga el Modo avanzado ni cambia el orden.

### En el móvil

![El buscador en el móvil](../img/movil-buscador.jpg)

En pantallas estrechas el panel está escondido: ábrelo con **☰**. Se cierra:
- con el botón **«Show N cards»** de abajo, que además te dice cuántas cartas saldrán;
- tocando fuera del panel;
- o con <kbd>Esc</kbd>.

## Ordenar

| Opción | Orden |
|---|---|
| **«Card number»** (por defecto) | Serie → número de set → número de colección (BT1-001, BT1-002… BT2-001…) |
| **«Oldest»** / **«Newest»** | Por el orden en que Bandai dio de alta cada carta |
| **«Name A-Z»** | Alfabético |
| **Energy ↑ / ↓** | Por coste |
| **Power ↑ / ↓** | Por poder |

Las cartas sin ese valor (por ejemplo, Power en una EXTRA) van siempre al final.

## Los resultados

- **Contador:** arriba de la rejilla, «**N** cards».
- **48 cartas por página.**
- **Sin resultados:** «No cards match these filters.»

Cada carta de la rejilla muestra:

- **La imagen.** Si no carga, sale el número de la carta.
- **Distintivos de construcción de mazo:**
  - **«1 COPY»**: Ultimate, máximo 1 en el mazo.
  - **SC ≤4**: máximo 4 cartas [Super Combo].
  - **DB ≤7**: máximo 7 cartas [Dragon Ball].
- **«2 sides»** en las cartas de doble cara.
- **×N** si tienes copias auténticas de esa carta.
- **BAN** o **LIMIT 1** si está en la ban list. Las Banned salen en gris. Pasa el ratón para ver desde cuándo.
- **✎** si tiene errata oficial, y **?N** si tiene N preguntas oficiales (Q&A).
- **Debajo de la imagen:**
  - nombre, número y puntos de color;
  - tipo, ⚡ Energy y ✊ Power;
  - las ubicaciones donde tienes copias.

Haz clic en una carta para abrir [su ficha](ficha-de-carta.md).

### Páginas

Abajo están **«← Previous»** y **«Next →»** (en el móvil, ‹ y ›). Se muestran siempre la primera y la última página y las dos de cada lado de la actual; los huecos se marcan con «…». Al cambiar de página, la vista sube sola al principio.

## Filtrar desde una carta

En la ficha de una carta puedes hacer clic en:
- cualquier **[habilidad entre corchetes]** del texto;
- los botones de **«This card's keyword skills»**;
- los de **«Special traits»** (rasgos).

Ese valor se **añade** a los filtros y la ficha se cierra. Es la forma más rápida de buscar «más cartas con [Barrier]» o «más Saiyan».

> [!TIP]
> El texto entre corchetes se traduce al nombre oficial: `[Over Realm 3]` filtra por la habilidad «Over Realm X».

## La dirección guarda la búsqueda

Todo lo que eliges se refleja en la dirección del navegador: texto, filtros, orden, página y modo avanzado. Si copias la dirección y la abres en otro sitio, sale la misma búsqueda. Lo explicamos en [Enlaces, direcciones y atajos](enlaces-y-navegacion.md).
