# Ubicaciones

Una **ubicación** es un sitio donde guardas cartas: un mazo, un archivador, una caja… La página **Ubicaciones** (`/locations`) las lista todas con sus copias y su valor, y desde ella se crean, se editan, se ordenan y se mandan mazos al histórico.

![Ubicaciones: pestañas por tipo, mazos en uso con el arte de su Leader, histórico, archivadores y cajas](img/ubicaciones.jpg)

## Tipos de ubicación

| Tipo | Para qué | En la página |
|---|---|---|
| **Mazo** | Un mazo montado. Tiene Leader, versiones, side deck y partidas: ver [Mazos](mazos.md). | Pestaña «Mazos» |
| **Archivador** | Carpetas con fundas de 9. | Pestaña «Archivadores» |
| **Almacén** | Cajas de cartas sueltas. | Pestaña «Almacén» |
| **Otro** | Cualquier otra cosa. | Pestaña «Otras», solo si hay alguna |

Además está **«Sin ubicar»**: siempre existe y **no se puede borrar**. Es donde caen:
- las cartas escaneadas sin destino;
- las añadidas con **+** sin elegir ubicación;
- las de un mazo que pasa al histórico;
- las de una ubicación que se borra.

Si «Sin ubicar» tiene copias, arriba de la página aparece **«N copias sin ubicar · Ordenarlas →»**, que te lleva a ellas para repartirlas.

> [!NOTE]
> Esta página no mueve cartas. Para moverlas usa la [vista Lista de Mi colección](mi-coleccion.md#vista-lista-mover-copias) (el enlace está en el texto de la cabecera).

## Las pestañas

Arriba están **Mazos**, **Archivadores**, **Almacén** y **Otras**, cada una con su número. Al bajar por la página, la pestaña activa cambia sola según la sección que estás viendo.

### Mazos

**«En uso N»:** una tarjeta por mazo con:
- el **arte de su Leader** (su cara Awaken) y los puntos de color;
- el nombre del mazo y el de su Leader;
- **«N copias · M cartas · X €»**: el valor sale de Cardmarket y no cuenta las falsas;
- **«N falsas»**, que lleva al mazo mostrando también las falsas;
- **⚠ N Banned · M Limited repetida(s)**, si hay cartas que no se pueden jugar. Al pasar el ratón se ven los números.

**Cómo se elige el Leader:** es la carta LEADER que hay en la caja. Si hay varias, la auténtica de la que tienes más copias. Si la caja está vacía, se usa el Leader de su última lista guardada.

**«Histórico N»** (desplegable): los mazos que ya no juegas, «mazos que ya no usas; su última lista queda guardada». Cada uno muestra:
- cuántas copias quedan en la caja, o cuántas cartas tenía su última lista;
- desde cuándo está en el histórico, y «N.ª vez» si ya ha pasado varias veces;
- el botón **«Volver a usar»**.

### Archivadores, Almacén y Otras

Una fila por ubicación con:
- su nombre y sus notas;
- **«N copias · M cartas · X €»** y «N falsas»;
- una barra que compara su tamaño con el resto.

Al pulsarla se abre esa ubicación en Mi colección.

## Crear una ubicación

Cada sección tiene su botón: **«+ Nuevo mazo»**, **«+ Nuevo archivador»**, **«+ Nueva caja»** o **«+ Nueva ubicación»**. Escribe el nombre (único, hasta 80 caracteres) y pulsa **Crear**.

## Ordenar las ubicaciones

Con más de una ubicación en una sección aparece el botón **«Ordenar»**:
1. Arrastra cada fila por su asa **⠿**. En el móvil, mantenla pulsada un momento antes de arrastrar.
2. Pulsa **«Listo»** para terminar.

Este orden es el que se usa en todos los selectores de ubicación de la web.

## El menú ⋯ de cada ubicación

### Editar…

El diálogo **«Editar ubicación»** permite cambiar:
- el **Nombre**;
- el **Tipo** (Mazo, Archivador, Almacén, Otro);
- las **Notas**, por ejemplo «caja azul del armario».

**«Borrar…»** pide confirmación: «¿Borrar «Caja 3»? Sus N copias pasarán a «Sin ubicar».» Los escaneos que apuntaban a esa ubicación también pasan a «Sin ubicar».

> [!WARNING]
> - Un mazo con **partidas anotadas** no se puede borrar. Borra antes sus partidas o cámbiale el tipo.
> - El estado «en uso / en el histórico» no se cambia editando: se cambia con las opciones de abajo.

### Mover al histórico (solo mazos)

Cuando desmontas un mazo:

1. Se abre **«Mover «Nombre» al histórico»** con la lista de lo que hay en la caja, marcando el Leader y las falsas.
2. Pulsa **«Mover al histórico»**. Entonces:
   - si la caja tenía cartas, su lista se guarda como versión automática **«Al pasar al histórico»**;
   - todas las copias, auténticas y falsas, pasan a **«Sin ubicar»**;
   - el side deck se vacía;
   - el mazo pasa al histórico y queda apuntado en su registro.
3. Al terminar puedes **«Copiar lista»**, que copia el texto `2x BT1-001 Nombre`, para saber qué cartas guardar, o ir a **«Ver «Sin ubicar»»**.

### Volver a usar (solo mazos del histórico)

El mazo vuelve a **En uso** y la web **trae una copia de su Leader** a la caja, buscándola por este orden:
1. Primero auténticas.
2. Primero de «Sin ubicar», luego de archivadores y cajas, y como último recurso de otros mazos.

El aviso te dice de dónde la ha sacado; el resto de cartas las recuperas restaurando su última versión. Si no tienes ninguna copia del Leader, el aviso lo dice. **«Abrir el mazo»** te lleva directamente.

### Registro de uso…

En los mazos que han pasado alguna vez por el histórico verás un registro con:
- cuántas veces ha pasado al histórico y si ahora está en uso o en el histórico;
- cada entrada con fecha y hora: **«Al histórico»**, con cuántas copias salieron, o **«Vuelve a usarse»**.
