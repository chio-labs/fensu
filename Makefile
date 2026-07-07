SHELL := /bin/bash

.PHONY: check test verify

# Bootstrap scaffold: vendored sqlbuild checkers (scripts/checkers/) enforce
# structure on strata's own code — including themselves — until the Phase 6
# self-hosting cutover swaps this body to `uv run strata check src/strata`.
check:
	uv run ruff format .
	uv run ruff check --fix .
	uv run ty check src tests
	uv run python scripts/checkers/structure/check_structure_conventions.py src/strata scripts
	uv run python scripts/checkers/testing/check_test_conventions.py tests
	uv run python scripts/checkers/type_annotations/check_type_annotation_conventions.py src tests

test:
	uv run pytest tests -q

verify: check test
