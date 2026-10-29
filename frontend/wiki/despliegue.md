# Desarrollo y despliegue

Cómo levantar el proyecto en tu ordenador, pasar los tests y subir los cambios al servidor.

## Levantarlo en local

El paso a paso completo, con el servidor, está en [Instalación paso a paso](instalacion.md). En resumen:

```bash
docker compose up -d   # todo se prepara solo: catálogo y precios del repo, admin / admin, huellas del escáner
```

| Qué | Dónde |
|---|---|
| Web (Vite, con recarga en caliente) | http://localhost:5173 |
| API | http://localhost:8000/api/ |
| Documentación de la API (Swagger) | http://localhost:8000/api/docs/ |
| Admin | http://localhost:8000/admin/ (**admin / admin**) |

El catálogo y los precios vienen en el repositorio (`data/seed/`); `make seed` los pone al día.

**Al editar:**
- **Frontend:** el código está montado en el contenedor y Vite recarga solo.
- **Backend:** `runserver` también se recarga solo al guardar.
- **Celery:** los workers **no** se recargan solos. Reinícialos tras tocar tareas:

  ```bash
  docker compose restart celery_worker scanner_worker celery_beat
  ```

## Tests

```bash
make test                                                         # todos los del backend
docker compose exec backend python manage.py test prices          # solo los de una app
docker compose exec frontend npm run lint                         # lint del frontend (oxlint)
docker compose exec frontend npx tsc -b                           # comprobación de tipos
```

**Dónde están los tests:**
- `backend/cards/tests/`;
- `backend/scanner/tests/` (incluye un benchmark del reconocimiento);
- `backend/prices/tests.py`, `backend/collection/tests.py`, `backend/decks/tests.py`, `backend/errorlog/tests.py`, `backend/backups/tests.py`.

## Ramas

- **`develop`**: el día a día. Los cambios se prueban en local y se suben aquí.
- **`main`**: lo que está en producción. **Se despliega desde `main`.**

## Integración continua (GitHub Actions)

En cada push a `develop` o `main`, y en cada pull request, se ejecuta `.github/workflows/ci.yml`. Un push nuevo a la misma rama cancela la ejecución anterior.

| Trabajo | Qué hace |
|---|---|
| **backend** | Python 3.12 con Postgres 16 y Redis 7. Comprueba que no falten migraciones (`makemigrations --check`) y pasa **todos** los tests. |
| **frontend** | Node 22. `npm ci` y `npm run build` (tipos de TypeScript + build de Vite). |

**No se despliega nada con la CI en rojo.**

## Desplegar en el servidor

El flujo habitual:

1. **Commit en `develop`** y push. Espera a que la CI pase.
2. **Lleva `develop` a `main`:**

   ```bash
   git push origin develop:main
   ```

3. **En el servidor**, actualiza el clon:

   ```bash
   cd ~/Development/DragonBall-EnhancedAPI
   git pull --ff-only
   ```

   El clon del servidor tiene un **hook de git** (`.githooks/post-merge`, activado una vez con `make hooks`). Después de cada `git pull` en `main`, el hook lanza el despliegue solo.

### Qué hace el despliegue (`scripts/deploy.sh`, también `make deploy`)

1. `git pull --ff-only`, salvo que se lance con `SKIP_PULL=1`, como hace el hook.
2. Si no hay commits nuevos, termina, salvo con `FORCE=1`.
3. Reconstruye solo lo que ha cambiado:
   - el **backend**, si cambian `requirements.txt`, el `Dockerfile` o `entrypoint.sh`;
   - el **frontend** (build de producción), si cambia algo en `frontend/`;
   - la **cámara**, si cambia `camera/` y está activa.
4. `docker compose up -d`.
5. Aplica las **migraciones**.
6. Reinicia `backend`, `celery_worker`, `celery_beat` y `scanner_worker`.
7. Limpia las imágenes de Docker que ya no se usan.

> [!WARNING]
> El despliegue **solo reinicia contenedores**. Si has cambiado los **volúmenes** de `docker-compose*.yml` o el **`.env`**, ejecuta además `docker compose up -d` en el servidor para que se apliquen.

Para saltarte el hook en un `pull` concreto:

```bash
SKIP_DEPLOY_HOOK=1 git pull
```

### Después de desplegar

- Abre la web y comprueba que carga. En el escáner, la web avisará con «Hay una versión nueva de la web» a quien la tenga abierta.
- Mira `http://192.168.1.50/api/health/`: debería decir `"status": "ok"`.
- Si has tocado tareas o precios, revisa el admin (*Errores*, *sync runs*) al día siguiente.

## HTTPS para la cámara del móvil

Una vez por servidor, o cuando cambie su IP:

```bash
scripts/local-https.sh 192.168.1.50
```

El script:
1. crea, o reutiliza, una **autoridad de certificación propia** (`certs/ca.key` y `certs/ca.crt`), limitada a IPs privadas y nombres `.local`;
2. crea el certificado del servidor, válido 825 días como exige iOS;
3. recrea el contenedor del frontend para que nginx active HTTPS.

Después, instala `http://192.168.1.50/ca.crt` en cada móvil (ver [Usar el escáner](escaner.md#antes-de-empezar-la-camara-del-movil-necesita-https)).

> [!CAUTION]
> `certs/ca.key` no debe salir nunca del servidor.

## Capturas de esta wiki

Las capturas de `frontend/wiki/img/` se generan con un script que abre la web local en Chrome:

```bash
pip install playwright        # una vez; usa el Chrome instalado
python scripts/wiki_screenshots.py          # todas
python scripts/wiki_screenshots.py precios  # solo las que contienen «precios»
```

Necesita la web local levantada (`make up`) y un superusuario local para las capturas del admin. El script abre la sesión sin contraseña.

## Escribir en la wiki

La wiki son los ficheros Markdown de `frontend/wiki/`:
- se leen tal cual en GitHub;
- la web los muestra en `/wiki`.

**Para añadir un artículo:**
1. Crea `frontend/wiki/<slug>.md`, empezando por `# Título`.
2. Añádelo a `WIKI_ARTICLES` en `frontend/src/lib/wiki.ts`, con su categoría, título, resumen y captura de portada.
3. Añádelo al índice de `frontend/wiki/README.md`.

**Convenciones:**
- **Enlaces entre artículos:** `[texto](otro-articulo.md)` o `[texto](otro-articulo.md#apartado)`.
- **Imágenes:** `![pie de foto](img/captura.jpg)`. El texto alternativo sale como pie.
- **Avisos:** `> [!NOTE]`, `> [!TIP]`, `> [!IMPORTANT]`, `> [!WARNING]`, `> [!CAUTION]`. Se ven igual en GitHub.
