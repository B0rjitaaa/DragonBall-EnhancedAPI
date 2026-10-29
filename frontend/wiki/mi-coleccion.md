# Mi colección

**Mi colección** (`/collection`) es el Buscador, pero solo con las cartas que tienes. Tiene la misma búsqueda, los mismos filtros, el mismo modo avanzado y la misma ficha. Además lleva todo lo necesario para gestionar tus copias: cuántas tienes, dónde están, cuáles son falsas y cuánto vale todo.

![Mi colección: totales y valor arriba, controles de ubicación y vista, y la rejilla con − / + en cada carta](img/coleccion.jpg)

## Copias, cartas y ubicaciones

Tres ideas para entender esta parte:

- **Carta**: una impresión concreta (BT20-149 normal y BT20-149 alt-art son cartas distintas).
- **Copia**: cada ejemplar físico que tienes de una carta.
- **Ubicación**: dónde está cada copia. Puede ser un **mazo**, un **archivador**, una caja de **almacén** u **otro** sitio. Siempre existe **«Sin ubicar»**, donde va lo que no tiene sitio todavía (lo escaneado sin destino, lo que sale de un mazo…). Más en [Ubicaciones](ubicaciones.md).

Cada copia es además **auténtica** o **falsa** (ver [Copias falsas](#copias-falsas)).

## La barra de resultados

Encima de las cartas:

- **«N cartas · M copias»**: cuántas cartas distintas y cuántas copias cumplen la búsqueda actual. Por defecto solo cuentan las copias auténticas.
- **«valor X €»**: lo que valen esas copias auténticas, con el precio de cada carta.
  - **«(+ Y € en cartas sin ventas)»**: lo que suman las cartas que solo tienen un anuncio de un vendedor. Va aparte y no se suma al total.
  - Al pasar el ratón se ve el desglose, incluidas las copias que no tienen precio.

  Cómo se calcula cada precio: [De dónde sale cada precio](precios.md).
- **Selector de ubicación**: «Todas las ubicaciones» o una concreta. Cada una lleva su número de copias, con las falsas incluidas.
- **«Mostrar falsas»**: cuenta y muestra también las copias falsas.
- **«Ubicaciones…»**: va a la página de [Ubicaciones](ubicaciones.md).
- **Selector de vista**:
  - **«Cuadrícula»**;
  - **«Lista»**;
  - **«Mazo»**, solo cuando la ubicación elegida es un mazo.
- **«Descargar copia»**, **«Descargar CSV»**, **«Importar CSV»** y **«Restaurar copia»**: ver [Importar, exportar y copia](importar-exportar.md).
- **«Escanear cartas»**: abre el [Escáner](escaner.md).

> [!TIP]
> El valor y los contadores siguen tus filtros. Filtra por «Rarity: Secret Rare» y verás cuántas SCR tienes y cuánto valen. Elige una ubicación y verás lo que vale esa caja.

## Ordenar

Están las mismas opciones que en el Buscador, y dos más:
- **«Más copias»**: primero las cartas de las que más copias tienes.
- **«Mi orden»**: solo con una ubicación elegida. Es el orden en que tú has colocado las cartas en esa ubicación (ver [Reordenar](#reordenar-arrastrando)). Al elegir una ubicación, el orden pasa a «Mi orden» automáticamente.

## Vista «Cuadrícula»

Cada carta muestra lo mismo que en el Buscador y además:
- **La ubicación** (o «Caja 1 ×2 · Archivador ×1» si hay copias en varias).
- **Con «Mostrar falsas»:** el distintivo «N falsas».
- **Debajo:** los botones **− ×N +**.

### Añadir y quitar con − / +

- **Con una ubicación elegida**, **+** y **−** suman o quitan en esa ubicación.
- **Con «Todas las ubicaciones»:**
  - **+** suma una copia auténtica en **«Sin ubicar»**.
  - **−** quita primero de «Sin ubicar». Si allí no hay, quita de la única otra ubicación donde esté la carta.
  - Si la carta está en **varias ubicaciones**, no adivina de cuál quitar: abre la ficha con el aviso «Esta carta está en varias ubicaciones: quita la copia desde la que quieras.»
- **Sin «Mostrar falsas»**, **−** solo quita auténticas. Con «Mostrar falsas», quita primero auténticas y después falsas.

Una carta que llega a 0 copias desaparece de la lista en el momento.

### Reordenar arrastrando

Con una ubicación elegida y el orden **«Mi orden»**, puedes **arrastrar las cartas** para colocarlas como las tienes de verdad (útil en un archivador). El aviso lo recuerda: «Arrastra las cartas para ordenarlas (en el móvil, mantén pulsada una carta). El orden se guarda.»

- **En el ordenador:** pincha y arrastra.
- **En el móvil:** mantén pulsada la carta un momento y arrastra.
- **Las cartas nuevas** de una ubicación van al final.
- **Solo se reordenan las cartas que estás viendo.** Las de otras páginas o las que tienes filtradas mantienen su sitio.

![Mi colección dentro de una ubicación, ordenada a mano](img/coleccion-ubicacion.jpg)

## Vista «Lista»: mover copias

La lista sirve sobre todo para **mover copias entre ubicaciones**, una a una o muchas de golpe.

![Vista Lista con casillas de selección y el control de mover en cada fila](img/coleccion-lista.jpg)

**Cada fila tiene:**
- la casilla de selección;
- la miniatura (al pulsarla se abre la ficha);
- el total **×N**;
- una etiqueta por ubicación con su cantidad. Las falsas llevan «falsa», y la nota se ve al pasar el ratón.
- el control de mover: **[n] de [origen] a [destino…] → Mover**.

El origen que se propone es la ubicación elegida, o si no la que más copias tiene. Las falsas aparecen como «Caja 1 (falsas)» y siguen siendo falsas al moverlas.

**Mover muchas a la vez:**
1. Marca las cartas, o usa **«Seleccionar todas»** para las de la página.
2. Arriba aparece **«Mover [todas sus copias | 1 copia] de [origen] a [elige destino…] → Mover N»**.
3. Si alguna de las seleccionadas no tiene copias en el origen, el aviso del botón lo dice.
4. **«Quitar selección»** desmarca todo.

> [!NOTE]
> **Las notas al mover:**
> - Si mueves **todas** las copias de una fila, la nota viaja con ellas.
> - Si mueves solo **algunas**, la nota se queda en el origen.
> - Desde la ficha puedes elegir **qué línea** de la nota se lleva la copia, por ejemplo la posición en el archivador.

## Vista «Mazo»

Cuando eliges un mazo, la vista pasa a **«Mazo»**: Leader, Main Deck, Z Deck y Side Deck, con sus reglas, estadísticas, versiones y partidas. Lo explicamos en [Mazos](mazos.md).

## Copias falsas

Las proxies o falsificaciones que tengas puedes apuntarlas como **falsas**, sin mezclarlas con las auténticas:

- **Cómo se marcan:** se marcan a mano desde la ficha, con **«Marcar falsa»** en la fila de la ubicación. **«Es auténtica»** hace lo contrario. Cada clic cambia **una** copia.
- **Cómo se guardan:** cada carta tiene en cada ubicación una fila de auténticas y otra de falsas, con su propia nota (p. ej. «AliExpress, junio»).
- **Cómo entran las nuevas:** las copias nuevas (+, escáner, importación sin columna `falsa`) entran siempre como auténticas.
- **Por defecto no cuentan en nada:** ni en los contadores, ni en los filtros, ni en el valor. Para verlas marca **«Mostrar falsas»**.
- **El valor de la colección nunca las incluye**, aunque estén a la vista.

> [!IMPORTANT]
> Una falsa en un mazo sigue contando en la **lista del mazo**, porque físicamente está ahí. Lo que no hace es sumar en el valor.

## Añadir cartas desde el Buscador

No hace falta ir a Mi colección para añadir una carta. En la ficha de cualquier carta del Buscador tienes el panel de tus copias con **«Añadir a Mi colección en [ubicación] → Añadir»**. Ver [La ficha de una carta](ficha-de-carta.md#tus-copias). En la rejilla del Buscador, las cartas que tienes llevan **×N**.

## Colección vacía

Si todavía no tienes nada, la página dice «Tu colección está vacía: escanea cartas con el escáner y aparecerán aquí.» Hay tres formas de llenarla:
- el [Escáner](escaner.md);
- **Añadir** desde la ficha de una carta;
- [importar un CSV](importar-exportar.md).
