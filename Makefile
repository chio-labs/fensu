SHELL := /bin/bash

.PHONY: benchmark benchmark-budget benchmark-profile check check-rust develop-memory develop-native self-check skills test test-e2e test-integration test-memory test-rust test-unit verify

BENCHMARK_PROJECT ?= ../sqlbuild
BENCHMARK_RUNS ?= 5

benchmark:
	uv run python -m scripts.benchmark_check --project "$(BENCHMARK_PROJECT)" --runs "$(BENCHMARK_RUNS)"

benchmark-budget:
	uv run python -m scripts.perfbudget_check

benchmark-profile:
	uv run python -m scripts.benchmark_check --project "$(BENCHMARK_PROJECT)" --profile

check:
	uv run ruff format .
	uv run ruff check --fix .
	uv run ty check src tests scripts
	uv run fensu check
	@command -v cargo >/dev/null && $(MAKE) --no-print-directory check-rust || true

check-rust:
	cargo fmt --check
	cargo clippy --all-targets --quiet -- -D warnings
	cargo run -p fensu-structure-checker --quiet

test-rust:
	cargo test --all --quiet

develop-native:
	uv sync --reinstall-package fensu

develop-memory:
	uvx --from 'maturin[patchelf]>=1.14,<2' maturin develop --release --uv --features extension-module,memory

self-check:
	uv run fensu check

skills:
	uv run fensu skills

test:
	uv run pytest tests -q -n auto

test-unit:
	uv run pytest tests/unit -q -n auto

test-integration:
	uv run pytest tests/integration -q -n auto

test-memory:
	cargo test -p fensu-memory --features sqlite-engine

test-e2e:
	uv run pytest tests/e2e -q -n auto

verify: check test
