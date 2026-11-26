.DEFAULT_GOAL := help

UV ?= uv

.PHONY: help setup run install uninstall screenshot test lint format clean

help: ## List the available commands
	@awk 'BEGIN { FS = ":.*##" } /^[a-zA-Z0-9_-]+:.*##/ { printf "  %-12s %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

setup: ## Create the venv (it must see the system PyGObject), sync the dependencies and install the pre-commit hook
	$(UV) venv --system-site-packages --python /usr/bin/python3 --allow-existing
	$(UV) sync --extra dev
	$(UV) run --extra dev pre-commit install

run: ## Start the launcher from this checkout (run it again to close it)
	/usr/bin/python3 src/lupa.py

install: ## Install the command and the Super+Space shortcut (Cinnamon)
	./install.sh

uninstall: ## Remove the command and the shortcut
	./uninstall.sh

screenshot: ## Regenerate the screenshots of the README (needs a display)
	/usr/bin/python3 tools/screenshot.py

test: ## Run the tests, at 100% coverage
	$(UV) run --extra dev pytest -q

lint: ## Run every pre-commit hook on all files, as CI does
	$(UV) run --extra dev pre-commit run --all-files --show-diff-on-failure

format: ## Fix lint issues and format the code with ruff
	$(UV) run --extra dev ruff check --fix .
	$(UV) run --extra dev ruff format .

clean: ## Remove the test and lint caches
	rm -rf .pytest_cache .ruff_cache .coverage coverage.xml
