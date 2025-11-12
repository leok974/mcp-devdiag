VENV=.venv
PY=$(VENV)/bin/python

venv:
	python -m venv $(VENV)
	$(PY) -m pip install -U pip
	$(PY) -m pip install -e .
	$(PY) -m pip install -r requirements-dev.txt

lint:
	$(VENV)/bin/ruff check .
	$(VENV)/bin/ruff format --check .

typecheck:
	$(VENV)/bin/mypy mcp_devdiag

test:
	$(VENV)/bin/pytest

mcp:
	$(VENV)/bin/mcp-devdiag --stdio

# PostgreSQL targets
.PHONY: postgres.start
postgres.start:
	docker compose -f deployments/postgres.devdiag.yml up -d

.PHONY: postgres.stop
postgres.stop:
	docker compose -f deployments/postgres.devdiag.yml down

.PHONY: postgres.psql
postgres.psql:
	docker exec -it devdiag-postgres psql -U devdiag -d devdiag

.PHONY: postgres.backup
postgres.backup:
	./deployments/backup.sh

.PHONY: postgres.cleanup
postgres.cleanup:
	docker exec -i devdiag-postgres psql -U devdiag -d devdiag -f /dev/stdin < deployments/retention-cleanup.sql

# Grafana targets
.PHONY: grafana.import
grafana.import:
	chmod +x scripts/grafana/*.sh
	./scripts/grafana/import-datasource.sh
	./scripts/grafana/import-dashboard.sh deployments/grafana/dashboards/devdiag-analytics.json

.PHONY: grafana.datasource
grafana.datasource:
	chmod +x scripts/grafana/import-datasource.sh
	./scripts/grafana/import-datasource.sh

.PHONY: grafana.dashboard
grafana.dashboard:
	chmod +x scripts/grafana/import-dashboard.sh
	./scripts/grafana/import-dashboard.sh deployments/grafana/dashboards/devdiag-analytics.json

# DevDiag HTTP Server targets
.PHONY: devdiag-up devdiag-down devdiag-selfcheck devdiag-ready devdiag-probe devdiag-logs devdiag-test devdiag-clean

devdiag-up:
	docker compose -f docker-compose.devdiag.yml up -d --build
	@echo "Waiting for server to be ready..."
	@for i in {1..20}; do curl -fsS http://127.0.0.1:8080/healthz > /dev/null 2>&1 && break || sleep 1; done
	@echo "✅ DevDiag HTTP server is up"

devdiag-down:
	docker compose -f docker-compose.devdiag.yml down

devdiag-selfcheck:
	@echo "🔍 DevDiag Selfcheck:"
	@curl -s http://127.0.0.1:8080/selfcheck | jq .

devdiag-ready:
	@echo "✅ DevDiag Readiness:"
	@curl -s http://127.0.0.1:8080/ready | jq .

devdiag-probe:
	@echo "🌐 Running diagnostic probe:"
	@curl -s -X POST http://127.0.0.1:8080/diag/run \
		-H 'content-type: application/json' \
		-d '{"url":"https://app.ledger-mind.org","preset":"app"}' | jq .

devdiag-logs:
	docker compose -f docker-compose.devdiag.yml logs -f

devdiag-test: devdiag-up
	@echo "Running smoke tests..."
	@sleep 2
	@make devdiag-selfcheck
	@make devdiag-ready
	@make devdiag-probe

devdiag-clean: devdiag-down
	docker rmi devdiag-http:latest || true
