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
