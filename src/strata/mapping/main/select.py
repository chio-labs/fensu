"""Select one function from an in-memory project index."""

from strata.mapping._helpers.index import select_function
from strata.mapping.models import FunctionDefinition


def select_mapping_function(
    *, definitions: dict[str, FunctionDefinition], symbol: str
) -> FunctionDefinition:
    """Select one bare, dotted, or path-qualified function."""

    return select_function(definitions=definitions, symbol=symbol)
