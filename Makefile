.PHONY: help install migrate migrations test lint format shell run celery

PYTHON = python
MANAGE = $(PYTHON) manage.py
SETTINGS_DEV = config.settings.dev
SETTINGS_TEST = config.settings.test

help:
	@echo "GrowthPilot — Development Commands"
	@echo ""
	@echo "  make install       Install dev dependencies"
	@echo "  make migrate       Run pending migrations"
	@echo "  make migrations    Create new migrations"
	@echo "  make test          Run test suite"
	@echo "  make lint          Run ruff linter"
	@echo "  make format        Format code with black + isort"
	@echo "  make shell         Open Django shell"
	@echo "  make run           Start dev server"
	@echo "  make celery        Start Celery worker"
	@echo "  make seed          Seed development data"
	@echo "  make check-all     Run lint + type check + tests"

install:
	pip install -r requirements/dev.txt

migrate:
	DJANGO_SETTINGS_MODULE=$(SETTINGS_DEV) $(MANAGE) migrate

migrations:
	DJANGO_SETTINGS_MODULE=$(SETTINGS_DEV) $(MANAGE) makemigrations

test:
	pytest --cov=apps --cov-report=term-missing -v

lint:
	ruff check .

format:
	black .
	isort .

shell:
	DJANGO_SETTINGS_MODULE=$(SETTINGS_DEV) $(MANAGE) shell_plus

run:
	DJANGO_SETTINGS_MODULE=$(SETTINGS_DEV) $(MANAGE) runserver 0.0.0.0:8000

celery:
	celery -A config.celery worker --loglevel=debug --concurrency=2

celery-beat:
	celery -A config.celery beat --loglevel=info --scheduler=django_celery_beat.schedulers:DatabaseScheduler

seed:
	DJANGO_SETTINGS_MODULE=$(SETTINGS_DEV) $(PYTHON) scripts/seed_data.py

check-all: lint
	mypy apps/ config/ core/ --ignore-missing-imports
	pytest --cov=apps -v

generate-key:
	$(PYTHON) -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

superuser:
	DJANGO_SETTINGS_MODULE=$(SETTINGS_DEV) $(MANAGE) createsuperuser
