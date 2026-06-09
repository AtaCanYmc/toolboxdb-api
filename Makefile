VENV=.venv
PY=$(VENV)/bin/python
PIP=$(VENV)/bin/pip

.PHONY: init install run lint test format clean

init:
	python3.11 -m venv $(VENV)

install: init
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

run: install
	$(VENV)/bin/uvicorn main:app --reload

lint:
	$(VENV)/bin/black --check .
	$(VENV)/bin/flake8 src tests

format:
	$(VENV)/bin/black .

test: install
	$(VENV)/bin/pytest -q

clean:
	rm -rf $(VENV) __pycache__
