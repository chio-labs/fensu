#!/usr/bin/env bash
set -euo pipefail

package_root="$(mktemp -d)"
consumer_root="$(mktemp -d)"
trap 'rm -rf "${package_root}" "${consumer_root}"' EXIT

version="$(cargo +1.85.0 metadata --locked --no-deps --format-version 1 \
  | jq -r '.packages[] | select(.name == "fensu-policy") | .version')"

CARGO_TARGET_DIR="${package_root}" cargo +1.85.0 package --locked -p fensu-policy

cargo +stable new --quiet --lib "${consumer_root}/consumer"
cargo +stable add --quiet --manifest-path "${consumer_root}/consumer/Cargo.toml" \
  --path "${package_root}/package/fensu-policy-${version}"
cargo +1.85.0 check --locked --manifest-path "${consumer_root}/consumer/Cargo.toml"
