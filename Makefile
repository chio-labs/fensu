SHELL := /bin/bash

.PHONY: check self-check test verify

# Keep the bootstrap checkers active alongside Strata until their removal is
# explicitly approved after the self-hosting behavior has been demonstrated.
check:
	uv run ruff format .
	uv run ruff check --fix .
	uv run ty check src tests
	uv run python scripts/checkers/structure/check_structure_conventions.py src/strata scripts
	uv run python scripts/checkers/testing/check_test_conventions.py tests
	uv run python scripts/checkers/type_annotations/check_type_annotation_conventions.py src tests
	uv run strata check

self-check:
	uv run strata check

test:
	uv run pytest tests -q -n auto

verify: check test
