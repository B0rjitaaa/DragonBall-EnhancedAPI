# De dónde sale cada precio

Cada carta del catálogo tiene, si se puede, un **precio en euros**. Sale de cruzar **Cardmarket** (el mercado europeo) con **TCGplayer** (el de EE. UU.), más los precios que pongas tú a mano. Este artículo cuenta las reglas, paso a paso, para que sepas cuándo fiarte de un precio y cuándo no.

![El precio en la ficha de una carta: cifra, fuente, comparativa y enlaces](img/precio-ficha.jpg)

## Las fuentes

### Cardmarket

Cardmarket publica cada día un **catálogo** y una **guía de precios** pública de todos sus productos de Dragon Ball Super. De cada producto da:
- la **tendencia** (trend);
- las **medias de venta** de 1, 7 y 30 días;
- el **anuncio más barato** (low).

Son datos **de toda Europa** y mezclan idiomas.

### TCGplayer

TCGplayer es el mercado de Estados Unidos. Sus datos llegan a través de **tcgcsv.com**, que publica un volcado diario. Se usa su **precio de mercado**, que sale de ventas reales, convertido de dólares a euros con el **cambio oficial del BCE** de cada día.

### A mano

En la [revisión de precios](revisar-precios.md) del admin puedes poner el precio de una carta a mano. **Un precio a mano siempre manda.**

## El precio de referencia de Cardmarket

Los datos de Cardmarket a veces tienen picos raros (un trend inflado por una venta aislada, una media disparada…). Para no fiarse de un solo dato, se toma **el menor** de estos tres:

1. la **tendencia** (trend);
2. la **mediana** de las medias de 1, 7 y 30 días;
3. **3 veces el anuncio más barato**.

**Si no hay ventas** (un set recién salido, una carta rarísima), solo queda el anuncio más barato. Se usa, pero marcado como **«sin ventas»**: es lo que *pide* un vendedor, no lo que se paga.

## Cómo se combinan

| Situación | Precio que se usa | ¿Cuenta en el valor? |
|---|---|---|
| Hay un precio **a mano** | Ese | Sí |
| Cardmarket **con ventas** | Cardmarket… | Sí |
| …pero TCGplayer es **menos de la mitad** | TCGplayer (corrige precios inflados en Europa) | Sí |
| Cardmarket **sin ventas** y hay TCGplayer | El **menor** de los dos (si el anuncio no es sospechoso) | Sí |
| **Solo** un anuncio en Cardmarket | Ese anuncio, como «desde X €» | **No** |
| Nada | Sin precio | — |

En la ficha, la línea de fuentes («Cardmarket X € · TCGplayer Y € (EE. UU.) · desde Z € en Europa») te deja ver si coinciden.

## Cartas «sin ventas»

Una carta que solo tiene un anuncio en Cardmarket y nada más sale como **«desde X €»**, con el texto «solo lo que pide un vendedor: sin ventas (no cuenta en el valor)». Su importe **no se suma** al valor de tu colección. Se muestra aparte, como «(+ Y € en cartas sin ventas)», para que lo tengas en cuenta sin inflar el total.

## Precios sospechosos

Un anuncio sin ventas puede ser absurdo: alguien pide 9.999 € por una carta de 2 €. Un anuncio se considera **sospechoso** cuando:
- es el único dato (sin ventas en ninguna fuente);
- y está **por encima del percentil 99** de las cartas de su misma rareza que sí tienen ventas. Hace falta que haya al menos 20 cartas de esa rareza para comparar.

Los sospechosos **no cuentan en nada**, ni siquiera en el «aparte», hasta que alguien los revisa. En la ficha salen como «precio dudoso: un solo anuncio, sin ventas».

## Emparejar cada carta con su producto

La parte delicada es saber **qué producto de Cardmarket es cada carta**, porque Cardmarket no da el número de la carta ni su rareza: solo la expansión y el nombre. El emparejamiento automático:

- **Expansiones:** empareja cada set con su expansión de Cardmarket y deja fuera Fusion World.
- **Nombres:** compara los nombres, aprovechando las pistas que Cardmarket mete en ellos (número, set, color) y la forma «frente // reverso» de los Leaders.
- **Varias impresiones con el mismo nombre en un set** (normal y alt-art): las ordena por rareza y precio.
- **Reimpresiones** (la misma carta en un Starter Deck o en otro set): copian el precio de la impresión **original**, nunca al revés, y solo si no son promos.
- **Promos:** no copian el precio de la versión normal, porque una promo de torneo puede valer diez veces más. Cada promo busca su propio producto; si hay dudas, se queda **sin emparejar** para que la revises tú.
- **Impresiones creadas a mano desde TCGplayer:** apuntan directamente a su producto exacto.

Lo que no se puede decidir con seguridad va a la [revisión de precios](revisar-precios.md). **Tus elecciones se recuerdan** y mandan en todas las actualizaciones siguientes.

## Copias falsas

Las copias marcadas como [falsas](mi-coleccion.md#copias-falsas) **nunca cuentan** en ningún valor.

## Cuándo se actualiza

Todo se recalcula **cada día a las 05:15** (hora de Madrid). Cardmarket publica su guía hacia las 03:00. En cada actualización:
1. se descarga el catálogo y la guía de Cardmarket;
2. se rehacen los emparejamientos, respetando los tuyos;
3. se descarga el cambio del dólar;
4. se descarga TCGplayer (solo si tcgcsv tiene datos nuevos);
5. se recalcula el precio de cada carta y se apunta en el historial;
6. se rehace el **volcado** `data/precios_dbs.json`.

## El volcado de precios

Para que una **instalación nueva** arranque ya con precios, el repositorio trae un volcado de todo lo de esta página en `data/seed/precios_dbs.json.gz` (~1 MB), y el servidor rehace otro cada día en `data/precios_dbs.json`. Incluyen:
- los productos y emparejamientos de Cardmarket y TCGplayer;
- **tus elecciones y precios a mano** de la revisión;
- el cambio del dólar;
- el precio de cada carta y su historial.

Al arrancar con la base sin precios, se importa solo el más reciente. Ver [Instalación paso a paso](instalacion.md#los-datos-que-trae-el-repositorio).

| Comando | Qué hace |
|---|---|
| `make export-prices` | Rehace el volcado ahora |
| `make import-prices` | Carga el volcado **sustituyendo** los precios actuales |
| `make seed` | Pone al día los volcados del repositorio (`data/seed/`) |

Si no hay volcado, el worker descarga los precios en cuanto hay catálogo.

## El historial

- **Qué se guarda:** solo los precios que **cuentan en el valor**, y solo los días en que cambian.
- **Desde cuándo:** empezó el **28 de octubre de 2026**. No hay datos anteriores: el archivo histórico público de tcgcsv dejó de estar disponible.
- **Para qué se usa:**
  - la gráfica de la ficha;
  - la variación a 7 y 30 días;
  - la página [Precios](pagina-precios.md).
