"""Persistent cache semantic fingerprint constants."""

EVALUATION_FINGERPRINT_CONTRACT_VERSION: int = 1
FILE_RESULT_FINGERPRINT_DOMAIN: bytes = b"fensu-file-result-v2\0"
BYTECODE_SUFFIX: str = ".pyc"
PYTHON_SOURCE_SUFFIX: str = ".py"
PYTHON_CACHE_DIRECTORY_NAME: str = "__pycache__"
NATIVE_MODULE_SUFFIXES: tuple[str, ...] = (".so", ".pyd")
PACKAGE_INIT_FILE_NAME: str = "__init__.py"
