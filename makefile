VENV := venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

.PHONY: setup run clear init commit push clean

setup:
	python3 -m venv $(VENV)
	$(PIP) install -r requirements.txt
	@if [ ! -f config.yaml ]; then cp config.example.yaml config.yaml; echo "created config.yaml - edit it before running"; fi
	@if [ ! -f .env ]; then echo "GITHUB_TOKEN=" > .env; echo "created .env - put your token in it before running"; fi

run:
	$(PYTHON) -m app.main

init:
	$(PYTHON) -m app.core.repo_init

commit:
	$(PYTHON) -m app.core.repo_commit

push:
	$(PYTHON) -m app.core.repo_push

clear:
	$(PYTHON) -m app.utils._clear

clean:
	rm -rf $(VENV) gh_backup.log gh_backup.log.*
	find . -type d -name "__pycache__" -exec rm -rf {} +