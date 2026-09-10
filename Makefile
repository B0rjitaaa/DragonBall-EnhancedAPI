.PHONY: up down build logs ps import sync sync-full test shell superuser psql reset

up:            ## Levanta todo en segundo plano
	docker compose up -d --build

down:          ## Para los contenedores (los datos se conservan)
	docker compose down

build:
	docker compose build

logs:          ## Logs de todos los servicios
	docker compose logs -f --tail=100

ps:
	docker compose ps

import:        ## Importa data/cartas_dbs.json (inserta o actualiza)
	docker compose exec backend python manage.py import_cards /data/cartas_dbs.json

sync:          ## Encola un sync con Bandai (solo cartas nuevas)
	docker compose exec backend python manage.py sync_cards --async

sync-full:     ## Encola un sync completo (vuelve a descargar todas)
	docker compose exec backend python manage.py sync_cards --full --async

test:          ## Tests del backend
	docker compose exec backend python manage.py test cards

shell:
	docker compose exec backend python manage.py shell

superuser:     ## Crea un usuario para /admin
	docker compose exec backend python manage.py createsuperuser

psql:
	docker compose exec db psql -U dbs dbs

reset:         ## ¡Borra la base de datos y Redis!
	docker compose down -v
