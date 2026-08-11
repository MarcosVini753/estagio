PYTHON ?= python
NPM ?= npm
MANAGE := cd backend && $(PYTHON) manage.py

.PHONY: install db-up db-down migrate migrations seed seed-reports run check test lint format-check frontend-build frontend-check frontend-e2e

install:
	$(PYTHON) -m pip install -r requirements/dev.txt
	$(NPM) ci
	$(NPM) run build

db-up:
	docker compose up -d db

db-down:
	docker compose down

migrate:
	$(MANAGE) migrate

migrations:
	$(MANAGE) makemigrations

seed:
	$(MANAGE) seed_demo_data

seed-reports:
	$(MANAGE) seed_report_demo_data --reset

run:
	$(MANAGE) runserver 0.0.0.0:8000

check:
	$(MANAGE) check
	$(MANAGE) makemigrations --check --dry-run
	$(PYTHON) -m compileall -q backend
	$(NPM) run check:frontend

test:
	$(MANAGE) test

lint:
	$(PYTHON) -m ruff check backend

format-check:
	$(PYTHON) -m ruff format --check backend

frontend-build:
	$(NPM) run build

frontend-check:
	$(NPM) run check:frontend

frontend-e2e:
	$(NPM) run test:e2e
