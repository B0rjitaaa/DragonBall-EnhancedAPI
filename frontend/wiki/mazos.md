# Mazos

Un **mazo** es una [ubicación](ubicaciones.md) de tipo Mazo. Al abrirlo (`/collection/deck/<id>`, o eligiéndolo en Mi colección) se ve en la vista **«Mazo»**:
- el Leader;
- el Main Deck, el Z Deck y el Side Deck;
- la comprobación de las reglas de construcción;
- estadísticas;
- las **versiones** de la lista;
- las **partidas** jugadas.

![Vista Mazo: Leader, contadores, avisos de construcción, estadísticas, partidas y la lista por secciones](img/mazo.jpg)

## Caja, lista principal y versiones

Estas tres ideas son la clave para entender los mazos:

- **La caja** es lo que hay físicamente en esa ubicación: las copias que la web tiene apuntadas en el mazo.
- **Las versiones** (v1, v2, v3…) son listas guardadas. Cada vez que cambias el mazo y guardas, se crea una versión nueva, así queda el historial de cómo ha evolucionado.
- **La lista principal** (★) es la versión que está, o debería estar, en la caja. Las partidas se anotan contra ella.

Cuando la caja y la principal coinciden, todo cuadra. Si mueves copias por fuera (desde Mi colección o el escáner), la web te avisa de que **«la caja ha cambiado»**.

## La cabecera del mazo

### El Leader

- **Ver la otra cara:** pulsa el Leader para alternar **Front** ⟲ **Awaken**. Por defecto se ve la cara Awaken.
- **«número · ficha»** abre su ficha.
- **«Quitar»** lo quita de la lista. Para poner otro, usa «Añadir carta».

### Contadores

- **«N/60 Main Deck»**: en verde cuando estás entre 50 y 60.
- **«N Z Deck»**.
- **«X.X Av. Energy»**: el coste medio del Main Deck.
- **«N side»**: si hay side deck.

### Reglas de construcción

Si todo está bien se lee **«✓ Cumple las reglas de construcción»**. Si no, **«⚠ N avisos de construcción»**, que se despliega:

| Aviso | Regla |
|---|---|
| Falta la carta Leader | Todo mazo necesita un Leader. |
| Faltan N cartas para llegar a 50 | Mínimo 50 cartas en el Main Deck. |
| Sobran N cartas (máximo 60) | Máximo 60 cartas en el Main Deck. |
| BT1-030 Nombre: N copias (máx. 4) | Máximo 4 copias de un **mismo número**, sumando todas sus impresiones (normal + alt-art…) en Main y Z Deck. |
| … está Banned | No se puede jugar. |
| … es Limited: máximo 1 copia | Solo 1 copia. |
| Ultimate: máx. 1 copia | Las cartas con [Ultimate]. |
| Super Combo: máx. 4 en el mazo | Máximo 4 cartas [Super Combo]. |
| Dragon Ball: máx. 7 en total | Máximo 7 cartas [Dragon Ball]. |
| Hay N cartas Leader en el mazo | Es una advertencia, no un error. |

Cada carta con problemas lleva una marca con el motivo.

> [!NOTE]
> Las reglas se comprueban sobre el **Main Deck** (y el Z Deck para las 4 copias). El **side deck no se comprueba**.

### Estadísticas

- **Curva de Energy:** barras de coste de 0 a 10+.
- **Tipos:** Battle, Extra, Unison.
- **Colors:** reparto de colores.

**Pulsa cualquier barra o color para filtrar la lista**: por ejemplo, ver solo las cartas de coste 2. Cada sección dice entonces «X de Y cartas». **«✕ Quitar filtros»** vuelve a mostrarlo todo.

## Las secciones de la lista

- **Mazo principal** (Main Deck).
- **Z Deck**: las cartas cuyo tipo empieza por «Z-» (Z-BATTLE, Z-EXTRA…).
- **Side deck**.

Las copias falsas que hay en la caja también cuentan en la lista, porque físicamente están en el mazo.

## Preparar cambios (el borrador)

Con la pestaña **«Principal»** seleccionada puedes preparar una lista nueva **sin mover nada todavía**:

- **− / +** en cada carta cambia sus copias (de 0 a 99).
- **→ Side** pasa una copia al side deck; **↩ Mazo** la devuelve.
- **+ Añadir carta** (al final del Main Deck) abre un buscador de todo el catálogo. Escribe al menos 2 letras del nombre, número o texto y pulsa una carta para sumar una copia; puedes pulsar varias veces. **«Listo»** cierra el buscador.
- **Cada cambio** se ve sobre la carta como **+N** o **−N**: «Cambio sin guardar respecto a lo que hay en la caja».

El borrador se guarda en tu navegador: si recargas la página, no se pierde. **«Descartar»** lo tira.

> [!TIP]
> El borrador no toca tu colección. Sirve para probar ideas («¿y si quito 2 de esta y pongo 2 de aquella?») y ver al momento cómo quedan la curva y los avisos de reglas.

### Ordenar las cartas

Sin cambios pendientes y sin filtros, puedes **arrastrar las cartas** dentro de su sección para ordenarlas a tu gusto. En el móvil, mantén pulsada la carta antes de arrastrar.

## Guardar la lista

**«Guardar lista»** abre «Guardar lista vN», con dos campos opcionales: **Nombre** (p. ej. «Más removal») y **Notas**.

- **Si las cartas ya están en la caja:** «✓ Estas cartas ya están en la caja del mazo: la lista pasará a ser la principal.»
- **Si no:** te enseña qué copias habría que mover y te deja elegir entre dos botones:
  - **«Solo guardar»**: guarda la versión sin tocar la caja;
  - **«Guardar y hacer principal (N copias)»**: guarda y además mueve las copias.

Una versión que coincide exactamente con la caja (side incluido) pasa a ser la principal automáticamente.

## Hacer principal una versión (mover copias)

Al elegir una versión en la barra de listas aparecen sus datos y sus botones:
- **«vN · guardada el …»**, con las etiquetas **★ principal** y **automática**;
- **«Cambios desde vN»**: qué cambió respecto a la anterior;
- **«Hacer principal»**, o **«Recolocar la caja»** si ya es la principal pero la caja ha cambiado;
- **«Renombrar»** y **«Borrar»**. Solo se puede borrar una versión sin partidas, y borrarla no mueve cartas.

**«Hacer principal»** mueve **de verdad** copias de tu colección para que la caja quede igual que esa versión. Antes de hacerlo te enseña el plan:

- **«Salen de la caja N copias»**:
  - van a **«Llevarlas a»**, que por defecto es «Sin ubicar»;
  - puedes elegir otro destino para cada carta;
  - salen primero las falsas.
- **«Entran en la caja N copias»**:
  - de cada carta se ve de dónde se coge (por ejemplo «De: Sin ubicar 2 + Caja 3 1»). Va primero a «Sin ubicar», luego a archivadores y cajas, y como último recurso a otros mazos;
  - puedes forzar el origen de cada carta.
- **Avisos posibles:**
  - **«⚠ Se sacarán copias de otros mazos»**;
  - **«⚠ Faltan N copias»**, si no tienes suficientes. La caja quedará incompleta hasta que las consigas;
  - **«⚠ Lo que hay ahora en la caja no está guardado como lista»**. Guárdalo antes si quieres poder volver a ello.

Pulsa **«Mover N copias y hacer principal»**. Al terminar se resume cuántas salieron y entraron.

> [!IMPORTANT]
> La web mueve las copias **en tu colección**. Haz el mismo movimiento con las cartas de verdad para que todo siga cuadrando.

## Partidas

El panel **«Partidas»** guarda tus resultados con el mazo.

- **«+ Resultado»** abre el formulario **«Anotar resultado»**:

  | Campo | Detalle |
  |---|---|
  | **Opponent Leader** | Busca el Leader rival por nombre o número. Te ofrece los 6 últimos que has anotado. Si no está en el catálogo, **«Usar «texto» sin carta»**. |
  | **Resultado** | **Victoria**, **Derrota** o **Empate**. |
  | **Fecha** | Hoy por defecto. No admite fechas futuras. |
  | **Oponente** | Nombre del rival, con autocompletado. |
  | **¿Quién empezó?** | **Yo**, **Opponent** o «—». |
  | **Marcador** | Por ejemplo «2-1». |
  | **Evento** | Torneo, tienda, casual…, con autocompletado. |
  | **Notas** | Qué funcionó y qué faltó. |

  La partida se anota con la **lista principal**. Si la caja ha cambiado desde la última versión, se guarda antes una versión nueva automática; así cada partida sabe con qué lista se jugó.

- **El resumen** muestra:
  - el **% de victorias** y el total de partidas;
  - **V / D / E**;
  - una tabla **«Contra»** con los últimos Leaders rivales y tu balance contra cada uno.
- **«Ver todas las partidas (N) →»** abre la lista completa, con ✎ para editar y 🗑 para borrar cada partida.
- **Partidas por versión:** al seleccionar una versión, el panel pasa a «Partidas con vN» y solo muestra las jugadas con esa lista. Así puedes comparar qué versión funciona mejor.

## El histórico

Cuando dejas de jugar un mazo, en vez de borrarlo **muévelo al histórico** desde [Ubicaciones](ubicaciones.md#mover-al-historico-solo-mazos):
- su lista queda guardada;
- las cartas vuelven a «Sin ubicar»;
- sus partidas se conservan.

Para volver a jugarlo, **«Volver a usar»** trae su Leader a la caja y, con **Hacer principal** sobre su última versión, recuperas el resto de cartas.
