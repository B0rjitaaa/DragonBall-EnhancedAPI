# Preguntas frecuentes y problemas

## Uso

### ¿Cómo comparto una carta con alguien?

En su ficha, pulsa **🔗 Copiar enlace**. El enlace tiene la forma `…/?card=BT20-149` y abre la ficha directamente. Ver [Enlaces, direcciones y atajos](enlaces-y-navegacion.md#enlace-a-una-carta).

### ¿Puedo guardar una búsqueda?

Sí. Toda la búsqueda (texto, filtros, orden, modo avanzado) va en la dirección del navegador: guárdala en favoritos.

### ¿Por qué el valor de mi colección no incluye todas mis cartas?

El valor solo suma:
- copias **auténticas**: las [falsas](mi-coleccion.md#copias-falsas) nunca cuentan;
- cartas con **precio de mercado** (con ventas) o **puesto a mano**.

Las que solo tienen un anuncio de un vendedor van **aparte** («+ X € en cartas sin ventas»). Las de precio dudoso no cuentan hasta revisarlas. Al pasar el ratón por el valor ves cuántas copias quedan fuera y por qué. Ver [De dónde sale cada precio](precios.md).

### Un precio me parece mal. ¿Cómo lo corrijo?

1. En la ficha de la carta, compara las fuentes («Cardmarket X € · TCGplayer Y €») y abre **Ofertas en Europa ↗** para ver la carta en Cardmarket.
2. Si está emparejada con el producto equivocado, o quieres fijar el precio, ve a la [revisión de precios](revisar-precios.md) del admin. Allí puedes elegir el producto correcto, poner el precio a mano o cambiar tus copias a la edición buena.

### He hecho un lío en la colección. ¿Puedo volver atrás?

Sí, si tienes una **copia JSON** de antes, la de «Descargar copia». Usa **Restaurar copia** en Mi colección: verás qué cambia antes de aplicarlo, y antes de sustituir se descarga una copia de lo actual por si acaso. Ver [Restaurar copia](importar-exportar.md#restaurar-copia).

### He añadido una carta en la ubicación equivocada

Ábrela en Mi colección y usa **Mover…** en su ficha, o la [vista Lista](mi-coleccion.md#vista-lista-mover-copias), para moverla.

### ¿Qué pasa con mis cartas si borro una ubicación?

Pasan a **«Sin ubicar»**: no se pierde ninguna copia. Un mazo con partidas anotadas no se puede borrar; mándalo al histórico.

### ¿Cómo desmonto un mazo sin perder su lista?

En [Ubicaciones](ubicaciones.md), menú ⋯ → **Mover al histórico**. La lista se guarda como versión, las cartas vuelven a «Sin ubicar» y las partidas se conservan. Para volver a montarlo, **Volver a usar**.

### El escáner ha añadido la edición equivocada

- **Durante la sesión:** pulsa **Corregir** en esa fila.
- **Después:** búscala en Mi colección y quita la copia, o usa en la [revisión de precios](revisar-precios.md) la opción **«Tengo otra edición»**, que cambia tus copias de impresión.

Confirmar la buena enseña al escáner para la próxima vez.

## Problemas

### Al guardar algo sale un error «CSRF»

Pasa cuando tienes **la sesión del admin abierta** en el mismo navegador. Cierra sesión en `/admin/`, o usa el admin en una ventana privada. Hay un arreglo preparado pero sin desplegar todavía.

### La cámara del móvil no se abre en el escáner

- **«El navegador solo permite la cámara en directo con HTTPS»:** pulsa **«Abrir la versión segura»**. La primera vez tendrás que instalar el certificado en el móvil (ver [Usar el escáner](escaner.md#antes-de-empezar-la-camara-del-movil-necesita-https)).
- **«Permiso de cámara denegado»:** en el iPhone, Ajustes → Chrome (o Safari) → Cámara → Permitir, y recarga.
- **Como alternativa**, usa **Subir foto**.

### El modo ráfaga no captura las cartas

- Empieza con la zona del marco **vacía**: aprende el fondo durante un segundo.
- Deja cada carta **quieta** un momento.
- Usa un **fondo liso**, con luz uniforme y sin reflejos.
- Si lo necesitas, **Capturar ahora** fuerza la captura.

### Aparece una franja roja bajo el menú

Algo importante del servidor está caído: la base de datos, Redis, el escáner o las tareas de fondo. Si dura más de 10 minutos te llegará también un Telegram. Revisa el servidor (ver abajo).

### La web no carga en absoluto

1. **Comprueba que el servidor está encendido y en la red.** Si configuraste la vigilancia de caídas (Healthchecks.io o el vigilante), te habrá llegado un aviso.
2. **Entra por SSH y mira los contenedores:**

   ```bash
   cd ~/Development/DragonBall-EnhancedAPI
   docker compose ps
   docker compose logs --tail 100 backend
   ```

3. **Si alguno está parado:** `docker compose up -d`.

### Faltan cartas nuevas que ya ha publicado Bandai

Las cartas nuevas se buscan cada día a las 04:00. Para no esperar:

```bash
docker compose exec backend python manage.py sync_cards
```

Si la sincronización falla, mira *sync runs* en el admin y los [errores](registro-de-errores.md).

### Ha llegado un aviso de que la copia de seguridad ha fallado

Abre **Copias de seguridad** en el admin: verás en qué paso falló y el mensaje de error. Lanza otra con **Hacer copia ahora**. Si lo que falla es solo la **copia fuera del servidor** («Copia fuera del servidor: ❌ falló»), comprueba el destino: el otro equipo encendido, o la nube con `rclone lsd <remoto>:`. Ver [Copias de seguridad](copias-de-seguridad.md).

### He desplegado y no se ven los cambios

- **Navegador:** recarga sin caché. En el escáner sale el aviso «Hay una versión nueva de la web».
- **Volúmenes o `.env`:** si los cambiaste, ejecuta `docker compose up -d` en el servidor. El despliegue solo reinicia contenedores.
- **Comprueba** que `main` tiene tus commits y que la CI pasó. Ver [Desarrollo y despliegue](despliegue.md).
