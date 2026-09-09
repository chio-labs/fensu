SHELL := /bin/bash

.PHONY: benchmark benchmark-budget benchmark-profile catalogue-check catalogue-generate check check-ci check-rust develop-native native-corpus-generate self-check skills skills-content-check test test-e2e test-integration test-rust test-unit verify

BENCHMARK_PROJECT ?= ../sqlbuild
BENCHMARK_RUNS ?= 5

benchmark:
	uv run python -m scripts.benchmark_check --project "$(BENCHMARK_PROJECT)" --runs "$(BENCHMARK_RUNS)"

benchmark-budget:
	uv run python -m scripts.perfbudget_check

benchmark-profile:
	uv run python -m scripts.benchmark_check --project "$(BENCHMARK_PROJECT)" --profile

catalogue-check:
	uv run python -m scripts.catalogue_generate --check

catalogue-generate:
	uv run python -m scripts.catalogue_generate

check: catalogue-check
	uv run ruff format .
	uv run ruff check --fix .
	uv run ty check src tests scripts
	@if command -v cargo >/dev/null; then uv run fensu check; else uv run fensu check --target python; fi
	@command -v cargo >/dev/null && $(MAKE) --no-print-directory check-rust || true

check-ci: catalogue-check
	uv run ruff format --check .
	uv run ruff check .
	uv run ty check src tests scripts
	uv run fensu check
	$(MAKE) --no-print-directory check-rust

check-rust:
	cargo fmt --check
	cargo clippy --all-targets --quiet -- -D warnings
	cargo run -p fensu-structure-checker --quiet -- --config rust-structure-checker.toml

test-rust:
	cargo test --all --quiet

develop-native:
	uv sync --reinstall-package fensu

native-corpus-generate:
	PYTHONPATH=. FENSU_CORE_FIXTURE_OUTPUT=crates/fensu-native/tests/rules/fixtures/generated_rules.jsonl uv run pytest tests/unit/src/fensu/rules tests/integration/src/fensu/rules -q -n 0 -p scripts.native_corpus._helpers.capture_plugin

self-check:
	uv run fensu check

skills:
	uv run fensu skills

skills-content-check:
	cargo test -p fensu-cli --test skills --quiet

test:
	uv run pytest tests -q -n auto

test-unit:
	uv run pytest tests/unit -q -n auto

test-integration:
	uv run pytest tests/integration -q -n auto

test-e2e:
	uv run pytest tests/e2e -q -n auto

verify: check-ci test
