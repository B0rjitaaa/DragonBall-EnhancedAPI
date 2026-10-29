# La página «Prices»

La página **«Prices»** (precios, `/prices`) resume el dinero:
- cuánto vale tu colección y cómo evoluciona;
- qué cartas suben y bajan;
- cuáles son las más caras.

Debajo del título: «Cardmarket (Europe) checked against TCGplayer (US), every day. No fake copies or cards without sales.»

![La página «Prices»: valor de la colección con su gráfica, y debajo las que suben, las que bajan y las más caras](../img/precios.jpg)

## Los controles

- **«My collection»** / **«Whole catalogue»** (todo el catálogo): qué cartas se miran. Por defecto, solo las tuyas (con al menos una copia auténtica).
- **«7 days»** / **«30 days»** / **«90 days»**: el periodo de las subidas y bajadas. Por defecto, 30 días.

## El valor de tu colección

Con «My collection» elegido, arriba sale:
- **«Your collection is worth €X»** (tu colección vale X €);
- la variación en el periodo (**▲ / ▼ N % in N days**);
- una **gráfica** de la evolución, con la fecha de inicio, el mínimo y el máximo.

Para que la gráfica cuente cómo cambian los **precios** y no cuántas cartas has ido metiendo, se calcula con **las copias que tienes hoy** multiplicadas por el precio de cada día. Solo cuentan las copias auténticas y los precios que cuentan en el valor (con ventas o a mano).

Con menos de dos días de historial dice «The chart will appear once there are a few days of history.»

## Suben, bajan y las más caras

Tres bloques de hasta 15 cartas:

| Bloque | Qué muestra |
|---|---|
| **«Up in N days»** (suben) | Las que más han subido en porcentaje. |
| **«Down in N days»** (bajan) | Las que más han bajado. |
| **«Most valuable in your collection»** (o **«Most valuable»**) | Por precio actual. |

**Cada tarjeta muestra:**
- la imagen;
- la variación **▲ / ▼ N %**;
- el nombre, el número y la rareza;
- el precio actual y el de antes (**«was €X»**).

Al pulsarla se abre su [ficha](ficha-de-carta.md).

**Para que salga en suben o bajan**, una carta tiene que:
- tener un precio que cuente en el valor;
- valer al menos **€1**, antes o ahora, para no llenar la lista de cartas de céntimos.

## Mientras no haya historial suficiente

El historial propio empezó el **28 de octubre de 2026**. Mientras no tenga tantos días como el periodo elegido, las subidas y bajadas se calculan de otra forma. Arriba lo avisa:

> Price history started on 28 October 2026. Until there are N days of our own history, rises and falls compare today's price with its **average sale price over the last 7 / 30 days on Cardmarket**.

En ese modo:
- el periodo de 7 días compara con la media de 7 días, y los de 30 y 90 días con la de 30;
- solo entran cartas con precio de Cardmarket;
- se ignoran los saltos de más de 5 veces, que suelen ser una venta suelta y no un cambio de precio real.

Cuando el historial sea lo bastante largo, la página usará el suyo propio sin que tengas que hacer nada.
