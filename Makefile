SHELL := /bin/bash

.PHONY: check self-check test verify

check:
	uv run ruff format .
	uv run ruff check --fix .
	uv run ty check src tests
	uv run strata check

self-check:
	uv run strata check

test:
	uv run pytest tests -q -n auto

verify: check test
