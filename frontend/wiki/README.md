# Wiki de DragonBall EnhancedAPI

Guía de uso y documentación técnica. Estos mismos artículos se ven en la web, en **`/wiki`** (por ejemplo `http://192.168.1.50/wiki`), con buscador y capturas ampliables.

![La wiki en la web](img/wiki.jpg)

## 🚀 Primeros pasos
- [Bienvenido a DragonBall EnhancedAPI](bienvenida.md): qué es la web, sus secciones y cómo está montada.
- [Enlaces, direcciones y atajos](enlaces-y-navegacion.md): compartir cartas y búsquedas, y los atajos de teclado.

## 🧰 Instalación
- [Instalación paso a paso](instalacion.md): con Docker, en tu ordenador o en el servidor.
- [Qué tiene que estar en marcha](servicios.md): contenedores, tareas, systemd y lo opcional de fuera del servidor, y cómo comprobarlos.

## 🔎 Buscador
- [Buscar cartas](buscar-cartas.md): búsqueda por texto, panel de filtros, orden y paginación.
- [Modo avanzado](modo-avanzado.md): condiciones con Y / O / NO.
- [La ficha de una carta](ficha-de-carta.md): texto, impresiones, precio, errata, Q&A y tus copias.
- [Novedades](novedades.md): cambios del catálogo desde tu última visita.

## 🗂️ Colección y mazos
- [Mi colección](mi-coleccion.md): copias, ubicaciones, falsas y valor.
- [Ubicaciones](ubicaciones.md): mazos, archivadores y cajas.
- [Mazos](mazos.md): Leader, versiones, side deck, partidas, estadísticas e histórico.
- [Importar, exportar y copia de la colección](importar-exportar.md): CSV y JSON.

## 📷 Escáner
- [Usar el escáner](escaner.md): móvil, HTTPS, modo ráfaga y modo archivador.
- [Revisar escaneos dudosos](revisar-escaneos.md): confirmar y corregir.
- [Cómo reconoce las cartas](como-reconoce.md): huellas, umbrales y fotos.

## 💶 Precios
- [De dónde sale cada precio](precios.md): Cardmarket, TCGplayer y precios a mano.
- [La página «Precios»](pagina-precios.md): valor de la colección, las que suben y las que bajan.
- [Revisar precios en el admin](revisar-precios.md): emparejar, corregir y poner precios a mano.

## 🛠️ Administración
- [El admin de Django](admin.md): qué hay en `/admin/`.
- [Registro de errores](registro-de-errores.md): fallos guardados y avisados por Telegram.
- [Copias de seguridad](copias-de-seguridad.md): diaria, bajo demanda, retención y restauración.

## ⚙️ Técnico
- [Arquitectura](arquitectura.md): servicios, servidores y configuración.
- [Datos y sincronización](datos-y-sincronizacion.md): Bandai, web oficial, imágenes e impresiones propias.
- [Tareas programadas y avisos](tareas-programadas.md): horarios, salud y Telegram.
- [Desarrollo y despliegue](despliegue.md): local, tests, CI y subir al servidor.
- [API REST](api.md): todos los endpoints.

## 💬 Ayuda
- [Preguntas frecuentes y problemas](preguntas-frecuentes.md)

---

**Para editar la wiki** ve a [Desarrollo y despliegue → Escribir en la wiki](despliegue.md#escribir-en-la-wiki). Las capturas se regeneran con `python scripts/wiki_screenshots.py`.
