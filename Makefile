.PHONY: install backups seed up down build logs ps deploy hooks migrate import import-prices export-prices sync sync-full test shell superuser psql reset

install:       ## Instala todo en un paso (.env, servicios, catálogo y precios, admin). En un servidor: make install SERVER=<ip>
	bash scripts/install.sh $(if $(SERVER),--server $(SERVER))

backups:       ## En el servidor: instala las copias de seguridad diarias (systemd; pide sudo)
	bash scripts/systemd/install.sh

seed:          ## Rehace data/seed/ (catálogo y precios del repo) con los datos de esta instalación
	docker compose exec backend python manage.py export_cards /data/seed/cartas_dbs.json.gz
	docker compose exec backend python manage.py export_prices /data/seed/precios_dbs.json.gz

up:            ## Levanta todo en segundo plano
	docker compose up -d --build

down:          ## Para los contenedores (los datos se conservan)
	docker compose down

build:
	docker compose build

deploy:        ## git pull + rebuild si hace falta + migraciones + reinicio
	bash scripts/deploy.sh

hooks:         ## Activa el hook: cada `git pull` en main ejecuta scripts/deploy.sh
	git config core.hooksPath .githooks
	@echo "Hook post-merge activado en este clon."

migrate:       ## Aplica migraciones pendientes
	docker compose exec backend python manage.py migrate

logs:          ## Logs de todos los servicios
	docker compose logs -f --tail=100

ps:
	docker compose ps

import:        ## Importa data/cartas_dbs.json (inserta o actualiza)
	docker compose exec backend python manage.py import_cards /data/cartas_dbs.json

import-prices: ## Carga los precios de data/precios_dbs.json (sustituye los que haya)
	docker compose exec backend python manage.py import_prices /data/precios_dbs.json

export-prices: ## Vuelca los precios a data/precios_dbs.json (el servidor lo hace solo cada día)
	docker compose exec backend python manage.py export_prices /data/precios_dbs.json

sync:          ## Encola un sync con Bandai (solo cartas nuevas)
	docker compose exec backend python manage.py sync_cards --async

sync-full:     ## Encola un sync completo (vuelve a descargar todas)
	docker compose exec backend python manage.py sync_cards --full --async

test:          ## Tests del backend
	docker compose exec backend python manage.py test --noinput

shell:
	docker compose exec backend python manage.py shell

superuser:     ## Crea un usuario para /admin
	docker compose exec backend python manage.py createsuperuser

psql:
	docker compose exec db psql -U dbs dbs

reset:         ## ¡Borra la base de datos y Redis!
	docker compose down -v
