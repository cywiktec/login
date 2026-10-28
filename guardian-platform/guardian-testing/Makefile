.PHONY: install test lint clean

PYTHON ?= python3

install:
	$(PYTHON) -m pip install -e .

test:
	PYTHONPATH=src:$$(ls -d ../*/src | tr '\n' ':') $(PYTHON) -m unittest discover -s tests || [ $$? -eq 5 ]

clean:
	find . -name __pycache__ -prune -exec rm -rf {} +
