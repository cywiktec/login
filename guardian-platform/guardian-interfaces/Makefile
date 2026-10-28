.PHONY: install test validate lint clean

PYTHON ?= python3

install:
	$(PYTHON) -m pip install -e .

test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests || [ $$? -eq 5 ]

validate:
	@mkdir -p build/pb
	$(PYTHON) -m grpc_tools.protoc -Iprotobuf --python_out=build/pb protobuf/guardian/v1/guardian.proto
	openapi-spec-validator openapi/guardian.yaml

clean:
	find . -name __pycache__ -prune -exec rm -rf {} +
