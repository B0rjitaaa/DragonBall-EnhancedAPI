# Development and deployment

How to run the project on your computer, run the tests and ship changes to the server.

## Running it locally

The complete step-by-step guide, including the server, is in [Step-by-step installation](instalacion.md). In short:

```bash
docker compose up -d   # everything sets itself up: catalog and prices from the repo, admin / admin, scanner fingerprints
```

| What | Where |
|---|---|
| Web app (Vite, with hot reload) | http://localhost:5173 |
| API | http://localhost:8000/api/ |
| API documentation (Swagger) | http://localhost:8000/api/docs/ |
| Admin | http://localhost:8000/admin/ (**admin / admin**) |

The catalog and prices come in the repository (`data/seed/`); `make seed` brings them up to date.

**When editing:**
- **Frontend:** the code is mounted in the container and Vite reloads by itself.
- **Backend:** `runserver` also reloads by itself when you save.
- **Celery:** the workers **don't** reload by themselves. Restart them after changing tasks:

  ```bash
  docker compose restart celery_worker scanner_worker celery_beat
  ```

## Tests

```bash
make test                                                         # all the backend ones
docker compose exec backend python manage.py test prices          # only one app's
docker compose exec frontend npm run lint                         # frontend lint (oxlint)
docker compose exec frontend npx tsc -b                           # type check
python3 scripts/check_wiki_links.py                               # wiki links, in both languages
```

**Where the tests are:**
- `backend/cards/tests/`;
- `backend/scanner/tests/` (includes a recognition benchmark);
- `backend/prices/tests.py`, `backend/collection/tests.py`, `backend/decks/tests.py`, `backend/errorlog/tests.py`, `backend/backups/tests.py`.

## Branches

- **`develop`**: day-to-day work. Changes are tested locally and pushed here.
- **`main`**: what's in production. **Deploys are made from `main`.**

## Continuous integration (GitHub Actions)

On every push to `develop` or `main`, and on every pull request, `.github/workflows/ci.yml` runs. A new push to the same branch cancels the previous run.

| Job | What it does |
|---|---|
| **backend** | Python 3.12 with Postgres 16 and Redis 7. Checks that no migrations are missing (`makemigrations --check`) and runs **all** the tests. |
| **frontend** | Node 22. `npm ci` and `npm run build` (TypeScript types + Vite build). |

**Nothing is deployed while CI is red.**

## Deploying to the server

The usual flow:

1. **Commit on `develop`** and push. Wait for CI to pass.
2. **Bring `develop` into `main`:**

   ```bash
   git push origin develop:main
   ```

3. **On the server**, update the clone:

   ```bash
   cd ~/Development/DragonBall-EnhancedAPI
   git pull --ff-only
   ```

   The server's clone has a **git hook** (`.githooks/post-merge`, enabled once with `make hooks`). After every `git pull` on `main`, the hook launches the deploy by itself.

### What the deploy does (`scripts/deploy.sh`, also `make deploy`)

1. `git pull --ff-only`, unless it's launched with `SKIP_PULL=1`, as the hook does.
2. If there are no new commits, it stops (“✔ No new changes (use FORCE=1 to force it).”), unless `FORCE=1` is set.
3. It rebuilds only what has changed:
   - the **backend**, if `requirements.txt`, the `Dockerfile` or `entrypoint.sh` change;
   - the **frontend** (production build), if anything in `frontend/` changes;
   - the **camera**, if `camera/` changes and it's enabled.
4. `docker compose up -d`.
5. Applies the **migrations**.
6. Restarts `backend`, `celery_worker`, `celery_beat` and `scanner_worker`.
7. Cleans up the Docker images no longer in use, and ends with “✔ Updated to …”.

> [!WARNING]
> The deploy **only restarts containers**. If you've changed the **volumes** in `docker-compose*.yml` or the **`.env`**, also run `docker compose up -d` on the server so they're applied.

To skip the hook on a specific `pull`:

```bash
SKIP_DEPLOY_HOOK=1 git pull
```

### After deploying

- Open the web app and check that it loads. In the scanner, anyone who has it open will see “A new version of the site is available.”
- Look at `http://192.168.1.50/api/health/`: it should say `"status": "ok"`.
- If you changed tasks or prices, check the admin (*Errors*, *Sync runs*) the next day.

## HTTPS for the phone camera

Once per server, or when its IP changes:

```bash
scripts/local-https.sh 192.168.1.50
```

The script:
1. creates, or reuses, its **own certificate authority** (`certs/ca.key` and `certs/ca.crt`), restricted to private IPs and `.local` names;
2. creates the server certificate, valid for 825 days as iOS requires;
3. recreates the frontend container so nginx enables HTTPS.

Then install `http://192.168.1.50/ca.crt` on each phone (see [Using the scanner](escaner.md#before-you-start-the-phone-camera-needs-https)).

> [!CAUTION]
> `certs/ca.key` must never leave the server.

## Screenshots for this wiki

The screenshots in `frontend/wiki/img/` are generated with a script that opens the local web app in Chrome:

```bash
pip install playwright        # once; it uses the installed Chrome
python scripts/wiki_screenshots.py          # all of them
python scripts/wiki_screenshots.py precios  # only the ones whose name contains “precios”
```

It needs the local web app running (`make up`) and a local superuser for the admin screenshots. The script opens the session without a password.

## Writing in the wiki

The wiki is the Markdown files in `frontend/wiki/`, in two languages with the same file names:
- `frontend/wiki/es/<slug>.md`: Spanish;
- `frontend/wiki/en/<slug>.md`: English;
- `frontend/wiki/img/`: the images, shared by both languages.

They can be read as they are on GitHub, and the web app shows them at `/wiki`. The **ES / EN** switch in the web wiki remembers your choice and, the first time, uses your browser's language.

**To add an article:**
1. Create `frontend/wiki/es/<slug>.md` and `frontend/wiki/en/<slug>.md`, each starting with `# Title`.
2. Add it to `WIKI_ARTICLES` in `frontend/src/lib/wiki.ts`, with its category, title and summary in both languages, and its cover screenshot.
3. Add it to the index in `frontend/wiki/es/README.md` and `frontend/wiki/en/README.md`.
4. Run `python3 scripts/check_wiki_links.py`: it checks the links, anchors and images in both languages, and that no article is missing in either of them.

**Conventions:**
- **Links between articles:** `[text](other-article.md)` or `[text](other-article.md#section)`. The anchor is the target heading in that same language.
- **Images:** `![caption](../img/screenshot.jpg)`. The alt text is shown as the caption.
- **Callouts:** `> [!NOTE]`, `> [!TIP]`, `> [!IMPORTANT]`, `> [!WARNING]`, `> [!CAUTION]`. They look the same on GitHub.
