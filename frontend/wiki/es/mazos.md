# Mazos

Un **mazo** es una [ubicación](ubicaciones.md) de tipo «Deck». Al abrirlo (`/collection/deck/<id>`, o eligiéndolo en «My collection») se ve en la vista **«Deck»**:
- el Leader;
- el Main Deck, el Z Deck y el Side Deck;
- la comprobación de las reglas de construcción;
- estadísticas;
- las **versiones** de la lista;
- las **partidas** jugadas.

![Vista Mazo: Leader, contadores, avisos de construcción, estadísticas, partidas y la lista por secciones](../img/mazo.jpg)

## Caja, lista principal y versiones

Estas tres ideas son la clave para entender los mazos:

- **La caja** es lo que hay físicamente en esa ubicación: las copias que la web tiene apuntadas en el mazo.
- **Las versiones** (v1, v2, v3…) son listas guardadas. Cada vez que cambias el mazo y guardas, se crea una versión nueva, así queda el historial de cómo ha evolucionado.
- **La lista principal** (★) es la versión que está, o debería estar, en la caja. Las partidas se anotan contra ella.

Cuando la caja y la principal coinciden, todo cuadra. Si mueves copias por fuera (desde «My collection» o el escáner), la web te avisa de que **«the box has changed»** (la caja ha cambiado).

## La cabecera del mazo

### El Leader

- **Ver la otra cara:** pulsa el Leader para alternar **Front** ⟲ **Awaken**. Por defecto se ve la cara Awaken.
- **«número · details»** abre su ficha.
- **«Remove»** lo quita de la lista. Para poner otro, usa «Add card».

### Contadores

- **«N/60 Main Deck»**: en verde cuando estás entre 50 y 60.
- **«N Z Deck»**.
- **«X.X Av. Energy»**: el coste medio del Main Deck.
- **«N side»**: si hay side deck.

### Reglas de construcción

Si todo está bien se lee **«✓ Meets the deck-building rules»**. Si no, **«⚠ N deck-building warnings»**, que se despliega:

| Aviso | Regla |
|---|---|
| The Leader card is missing | Todo mazo necesita un Leader. |
| N cards short of 50 | Mínimo 50 cartas en el Main Deck. |
| N cards too many (max 60) | Máximo 60 cartas en el Main Deck. |
| BT1-030 Nombre: N copies (max 4) | Máximo 4 copias de un **mismo número**, sumando todas sus impresiones (normal + alt-art…) en Main y Z Deck. |
| … is Banned | No se puede jugar. |
| … is Limited: 1 copy max | Solo 1 copia. |
| Ultimate: 1 copy max | Las cartas con [Ultimate]. |
| Super Combo: 4 max in the deck | Máximo 4 cartas [Super Combo]. |
| Dragon Ball: 7 max in total | Máximo 7 cartas [Dragon Ball]. |
| There are N Leader cards in the deck | Es una advertencia, no un error. |

Cada carta con problemas lleva una marca con el motivo.

> [!NOTE]
> Las reglas se comprueban sobre el **Main Deck** (y el Z Deck para las 4 copias). El **side deck no se comprueba**.

### Estadísticas

- **«Energy curve»:** barras de coste de 0 a 10+.
- **«Types»:** Battle, Extra, Unison.
- **Colors:** reparto de colores.

**Pulsa cualquier barra o color para filtrar la lista**: por ejemplo, ver solo las cartas de coste 2. Cada sección dice entonces «X of Y cards». **«✕ Clear filters»** vuelve a mostrarlo todo.

## Las secciones de la lista

- **«Main Deck»** (mazo principal).
- **Z Deck**: las cartas cuyo tipo empieza por «Z-» (Z-BATTLE, Z-EXTRA…).
- **Side deck**.

Las copias falsas que hay en la caja también cuentan en la lista, porque físicamente están en el mazo.

## Preparar cambios (el borrador)

Con la pestaña **«Main»** (principal) seleccionada puedes preparar una lista nueva **sin mover nada todavía**:

- **− / +** en cada carta cambia sus copias (de 0 a 99).
- **→ Side** pasa una copia al side deck; **«↩ Deck»** la devuelve.
- **«+ Add card»** (al final del Main Deck) abre un buscador de todo el catálogo. Escribe al menos 2 letras del nombre, número o texto y pulsa una carta para sumar una copia; puedes pulsar varias veces. **«Done»** cierra el buscador.
- **Cada cambio** se ve sobre la carta como **+N** o **−N**: «Unsaved change compared with what's in the box».

El borrador se guarda en tu navegador: si recargas la página, no se pierde. **«Discard»** lo tira.

> [!TIP]
> El borrador no toca tu colección. Sirve para probar ideas («¿y si quito 2 de esta y pongo 2 de aquella?») y ver al momento cómo quedan la curva y los avisos de reglas.

### Ordenar las cartas

Sin cambios pendientes y sin filtros, puedes **arrastrar las cartas** dentro de su sección para ordenarlas a tu gusto. En el móvil, mantén pulsada la carta antes de arrastrar.

## Guardar la lista

**«Save list»** abre «Save list vN», con dos campos opcionales: **«Name»** (p. ej. «More removal») y **«Notes»**.

- **Si las cartas ya están en la caja:** «✓ These cards are already in the deck box: the list will become the main one.»
- **Si no:** te enseña qué copias habría que mover y te deja elegir entre dos botones:
  - **«Just save»**: guarda la versión sin tocar la caja;
  - **«Save and make main (N copies)»**: guarda y además mueve las copias.

Una versión que coincide exactamente con la caja (side incluido) pasa a ser la principal automáticamente.

## Hacer principal una versión (mover copias)

Al elegir una versión en la barra de listas aparecen sus datos y sus botones:
- **«vN · saved …»**, con las etiquetas **«★ main»** y **«automatic»**;
- **«Changes since vN»**: qué cambió respecto a la anterior;
- **«Make main»** (hacer principal), o **«Rearrange the box»** si ya es la principal pero la caja ha cambiado;
- **«Rename»** y **«Delete»**. Solo se puede borrar una versión sin partidas, y borrarla no mueve cartas.

**«Make main»** mueve **de verdad** copias de tu colección para que la caja quede igual que esa versión. Antes de hacerlo te enseña el plan:

- **«Leaving the box N copies»**:
  - van a **«Move them to»**, que por defecto es «Unsorted»;
  - puedes elegir otro destino para cada carta;
  - salen primero las falsas.
- **«Entering the box N copies»**:
  - de cada carta se ve de dónde se coge (por ejemplo «From: Unsorted 2 + Caja 3 1»). Va primero a «Unsorted», luego a archivadores y cajas, y como último recurso a otros mazos;
  - puedes forzar el origen de cada carta.
- **Avisos posibles:**
  - **«⚠ Copies will be taken from other decks»**;
  - **«⚠ N copies missing»**, si no tienes suficientes. La caja quedará incompleta hasta que las consigas;
  - **«⚠ What's in the box right now isn't saved as a list»**. Guárdalo antes si quieres poder volver a ello.

Pulsa **«Move N copies and make main»**. Al terminar se resume cuántas salieron y entraron.

> [!IMPORTANT]
> La web mueve las copias **en tu colección**. Haz el mismo movimiento con las cartas de verdad para que todo siga cuadrando.

## Partidas

El panel **«Matches»** (partidas) guarda tus resultados con el mazo.

- **«+ Result»** abre el formulario **«Log result»**:

  | Campo | Detalle |
  |---|---|
  | **Opponent Leader** | Busca el Leader rival por nombre o número. Te ofrece los 6 últimos que has anotado. Si no está en el catálogo, **«Use “texto” without a card»**. |
  | **«Result»** | **«Win»**, **«Loss»** o **«Draw»**. |
  | **«Date»** | Hoy por defecto. No admite fechas futuras. |
  | **«Opponent»** | Nombre del rival, con autocompletado. |
  | **«Who went first?»** | **«Me»**, **«Opponent»** o «—». |
  | **«Score»** | Por ejemplo «2-1». |
  | **«Event»** | Torneo, tienda, casual…, con autocompletado. |
  | **«Notes»** | Qué funcionó y qué faltó. |

  La partida se anota con la **lista principal**. Si la caja ha cambiado desde la última versión, se guarda antes una versión nueva automática; así cada partida sabe con qué lista se jugó.

- **El resumen** muestra:
  - el **% de victorias** y el total de partidas;
  - **«W / L / D»** (victorias, derrotas, empates);
  - una tabla **«Against»** con los últimos Leaders rivales y tu balance contra cada uno.
- **«See all matches (N) →»** abre la lista completa, con ✎ para editar y 🗑 para borrar cada partida.
- **Partidas por versión:** al seleccionar una versión, el panel pasa a «Matches with vN» y solo muestra las jugadas con esa lista. Así puedes comparar qué versión funciona mejor.

## El histórico

Cuando dejas de jugar un mazo, en vez de borrarlo **muévelo al histórico** desde [Ubicaciones](ubicaciones.md#mover-al-historico-solo-mazos):
- su lista queda guardada;
- las cartas vuelven a «Unsorted»;
- sus partidas se conservan.

Para volver a jugarlo, **«Use again»** trae su Leader a la caja y, con **«Make main»** sobre su última versión, recuperas el resto de cartas.
