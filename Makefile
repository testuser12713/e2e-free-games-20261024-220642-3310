# Free games scraper - developer commands (run from the repository root).
#   make install   install backend and frontend dependencies
#   make dev       start API (uvicorn) and web frontend (Vite) together
#   make seed      load the demo deals into the database
#   make refresh   run every source adapter once (synchronously)
#   make test      run all tests (pytest + vitest), no network needed

PYTHON ?= $(shell command -v python3 >/dev/null 2>&1 && echo python3 || echo python)
API_PORT ?= 8000
WEB_PORT ?= 5173
VITE_API_BASE_URL ?= http://localhost:$(API_PORT)
CORS_ORIGINS ?= http://localhost:$(WEB_PORT),http://127.0.0.1:$(WEB_PORT)

.PHONY: install dev seed refresh test

install:
	cd backend && $(PYTHON) -m pip install -r requirements.txt
	@if [ -d frontend ]; then \
		cd frontend && if [ -f package-lock.json ]; then npm ci; else npm install; fi; \
	fi

dev:
	@trap 'kill 0' INT TERM EXIT; \
	(cd backend && CORS_ORIGINS="$(CORS_ORIGINS)" $(PYTHON) -m uvicorn app.main:app \
		--host 127.0.0.1 --port $(API_PORT) --no-access-log) & \
	if [ -d frontend ]; then \
		(cd frontend && VITE_API_BASE_URL="$(VITE_API_BASE_URL)" npm run dev -- --port $(WEB_PORT)) & \
	fi; \
	wait

seed:
	cd backend && $(PYTHON) -m app.seed

refresh:
	cd backend && $(PYTHON) -m app.cli refresh

test:
	cd backend && $(PYTHON) -m pytest
	@if [ -d frontend ]; then cd frontend && npm test; fi
