VENV = .venv
PYTHON = $(VENV)/bin/python
MAIN = fly_in.py
MAP ?= maps/easy/01_linear_path.txt

install:
	python3 -m venv $(VENV)
	$(PYTHON) -m pip install flake8 mypy

run:
	$(PYTHON) $(MAIN) $(MAP)

debug:
	$(PYTHON) -m pdb $(MAIN) $(MAP)

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf .mypy_cache .pytest_cache

lint:
	$(PYTHON) -m flake8 .
	$(PYTHON) -m mypy . --warn-return-any --warn-unused-ignores \
		--ignore-missing-imports --disallow-untyped-defs \
		--check-untyped-defs

lint-strict:
	$(PYTHON) -m flake8 .
	$(PYTHON) -m mypy . --strict

.PHONY: install run debug clean lint lint-strict