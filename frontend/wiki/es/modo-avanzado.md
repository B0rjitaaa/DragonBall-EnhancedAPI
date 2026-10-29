# Modo avanzado

El panel de filtros cubre casi todo, pero tiene dos límites: los **campos distintos siempre se combinan con Y**, y no se puede **negar** nada. El **Modo avanzado** quita esos límites. Con él montas la búsqueda como un árbol de condiciones unidas por **«AND»** (Y), **«OR»** (O) y **«NOT»** (NO), todo lo anidado que necesites.

![Modo avanzado: «Leaders rojos» O «cartas con Counter : Play que cuestan 2 o menos»](../img/modo-avanzado.jpg)

## Activarlo

Pulsa **«Advanced mode OFF»** en la cabecera para que pase a **ON**. Encima de los resultados aparece el panel **«Advanced search»** (búsqueda avanzada), con el recordatorio «Combined (AND) with the sidebar filters».

- **Al apagarlo** (OFF), el árbol **se conserva** pero deja de aplicarse. Al volver a ON sigue ahí.
- **Se combina con todo lo demás**: los resultados cumplen a la vez el texto libre, el panel lateral y el árbol avanzado.

## Grupos y condiciones

El árbol empieza con un **grupo raíz**. Mientras está vacío dice «Add conditions to refine the search. You can nest AND / OR groups.».

**Botones de cada grupo:**

| Botón | Qué hace |
|---|---|
| **«NOT»** | Niega el grupo entero: salen las cartas que *no* lo cumplen. |
| **«AND (all)»** / **«OR (any)»** | Si deben cumplirse todas las condiciones del grupo o basta con una. |
| **«+ Condition»** | Añade una condición al grupo. |
| **«+ Group»** | Añade un subgrupo dentro. Empieza con el operador contrario al del grupo padre, que es lo que se suele querer. |
| **✕** | Borra el grupo (el raíz no se puede borrar). |

Entre los hijos de un grupo se ve el conector **«AND»** u **«OR»**, para leer la búsqueda de un vistazo.

**Partes de cada condición**, de izquierda a derecha:
- **«NOT»** para negarla;
- el **campo**;
- el **operador**;
- el **valor**;
- **✕** para borrarla.

Una condición nueva empieza con «Keyword (Exact Value)» «includes».

> [!NOTE]
> Las condiciones a medias (sin valor) y los grupos vacíos **se ignoran**: no filtran nada. Así puedes ir montando el árbol sin que los resultados se queden a cero a cada paso.

## Los campos

En el selector, los campos están agrupados:

| Grupo | Campos |
|---|---|
| **Text** | **Card Name**: busca en el nombre de las dos caras · **Card Text**: texto de las dos caras, sin corchetes ni mayúsculas · **Card Number** |
| **Set** | **Series** · **Set Code** · **Card Set** (nombre completo de la expansión) · **Regulation** |
| **Tournament** | **Banned / Limited** · **Has Errata** · **Has Q&A** |
| **Attributes** | **Type** · **Color** · **Rarity** · **Energy** · **Color Cost** · **Combo Energy** · **Combo Power** · **Power** · **Power (Back Side)** · **Z-Energy Cost** · **Character** · **Special Trait** · **Era** · **Double-Sided** |
| **Skills** | **Activate Timing** · **Keyword Skills** · **Keywords** · **Keyword (Exact Value)** · **Mentioned Keyword** · **Keyword Family** |

Algunos campos **solo existen aquí**, no en el panel:
- **Card Set** y **Regulation**;
- **Double-Sided**;
- **Keyword (Exact Value)**: la habilidad tal cual aparece en la carta, con su número. Por ejemplo `Over Realm 4`.
- **Mentioned Keyword**: palabras entre corchetes que la carta **menciona** pero no tiene. Por ejemplo, una carta que dice «…it gains [Barrier]» *menciona* Barrier.
- **Keyword Family**: la habilidad sin su número (`Limit 1` → `Limit`; `Counter : Play` → `Counter`).
- **Card Name**, **Card Text** y **Card Number** por separado. La caja de búsqueda busca en los tres a la vez.

## Los operadores

Cada tipo de campo tiene sus operadores:

| Tipo de campo | Operadores |
|---|---|
| **Texto** (Card Name, Card Text, Card Number) | **«contains»** · **«is»** (igual, sin distinguir mayúsculas) · **«starts with»** |
| **Número** (Energy, Power…) | **«is»** · **≠** · **<** · **≤** · **>** · **≥** · **«between»** (mín y máx) · **«has no value»** |
| **Uno entre varios** (Type, Rarity, Series…) | **«is»** · **«is one of»** |
| **Lista** (Color, Special Trait, Keyword Skills…) | **«includes»** · **«includes any of»** · **«includes all»** · **«is empty»** |
| **Sí / No** (Has Errata, Double-Sided…) | **«is»** |

> [!WARNING]
> - **≠ en números** también deja fuera las cartas *sin* ese valor. «Power ≠ 10000» no devuelve las EXTRA, que no tienen Power. Si las quieres, usa **«has no value»** en otra condición con «OR».
> - **«is» en los campos de tipo «uno entre varios»** distingue mayúsculas: `LEADER`, no `leader`. Elige el valor de las sugerencias para no equivocarte.

## Escribir los valores

- **Sugerencias**: al escribir aparecen los valores que existen, con «N cards» al lado.
- **Varios valores** («is one of» / «includes any of» / «includes all»): cada valor es una etiqueta.
  - <kbd>Enter</kbd> añade lo que has escrito.
  - Elegir una sugerencia la añade directamente.
  - <kbd>⌫</kbd> con la caja vacía borra la última etiqueta.
- **«between»**: dos cajas, **«min»** y **«max»**.
- **«has no value»**, **«is empty»** y los campos Sí/No: un selector «Yes» / «No».

## Ejemplos

**Leaders rojos, o cartas con [Counter : Play] de coste 2 o menos** (la captura de arriba):

```
OR (any)
├── AND (all)
│   ├── Type is LEADER
│   └── Color includes Red
└── AND (all)
    ├── Keyword Skills includes Counter : Play
    └── Energy ≤ 2
```

**Saiyan azules que NO son Ultimate:**

```
AND (all)
├── Special Trait includes Saiyan
├── Color includes Blue
└── NOT  Keyword Skills includes Ultimate
```

**Cartas que dan Barrier a otras pero no lo tienen ellas:**

```
AND (all)
├── Mentioned Keyword includes Barrier
└── NOT  Keyword Skills includes Barrier
```

**Extras baratas de cualquier set de Zenkai (BT14 en adelante):**

```
AND (all)
├── Type is EXTRA
├── Energy ≤ 1
└── Set Code is one of BT14, BT15, BT16, …
```

## Límites

- **Anidación:** 6 niveles como máximo.
- **Condiciones:** 60 en total.
- **Valores:** 100 por condición.

Si te pasas, se muestra un error en rojo junto al contador de resultados.

## Guardar y compartir

El árbol se guarda en la dirección (`?advanced=…`), así que **una búsqueda avanzada se puede guardar en favoritos o compartir** como cualquier otra. Si el árbol existe pero el modo está en OFF, la dirección lleva además `advanced_on=0`. Más en [Enlaces, direcciones y atajos](enlaces-y-navegacion.md).
