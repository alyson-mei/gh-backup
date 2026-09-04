VENV := venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
PID_FILE := .app.pid
BIN_DIR := $(HOME)/.local/bin
BIN := $(BIN_DIR)/gh-backup

AUTOSTART_DIR := $(HOME)/.config/autostart
DESKTOP_FILE := $(AUTOSTART_DIR)/gh-backup.desktop

.PHONY: setup run login stop status autostart autostart-off init commit push clear clean uninstall

setup:
	python3 -m venv $(VENV)
	$(PYTHON) -m pip install -r requirements.txt
	@if [ ! -f config.yaml ]; then \
		cp app/resources/config_example.yaml config.yaml; \
		echo "created config.yaml from example"; \
	else \
		echo "config.yaml already exists, skipping overwrite"; \
	fi
	@if [ ! -f .env ]; then \
		printf '%s\n' 'GITHUB_TOKEN=' > .env; \
		echo "created .env - run 'gh-backup login' or put your token manually"; \
	fi
	@mkdir -p $(BIN_DIR)
	@printf '%s\n' \
		'#!/usr/bin/env bash' \
		'case "$$1" in' \
		'  -q|--quiet)' \
		'    make --no-print-directory -C "$(CURDIR)" run q=1 ;;' \
		'  login|stop|status|autostart|autostart-off|clear|clean)' \
		'    make --no-print-directory -C "$(CURDIR)" "$$1" ;;' \
		'  *)' \
		'    make --no-print-directory -C "$(CURDIR)" run ;;' \
		'esac' > $(BIN)
	@chmod +x $(BIN)
	@echo "installed CLI command: $(BIN)"

login:
	$(PYTHON) -m app.core.auth

run:
	@if [ "$(q)" = "1" ] || [ "$(quiet)" = "1" ]; then \
		if [ -f $(PID_FILE) ] && kill -0 $$(cat $(PID_FILE)) 2>/dev/null && grep -q "app.main" /proc/$$(cat $(PID_FILE))/cmdline 2>/dev/null; then \
			echo "already running (PID: $$(cat $(PID_FILE)))"; \
		else \
			nohup $(PYTHON) -m app.main > /dev/null 2>&1 & echo $$! > $(PID_FILE); \
			echo "started in background (PID: $$(cat $(PID_FILE)))"; \
		fi \
	else \
		$(PYTHON) -m app.main; \
	fi

stop:
	@if [ -f $(PID_FILE) ]; then \
		PID=$$(cat $(PID_FILE)); \
		if kill -0 $$PID 2>/dev/null && grep -q "app.main" /proc/$$PID/cmdline 2>/dev/null; then \
			kill $$PID; \
			printf "stopping process $$PID (waiting for graceful finish)"; \
			while kill -0 $$PID 2>/dev/null; do \
				sleep 0.5; \
				printf "."; \
			done; \
			rm -f $(PID_FILE); \
			echo " stopped."; \
		else \
			echo "process not active (stale PID file cleaned)"; \
			rm -f $(PID_FILE); \
		fi \
	else \
		echo "not running"; \
	fi

status:
	@if [ -f $(PID_FILE) ]; then \
		PID=$$(cat $(PID_FILE)); \
		if kill -0 $$PID 2>/dev/null && grep -q "app.main" /proc/$$PID/cmdline 2>/dev/null; then \
			echo "running (PID: $$PID)"; \
		else \
			echo "stale PID file found (process dead)"; \
			rm -f $(PID_FILE) 2>/dev/null; \
		fi \
	else \
		echo "not running"; \
	fi

autostart:
	@mkdir -p $(AUTOSTART_DIR)
	@printf '%s\n' \
		'[Desktop Entry]' \
		'Type=Application' \
		'Name=GitHub Backup' \
		'Comment=Vaults automatic git backup tool' \
		'Exec=$(BIN) -q' \
		'Terminal=false' \
		'Hidden=false' \
		'X-GNOME-Autostart-enabled=true' > $(DESKTOP_FILE)
	@echo "autostart enabled: $(DESKTOP_FILE)"

autostart-off:
	@rm -f $(DESKTOP_FILE)
	@echo "autostart disabled (removed $(DESKTOP_FILE))"

init:
	$(PYTHON) -m app.core.repo_init

commit:
	$(PYTHON) -m app.core.repo_commit

push:
	$(PYTHON) -m app.core.repo_push

clear:
	$(PYTHON) -m app.utils._clear

clean:
	rm -rf $(VENV) gh_backup.log gh_backup.log.* $(PID_FILE)
	find . -type d -name "__pycache__" -exec rm -rf {} +

uninstall: clean
	rm -f $(BIN) $(DESKTOP_FILE)
	@echo "removed $(BIN) and autostart entry"