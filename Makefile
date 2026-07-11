SHELL := /bin/bash

.PHONY: benchmark benchmark-profile check self-check skills test test-e2e test-integration test-unit verify

BENCHMARK_PROJECT ?= ../sqlbuild
BENCHMARK_RUNS ?= 5

benchmark:
	uv run python -m scripts.benchmark_check --project "$(BENCHMARK_PROJECT)" --runs "$(BENCHMARK_RUNS)"

benchmark-profile:
	uv run python -m scripts.benchmark_check --project "$(BENCHMARK_PROJECT)" --profile

check:
	uv run ruff format .
	uv run ruff check --fix .
	uv run ty check src tests scripts
	uv run strata check

self-check:
	uv run strata check

skills:
	uv run strata skills update

test:
	uv run pytest tests -q -n auto

test-unit:
	uv run pytest tests/unit -q -n auto

test-integration:
	uv run pytest tests/integration -q -n auto

test-e2e:
	uv run pytest tests/e2e -q -n auto

verify: check test
