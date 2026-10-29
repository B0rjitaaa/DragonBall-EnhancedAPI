# Cómo reconoce las cartas

Este artículo explica qué hace el servidor con cada foto. No hace falta para usar el escáner, pero ayuda a entender sus porcentajes y por qué a veces duda.

## El recorrido de una foto

```
Foto ─▶ recorte y enderezado ─▶ huella rápida (hash) ─┬─▶ ¿clara? ─▶ resultado
                                                      └─▶ ORB (puntos) ─▶ desempate de ediciones ─▶ resultado
```

### 1. Recorte y enderezado

El servidor busca los **bordes de la carta** en la foto, corrige la perspectiva y la deja recta, a 315 × 440 píxeles. Si no encuentra los bordes, sigue con la foto entera e indica «bordes de la carta no detectados» en el resultado.

### 2. Huella rápida (hash perceptual)

Cada carta del catálogo tiene **huellas** calculadas a partir de su imagen oficial (anverso y reverso), más las fotos que tú has confirmado. Primero se compara la foto con todas esas huellas, también girada 180° por si la carta está del revés.

Si la mejor coincidencia está **muy cerca** (distancia ≤ 20) y la segunda bastante más lejos (6 o más de diferencia), ya está. En el resultado aparece el método `hash`, y suele tardar unos pocos milisegundos.

### 3. Puntos característicos (ORB)

Si la huella rápida no basta, se compara con más detalle usando **puntos característicos** (esquinas, trazos, textos) de las mejores candidatas:
- Primero se miran las 8 mejores.
- Si ninguna llega a 15 puntos en común, se amplía a 48.
- La **confianza** (el porcentaje) sale de cuántos puntos coinciden: con 60 o más es el 100 %.

En el resultado aparece el método `orb`.

### 4. Desempate entre ediciones

El caso difícil son las **impresiones del mismo número** (normal, alt-art, SPR, promos de torneo…), que a veces solo se distinguen por el sello o el foil. Cuando las dos mejores candidatas son del mismo número:
- se compara la foto con todas las impresiones de ese número, **mirando solo las zonas donde se diferencian**;
- si tienes una **foto confirmada** de alguna de ellas, se usa en lugar de la imagen oficial (se parece más a lo que ve tu cámara);
- hace falta un 15 % de margen para decidir. Si no lo hay, el escaneo va a **«Revisar»**.

## Los umbrales

| Umbral | Valor | Qué decide |
|---|---|---|
| Confianza mínima | **45 %** | Por debajo, el escaneo queda «Por revisar». |
| Añadir sola (ráfaga y archivador) | **65 %** | A partir de aquí la carta se suma sola a la colección. |
| Captura sin carta | menos del 45 % y sin bordes | En ráfaga se descarta en silencio. |

Los umbrales se pueden ajustar en el servidor con variables de entorno (ver [Arquitectura](arquitectura.md#variables-de-entorno)).

## El escáner aprende contigo

Cada vez que **confirmas** o **corriges** una carta, su recorte se guarda como huella nueva de esa carta. Con el tiempo, el escáner reconoce mejor tus cartas con tu cámara y tu luz, sobre todo las alt-arts y las promos que se parecen entre sí.

## Velocidad

- **Un worker propio:** el reconocimiento corre en un proceso dedicado (`scanner_worker`) que atiende las fotos de una en una. Así un escáner muy usado no frena al resto de la web.
- **Siempre caliente:** cada minuto se «calienta», para que el primer escaneo tras un rato parado no tarde más.
- **Tiempos:** en el panel de la sesión se ve cuánto tardó cada carta. Si había otras en cola, también el tiempo total.

## Fotos

Las fotos de los escaneos **no se guardan para siempre**:

- Una tarea revisa cada hora (en el minuto 10) y **borra las fotos de más de 24 horas**.
- Si aun así ocupan más de **2 GB**, borra las más antiguas hasta bajar a **1,5 GB**.
- El registro del escaneo se conserva en el historial, sin foto.
- Las **huellas aprendidas no se pierden**: están en la base de datos.
- Las fotos **no entran en las copias de seguridad**.

## Huellas del catálogo

Cuando entran cartas nuevas en el catálogo, sus huellas se calculan a partir de las imágenes oficiales. Las impresiones creadas a mano (promos que no están en Bandai) también tienen huella, calculada a partir de la imagen que se les dio. Ver [Datos y sincronización](datos-y-sincronizacion.md#impresiones-propias).
