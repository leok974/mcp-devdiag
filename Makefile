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
