# La ficha de una carta

Al hacer clic en una carta (en «Search», «My collection», «News» o «Prices») se abre su **ficha**: la imagen grande y todo lo que se sabe de ella.

![Ficha de BT20-149: imagen, impresiones del mismo número, precio, reglas de construcción, texto y atributos](../img/ficha-carta.jpg)

**Para cerrarla:** pulsa **✕**, haz clic fuera de la ficha o pulsa <kbd>Esc</kbd>.

## Columna izquierda

### La imagen y sus caras

Las cartas de **dos caras** (Leaders y algunas otras) tienen dos botones: **«Front»** (cara frontal) y **«Back»** (cara trasera). Al cambiar de cara cambian la imagen, el nombre, el texto y la tabla de atributos.

![Un Leader: botones «Front» / «Back»](../img/ficha-leader.jpg)

### Impresiones del mismo número

Si un número tiene varias impresiones (normal, alt-art, SPR, promos de torneo…), debajo de la imagen aparece **«Printings of BT20-149»** con una miniatura de cada una y su rareza. La que estás viendo sale resaltada; pulsa otra para abrirla. Al pasar el ratón se ve su enlace, rareza y set.

### Evolución del precio

Si la carta tiene un precio que cuenta en el valor (con ventas), debajo sale la gráfica **«Price history»** (evolución del precio):

- **Periodos:** **«30 days»**, **«90 days»** (por defecto) y **«All»**.
- **Arriba a la derecha:** cuánto ha cambiado en ese periodo (**▲ 12%**, **▼ 5%** o **=** si se ha movido menos de un 0,5 %).
- **Tooltip:** al pasar el ratón por la gráfica se ve el precio de cada día.

El historial empezó el **28 de octubre de 2026**. Mientras haya un solo dato, en lugar de la gráfica dice «History started on 28 Oct: the chart will fill in over the coming days.»

## Columna derecha

### Número, set y enlace

Arriba: **número · nombre del set** y el botón **«🔗 Copy link»**. El botón copia la dirección de esta carta; al pegarla en otro sitio se abre esta ficha directamente. Mientras está copiado dice «Link copied ✓». Si el navegador no deja copiar, aparece el enlace seleccionado para que lo copies tú. Ver [Enlaces, direcciones y atajos](enlaces-y-navegacion.md#enlace-a-una-carta).

### El precio

![Recuadro de precio con sus fuentes y enlaces](../img/precio-ficha.jpg)

**La cifra grande:**
- **«€51.74»**: precio de mercado.
- **«from €11.60»**: solo hay un anuncio de un vendedor, sin ventas reales.

**Debajo, de dónde sale:**
- **«market price · Cardmarket»** o **«· TCGplayer»**: sale de ventas reales.
- **«price set by hand»**: lo pusiste tú en la [revisión de precios](revisar-precios.md).
- **«only a seller's asking price: no sales (not counted in the value)»**: solo lo que pide un vendedor, sin ventas.
- **«doubtful price: a single listing, no sales (not counted in the value)»**: un anuncio desproporcionado para su rareza, pendiente de revisar.

**Línea de fuentes:** «Cardmarket €51.74 · TCGplayer €46.56 (US) · from €50.00 in Europe». Así ves de un vistazo si las fuentes coinciden.

**Variación:** «7 days: ▲ 3%», «30 days: ▼ 8%».

**Enlaces:**
- **«Offers in Spain ↗»**: Cardmarket, solo vendedores de España y cartas en inglés.
- **«Offers in Europe ↗»**: Cardmarket, toda Europa y cartas en inglés.
- **TCGplayer ↗**: si la carta está emparejada con TCGplayer.

Si la carta no tiene producto en Cardmarket, los enlaces llevan a una búsqueda por su nombre.

Cómo se elige cada precio, con todas sus reglas, está en [De dónde sale cada precio](precios.md).

### Avisos de torneo

- **«⛔ Banned in official tournaments»**: no puede ir ni en el mazo ni en el side deck.
- **«⚠️ Limited: 1 copy max»**: máximo 1 copia entre mazo y side deck.

Los dos llevan debajo la fecha desde la que se aplican.

**«🃏 Deck building»** resume las reglas especiales de la carta:
- «Ultimate: 1 copy max».
- «Super Combo: 4 max in the deck».
- «Dragon Ball: 7 max in total».

### Errata oficial

Si Bandai ha publicado una errata, aparece **«✎ Official erratum»** con su fecha, dos columnas **«Before»** / **«After»** y las notas de la errata.

### Tus copias

Debajo de los avisos está el panel de **tus copias** de esa carta. Dice «Not in your collection» o «In your collection: ×3», más «1 fake» si tienes alguna falsa.

![Panel de copias en la ficha, dentro de «My collection»](../img/coleccion-ficha.jpg)

**Una fila por ubicación**, con su tipo («Deck», «Binder», «Storage»). Las copias falsas van en su propia fila, marcada **«Fake»**. En cada fila:
- **− / +**: quita o añade una copia en esa ubicación. Las filas de falsas no tienen **+**.
- **«Mark as fake»** / **«It's genuine»**: cambia **una** copia de auténtica a falsa o al revés. Si en esa fila hay varias copias y la nota tiene posiciones (por ejemplo, del archivador), pregunta **«Which one is the fake?»** y ofrece cada posición.
- **«Move…»**: mueve copias a otra ubicación: «Move [n] to [ubicación] → Move».
- **«Note»**: texto libre de hasta 500 caracteres. Se guarda al salir del campo. Ejemplos: «página 12» o, para una falsa, «AliExpress, junio».

**«Add to My collection in» [ubicación] → «Add»** suma una copia auténtica en una ubicación donde todavía no tienes esa carta. Te propone la última ubicación que usaste en este navegador, o «Unsorted» (sin ubicar).

> [!NOTE]
> Este panel solo aparece cuando la carta está en la página de resultados que tienes abierta. Si la abres desde un enlace o desde la fila de impresiones y no está en esa página, no sale. Búscala y ábrela desde los resultados.

Todo sobre copias, ubicaciones y falsas está en [Mi colección](mi-coleccion.md).

### Texto de la carta

- **Habilidades:** las palabras entre corchetes (**[Barrier]**, **[Activate : Main]**…) son botones. Al pasar el ratón muestran su explicación oficial; al hacer clic filtran el buscador por esa habilidad.
- **Atributos:** debajo del texto está la tabla con todo lo que Bandai da de la carta: Era, Type, Color, Power, Energy, Rarity, Character, Special Trait, Color Cost, Combo Power, Combo Energy…

### Keyword skills y rasgos

- **«This card's keyword skills»:** cada habilidad con su categoría (Activate Timing, Keyword Skills o Keywords) y su explicación oficial. Hacer clic filtra por ella.
- **«Special traits» (rasgos):** los Special Traits de la carta (Saiyan, Android…). También filtran al pulsarlos.

### Preguntas y respuestas (Q&A)

Si la web oficial tiene preguntas sobre la carta, aparece **«Q&A N»** (preguntas y respuestas), plegado. Ábrelo para leerlas (Q1, Q2…). Las que Bandai marca como recientes llevan la etiqueta **«new»**.

### Notas

Al final, las notas de Bandai sobre la carta, si las hay.
