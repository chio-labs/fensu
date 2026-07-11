"""Persistent cache semantic fingerprint constants."""

EVALUATION_FINGERPRINT_CONTRACT_VERSION: int = 1
BYTECODE_SUFFIX: str = ".pyc"
PYTHON_SOURCE_SUFFIX: str = ".py"
PYTHON_CACHE_DIRECTORY_NAME: str = "__pycache__"
NATIVE_MODULE_SUFFIXES: tuple[str, ...] = (".so", ".pyd")
