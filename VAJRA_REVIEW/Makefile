PYTHON := python3
PIP := pip3
UVICORN := uvicorn
PYTEST := pytest

# Auto-detect virtual environment if present
ifneq ("$(wildcard .venv/bin/python)","")
    PYTHON := .venv/bin/python
    PIP := .venv/bin/pip
    UVICORN := .venv/bin/uvicorn
    PYTEST := .venv/bin/pytest
endif

.PHONY: all setup load-data train serve test acceptance twin-test clean help

help:
	@echo "VAJRA Fleet Maintenance & Availability Platform (SIH 2026 - PS 26249)"
	@echo ""
	@echo "Available commands:"
	@echo "  make setup       Create .venv and install all dependencies"
	@echo "  make load-data   Initialize SQLite DB and load normalized CSVs"
	@echo "  make train       Train and evaluate XGBoost & Random Forest RUL models"
	@echo "  make serve       Start FastAPI application on http://localhost:8000"
	@echo "  make test        Execute automated test suite (34 unit & integration tests)"
	@echo "  make acceptance  Run full end-to-end acceptance verification (6 criteria)"
	@echo "  make twin-test   Run 3D Digital Twin exhaustive test suite (53 controls)"
	@echo "  make clean       Clean temporary caches and artifacts"

all: setup load-data train test

setup:
	$(PYTHON) -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r requirements.txt

load-data:
	PYTHONPATH=. $(PYTHON) backend/scripts/load_data.py

train:
	PYTHONPATH=. $(PYTHON) ml/train.py

serve:
	PYTHONPATH=. $(UVICORN) backend.app.main:app --host 0.0.0.0 --port 8000 --reload

test:
	PYTHONPATH=. $(PYTEST) tests/ -v

acceptance:
	PYTHONPATH=. $(PYTHON) scripts/acceptance_test.py

twin-test:
	PYTHONPATH=. $(PYTHON) scripts/test_3d_twin_screen.py

clean:
	rm -rf __pycache__ .pytest_cache generated_reports/*
