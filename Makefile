.PHONY: install backups seed up down build logs ps deploy hooks migrate import import-prices export-prices sync sync-full test shell superuser psql reset

install:       ## Installs everything in one step (.env, services, catalog and prices, admin). On a server: make install SERVER=<ip>
	bash scripts/install.sh $(if $(SERVER),--server $(SERVER))

backups:       ## On the server: installs the daily backups (systemd; asks for sudo)
	bash scripts/systemd/install.sh

seed:          ## Rebuilds data/seed/ (the repo's catalog and prices) from this installation's data
	docker compose exec backend python manage.py export_cards /data/seed/cartas_dbs.json.gz
	docker compose exec backend python manage.py export_prices /data/seed/precios_dbs.json.gz

up:            ## Starts everything in the background
	docker compose up -d --build

down:          ## Stops the containers (data is kept)
	docker compose down

build:
	docker compose build

deploy:        ## git pull + rebuild if needed + migrations + restart
	bash scripts/deploy.sh

hooks:         ## Enables the hook: every `git pull` on main runs scripts/deploy.sh
	git config core.hooksPath .githooks
	@echo "post-merge hook enabled in this clone."

migrate:       ## Applies pending migrations
	docker compose exec backend python manage.py migrate

logs:          ## Logs of all services
	docker compose logs -f --tail=100

ps:
	docker compose ps

import:        ## Imports data/cartas_dbs.json (inserts or updates)
	docker compose exec backend python manage.py import_cards /data/cartas_dbs.json

import-prices: ## Loads prices from data/precios_dbs.json (replaces existing ones)
	docker compose exec backend python manage.py import_prices /data/precios_dbs.json

export-prices: ## Dumps prices to data/precios_dbs.json (the server does it by itself every day)
	docker compose exec backend python manage.py export_prices /data/precios_dbs.json

sync:          ## Queues a Bandai sync (new cards only)
	docker compose exec backend python manage.py sync_cards --async

sync-full:     ## Queues a full sync (downloads all cards again)
	docker compose exec backend python manage.py sync_cards --full --async

test:          ## Backend tests
	docker compose exec backend python manage.py test --noinput

shell:
	docker compose exec backend python manage.py shell

superuser:     ## Creates a user for /admin
	docker compose exec backend python manage.py createsuperuser

psql:
	docker compose exec db psql -U dbs dbs

reset:         ## Deletes the database and Redis!
	docker compose down -v
