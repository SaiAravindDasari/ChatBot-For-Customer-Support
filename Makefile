.PHONY: install dev test lint clean docker docker-up docker-down setup help

# Default target
help: ## Show this help message
	@echo.
	@echo   QueryDesk - Enterprise AI Customer Support Platform
	@echo   ===================================================
	@echo.
	@echo   make install     Install Python dependencies
	@echo   make setup       Run first-time setup (NLTK, SpaCy, DB init)
	@echo   make dev         Start development server with hot-reload
	@echo   make test        Run full test suite (150+ tests)
	@echo   make lint        Run flake8 lint checks
	@echo   make clean       Remove caches, bytecode, and temp files
	@echo   make docker      Build production Docker image
	@echo   make docker-up   Start with docker-compose (API + Nginx)
	@echo   make docker-down Stop docker-compose stack
	@echo.

install: ## Install all Python dependencies
	pip install -r requirements.txt

setup: install ## First-time setup: download models, init database
	python setup.py

dev: ## Start development server with hot-reload on port 5000
	uvicorn backend.app:app --reload --host 127.0.0.1 --port 5000

test: ## Run the full pytest suite
	python -m pytest tests/ -v

lint: ## Run flake8 syntax and style checks
	flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics

clean: ## Remove Python bytecode, caches, and temp files
	@if exist __pycache__ rd /s /q __pycache__
	@if exist .pytest_cache rd /s /q .pytest_cache
	@if exist backend\__pycache__ rd /s /q backend\__pycache__
	@for /d %%d in (backend\*\__pycache__) do @rd /s /q "%%d" 2>nul
	@for /d %%d in (tests\__pycache__) do @rd /s /q "%%d" 2>nul
	@echo Cleaned.

docker: ## Build production Docker image
	docker build -t querydesk:latest .

docker-up: ## Start the full stack with docker-compose
	docker-compose up -d --build

docker-down: ## Stop the docker-compose stack
	docker-compose down
