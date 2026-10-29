# Modo avanzado

El panel de filtros cubre casi todo, pero tiene dos límites: los **campos distintos siempre se combinan con Y**, y no se puede **negar** nada. El **Modo avanzado** quita esos límites. Con él montas la búsqueda como un árbol de condiciones unidas por **Y**, **O** y **NO**, todo lo anidado que necesites.

![Modo avanzado: «Leaders rojos» O «cartas con Counter : Play que cuestan 2 o menos»](img/modo-avanzado.jpg)

## Activarlo

Pulsa **«Modo avanzado OFF»** en la cabecera para que pase a **ON**. Encima de los resultados aparece el panel **«Búsqueda avanzada»**, con el recordatorio «Se combina (Y) con los filtros del panel lateral».

- **Al apagarlo** (OFF), el árbol **se conserva** pero deja de aplicarse. Al volver a ON sigue ahí.
- **Se combina con todo lo demás**: los resultados cumplen a la vez el texto libre, el panel lateral y el árbol avanzado.

## Grupos y condiciones

El árbol empieza con un **grupo raíz**. Mientras está vacío dice «Añade condiciones para refinar la búsqueda. Puedes anidar grupos Y / O.».

**Botones de cada grupo:**

| Botón | Qué hace |
|---|---|
| **NO** | Niega el grupo entero: salen las cartas que *no* lo cumplen. |
| **Y (todas)** / **O (alguna)** | Si deben cumplirse todas las condiciones del grupo o basta con una. |
| **+ Condición** | Añade una condición al grupo. |
| **+ Grupo** | Añade un subgrupo dentro. Empieza con el operador contrario al del grupo padre, que es lo que se suele querer. |
| **✕** | Borra el grupo (el raíz no se puede borrar). |

Entre los hijos de un grupo se ve el conector **Y** u **O**, para leer la búsqueda de un vistazo.

**Partes de cada condición**, de izquierda a derecha:
- **NO** para negarla;
- el **campo**;
- el **operador**;
- el **valor**;
- **✕** para borrarla.

Una condición nueva empieza con «Keyword (Exact Value)» «incluye».

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
| **Texto** (Card Name, Card Text, Card Number) | **contiene** · **es** (igual, sin distinguir mayúsculas) · **empieza por** |
| **Número** (Energy, Power…) | **es** · **≠** · **<** · **≤** · **>** · **≥** · **entre** (mín y máx) · **sin valor** |
| **Uno entre varios** (Type, Rarity, Series…) | **es** · **es uno de** |
| **Lista** (Color, Special Trait, Keyword Skills…) | **incluye** · **incluye alguno de** · **incluye todos** · **está vacío** |
| **Sí / No** (Has Errata, Double-Sided…) | **es** |

> [!WARNING]
> - **≠ en números** también deja fuera las cartas *sin* ese valor. «Power ≠ 10000» no devuelve las EXTRA, que no tienen Power. Si las quieres, usa **sin valor** en otra condición con O.
> - **«es» en los campos de tipo «uno entre varios»** distingue mayúsculas: `LEADER`, no `leader`. Elige el valor de las sugerencias para no equivocarte.

## Escribir los valores

- **Sugerencias**: al escribir aparecen los valores que existen, con «N cartas» al lado.
- **Varios valores** (es uno de / incluye alguno de / incluye todos): cada valor es una etiqueta.
  - <kbd>Enter</kbd> añade lo que has escrito.
  - Elegir una sugerencia la añade directamente.
  - <kbd>⌫</kbd> con la caja vacía borra la última etiqueta.
- **entre**: dos cajas, **mín** y **máx**.
- **sin valor**, **está vacío** y los campos Sí/No: un selector Sí / No.

## Ejemplos

**Leaders rojos, o cartas con [Counter : Play] de coste 2 o menos** (la captura de arriba):

```
O (alguna)
├── Y (todas)
│   ├── Type es LEADER
│   └── Color incluye Red
└── Y (todas)
    ├── Keyword Skills incluye Counter : Play
    └── Energy ≤ 2
```

**Saiyan azules que NO son Ultimate:**

```
Y (todas)
├── Special Trait incluye Saiyan
├── Color incluye Blue
└── NO  Keyword Skills incluye Ultimate
```

**Cartas que dan Barrier a otras pero no lo tienen ellas:**

```
Y (todas)
├── Mentioned Keyword incluye Barrier
└── NO  Keyword Skills incluye Barrier
```

**Extras baratas de cualquier set de Zenkai (BT14 en adelante):**

```
Y (todas)
├── Type es EXTRA
├── Energy ≤ 1
└── Set Code es uno de BT14, BT15, BT16, …
```

## Límites

- **Anidación:** 6 niveles como máximo.
- **Condiciones:** 60 en total.
- **Valores:** 100 por condición.

Si te pasas, se muestra un error en rojo junto al contador de resultados.

## Guardar y compartir

El árbol se guarda en la dirección (`?advanced=…`), así que **una búsqueda avanzada se puede guardar en favoritos o compartir** como cualquier otra. Si el árbol existe pero el modo está en OFF, la dirección lleva además `advanced_on=0`. Más en [Enlaces, direcciones y atajos](enlaces-y-navegacion.md).
