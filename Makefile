PYTHON := .venv/bin/python
PIP := .venv/bin/pip
UVICORN := .venv/bin/uvicorn
PYTEST := .venv/bin/pytest

.PHONY: all setup load-data train serve test acceptance clean

all: setup load-data train test

setup:
	python3 -m venv .venv
	$(PIP) install -r requirements.txt

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

clean:
	rm -rf __pycache__ .pytest_cache ml/models/*.joblib generated_reports/*
