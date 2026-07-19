"""Select one function from an in-memory project index."""

from fensu.mapping.constants import (
    PATH_SYMBOL_SEPARATOR,
    POSIX_PATH_SEPARATOR,
    QUALIFIED_NAME_SEPARATOR,
    WINDOWS_PATH_SEPARATOR,
)
from fensu.mapping.exceptions import MapError
from fensu.mapping.models import FunctionDefinition


def select_mapping_function(
    *, definitions: dict[str, FunctionDefinition], symbol: str
) -> FunctionDefinition:
    """Select one bare, dotted, or path-qualified function."""

    if PATH_SYMBOL_SEPARATOR in symbol:
        path_fragment, function_name = symbol.rsplit(PATH_SYMBOL_SEPARATOR, maxsplit=1)
        normalized_fragment: str = path_fragment.replace(
            WINDOWS_PATH_SEPARATOR, POSIX_PATH_SEPARATOR
        ).removesuffix(".py")
        matches: tuple[FunctionDefinition, ...] = tuple(
            definition
            for definition in definitions.values()
            if definition.qualified_name == function_name
            and definition.path.as_posix().removesuffix(".py").endswith(normalized_fragment)
        )
    elif symbol in definitions:
        return definitions[symbol]
    elif QUALIFIED_NAME_SEPARATOR in symbol:
        matches = tuple(
            definition for definition in definitions.values() if definition.qualified_name == symbol
        )
    else:
        matches = tuple(
            definition for definition in definitions.values() if definition.name == symbol
        )
    if len(matches) == 1:
        return matches[0]
    if not matches:
        hint: str = (
            f" Use a full dotted key or path::{symbol}."
            if QUALIFIED_NAME_SEPARATOR in symbol
            else ""
        )
        raise MapError(f"Unknown project function: {symbol}.{hint}")
    choices: str = ", ".join(sorted(definition.key for definition in matches))
    raise MapError(
        f"Ambiguous function {symbol}; choose a full dotted key: {choices}; "
        f"or use path::{symbol if QUALIFIED_NAME_SEPARATOR in symbol else 'Class.method'}"
    )
