PYTHON ?= .venv/bin/python

.PHONY: install format check test clean

install:
	python3 -m venv .venv
	$(PYTHON) -m pip install -q --upgrade pip
	$(PYTHON) -m pip install -q -e . --group dev
	.venv/bin/pre-commit install

format:
	$(PYTHON) -m ruff format .
	$(PYTHON) -m ruff check --fix .

check:
	$(PYTHON) -m ruff format --check .
	$(PYTHON) -m ruff check .
	$(PYTHON) -m mypy
	$(PYTHON) -m pytest -q

test:
	$(PYTHON) -m pytest -q

clean:
	rm -rf build src/*.egg-info .pytest_cache .mypy_cache .ruff_cache
	find . -name __pycache__ -not -path "./.venv/*" -exec rm -rf {} +
