"""Core catalogue asset paths."""

from pathlib import Path

CATALOGUE_ASSET_PATH: Path = Path("crates/fensu-cli/assets/catalogue.json")
NATIVE_POLICY_PATH: Path = Path("crates/fensu-native/src/rules/_helpers/policy/generated_policy.rs")
CLI_DEFAULTS_PATH: Path = Path("crates/fensu-cli/src/configuration/constants.rs")
CHECK_ARGUMENTS: tuple[str, ...] = ("--check",)
WRITE_ARGUMENTS: tuple[str, ...] = ("--write",)
