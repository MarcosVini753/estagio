PYTHON ?= python
MANAGE := cd backend && $(PYTHON) manage.py

.PHONY: install db-up db-down migrate migrations seed run check test lint format-check

install:
	$(PYTHON) -m pip install -r requirements/dev.txt

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

run:
	$(MANAGE) runserver 0.0.0.0:8000

check:
	$(MANAGE) check
	$(MANAGE) makemigrations --check --dry-run
	$(PYTHON) -m compileall -q backend

test:
	$(MANAGE) test

lint:
	ruff check backend

format-check:
	ruff format --check backend
