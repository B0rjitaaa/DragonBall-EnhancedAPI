# Bienvenido a DragonBall EnhancedAPI

**DragonBall EnhancedAPI** es una web para **Dragon Ball Super Card Game** (Masters). Tiene cuatro usos:
- **buscar** en todo el catálogo de cartas con mucho más detalle que la web oficial;
- **gestionar tu colección**: qué cartas tienes, dónde están y cuánto valen;
- **montar y seguir tus mazos**: versiones de la lista, partidas y estadísticas;
- **dar de alta cartas con la cámara** del móvil.

Funciona en la red de casa, en el servidor **servidor**. Ábrela en `http://192.168.1.50/` desde el ordenador o el móvil.

![«Search», la página principal](../img/buscador.jpg)

## Las secciones

El menú de arriba es el mismo en todas las páginas:

| Sección | Para qué sirve | Empieza por |
|---|---|---|
| «Search» (buscador) | Todo el catálogo (más de 9.000 impresiones), con búsqueda por texto, filtros por cualquier atributo y un modo avanzado con «AND» / «OR» / «NOT». | [Buscar cartas](buscar-cartas.md) |
| «My collection» (mi colección) | Lo mismo que «Search», pero solo con tus cartas: copias, ubicaciones, falsas y el valor de todo. | [Mi colección](mi-coleccion.md) |
| «Locations» (ubicaciones) | Tus mazos, archivadores y cajas, con su valor, su Leader y su histórico. | [Ubicaciones](ubicaciones.md) |
| «Prices» (precios) | Cuánto vale tu colección, cómo evoluciona y qué cartas suben y bajan. | [La página «Prices»](pagina-precios.md) |
| «News» (novedades) | Cartas nuevas, cambios de texto, ban list, erratas y preguntas oficiales. | [Novedades](novedades.md) |
| «Wiki» | Esta guía. | — |
| «Scanner» (escáner) | Reconoce cartas con la cámara y las añade a tu colección. | [Usar el escáner](escaner.md) |

Y para administrar, el **admin de Django** en `/admin/`: revisión de precios, errores y copias de seguridad. Ver [El admin de Django](admin.md).

## Qué ofrece frente a la web oficial

- **Búsqueda de verdad:**
  - por cualquier palabra del texto, con frases exactas y exclusiones;
  - por cualquier atributo, combinándolos como quieras;
  - con recuentos en cada filtro.
- **Todo en una ficha:** la información de la carta, sus otras impresiones, su precio, su errata, sus Q&A y tus copias.
- **Ban list siempre al día**, aplicada a todas las impresiones y avisada en tus mazos.
- **Mazos con historia:** versiones de la lista, side deck, partidas contra cada Leader, reglas de construcción comprobadas y el histórico de mazos que ya no juegas.
- **Precios** de Cardmarket contrastados con TCGplayer, con historial diario.
- **Escáner** con «Burst mode» (modo ráfaga) para dar de alta cajas enteras.

## Cómo está montada (en dos líneas)

- **Piezas:** una API en **Django** con **PostgreSQL**, tareas en segundo plano con **Celery** y **Redis**, y una web en **React**, todo en **Docker**.
- **Datos:** salen de la API de **Bandai TCG+**, de la web oficial del juego, de **Cardmarket** y de **TCGplayer**. Se actualizan solos cada día.

El detalle está en [Arquitectura](arquitectura.md).

## Por dónde seguir

- **Si vas a instalarla:** [Instalación paso a paso](instalacion.md).
- **Si vas a buscar cartas:** [Buscar cartas](buscar-cartas.md) y [La ficha de una carta](ficha-de-carta.md).
- **Si quieres meter tu colección:** [Usar el escáner](escaner.md) y luego [Mi colección](mi-coleccion.md).
- **Si juegas:** [Mazos](mazos.md).
- **Si algo no funciona:** [Preguntas frecuentes y problemas](preguntas-frecuentes.md).
