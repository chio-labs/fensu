"""Call-map models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class MappingSource:
    """A directory to scan and the import root used to name its modules."""

    scan_path: Path
    import_root: Path


@dataclass(frozen=True, slots=True)
class MappingProject:
    """Repository display root and Python sources included in one map."""

    repo_root: Path
    sources: tuple[MappingSource, ...]
    cache_enabled: bool = True


@dataclass(frozen=True, slots=True)
class SourceSnapshot:
    """One discovered Python source and its exact invocation-local contents."""

    path: Path
    relative_path: str
    import_root: Path
    import_root_identity: str
    module_name: str
    source: bytes
    source_fingerprint: str


@dataclass(frozen=True, slots=True)
class ImportView:
    """Symbols and module aliases visible in one import context."""

    symbols: dict[str, tuple[str, str]]
    modules: dict[str, str]


@dataclass(frozen=True, slots=True)
class ModuleImports:
    """Separate executable and annotation import contexts."""

    runtime: ImportView
    annotation: ImportView


@dataclass(frozen=True, slots=True)
class MappingExpression:
    """A compact native expression projection used by map tree policy."""

    kind: str
    spelling: str
    parts: tuple[str, ...]
    child: MappingExpression | None = None
    string_value: str | None = None

    @property
    def name(self) -> str:
        """Return the terminal static name when one is available."""

        if self.parts:
            return self.parts[-1]
        return self.spelling.rsplit(".", maxsplit=1)[-1]


@dataclass(frozen=True, slots=True)
class MappingParameter:
    """One function parameter and its optional annotation."""

    name: str
    annotation: MappingExpression | None


@dataclass(frozen=True, slots=True)
class MappingCall:
    """One function-owned call in native traversal order."""

    callee: MappingExpression
    line: int


@dataclass(frozen=True, slots=True)
class MappingStatement:
    """Receiver-binding and call facts for one direct function statement."""

    control_flow: bool
    assigned_names: frozenset[str]
    binding_name: str | None
    binding_annotation: MappingExpression | None
    binding_value: MappingExpression | None
    calls: tuple[MappingCall, ...]


@dataclass(frozen=True, slots=True)
class FunctionSyntax:
    """Native map facts owned by one function declaration."""

    line: int
    parameters: tuple[MappingParameter, ...]
    returns: MappingExpression | None
    statements: tuple[MappingStatement, ...]

    @property
    def calls(self) -> tuple[MappingCall, ...]:
        """Return all owned calls in source-compatible traversal order."""

        calls: list[MappingCall] = []
        for statement in self.statements:
            calls.extend(statement.calls)
        return tuple(calls)


@dataclass(frozen=True, slots=True)
class ClassReference:
    """A class expression and the import context that owns it."""

    expression: MappingExpression
    annotation: bool


@dataclass(frozen=True, slots=True)
class FunctionDefinition:
    """A project-owned function or direct class method definition."""

    module_name: str
    name: str
    path: Path
    syntax: FunctionSyntax
    imports: ModuleImports
    owning_class: str | None = None

    @property
    def qualified_name(self) -> str:
        """Return the class-qualified name when this callable is a method."""

        return self.qualify(name=self.name, owning_class=self.owning_class)

    @property
    def canonical_key(self) -> str:
        """Return the unique project key for this callable."""

        return self.build_key(
            module_name=self.module_name,
            name=self.name,
            owning_class=self.owning_class,
        )

    @property
    def key(self) -> str:
        """Return the canonical callable identity."""

        return self.canonical_key

    @property
    def display_name(self) -> str:
        """Return the stable name rendered in a call map."""

        return self.qualified_name

    @staticmethod
    def qualify(*, name: str, owning_class: str | None = None) -> str:
        """Build one class-qualified callable name."""

        if owning_class is None:
            return name
        return f"{owning_class}.{name}"

    @classmethod
    def build_key(cls, *, module_name: str, name: str, owning_class: str | None = None) -> str:
        """Build one canonical callable key."""

        return f"{module_name}.{cls.qualify(name=name, owning_class=owning_class)}"


@dataclass(frozen=True, slots=True)
class ClassDefinition:
    """A project-owned top-level class and its direct static type facts."""

    module_name: str
    name: str
    path: Path
    imports: ModuleImports
    bases: tuple[MappingExpression, ...]
    base_keys: tuple[str, ...]
    protocol: bool
    class_attributes: dict[str, ClassReference]
    instance_attributes: dict[str, ClassReference]

    @property
    def canonical_key(self) -> str:
        """Return the unique project key for this class."""

        return self.build_key(module_name=self.module_name, name=self.name)

    @property
    def key(self) -> str:
        """Return the canonical class identity."""

        return self.canonical_key

    @staticmethod
    def build_key(*, module_name: str, name: str) -> str:
        """Build one canonical class key."""

        return f"{module_name}.{name}"


@dataclass(frozen=True, slots=True)
class ProjectIndex:
    """Parsed project classes and callables keyed by canonical identity."""

    functions: dict[str, FunctionDefinition]
    classes: dict[str, ClassDefinition]
    protocol_implementations: dict[str, tuple[str, ...]]

    def get_function(self, key: str) -> FunctionDefinition | None:
        """Return one function by canonical key."""

        return self.functions.get(key)

    def get_class(self, key: str) -> ClassDefinition | None:
        """Return one class by canonical key."""

        return self.classes.get(key)

    def get_protocol_implementations(self, key: str) -> tuple[ClassDefinition, ...]:
        """Return concrete project classes nominally implementing one protocol."""

        return tuple(
            definition
            for implementation_key in self.protocol_implementations.get(key, ())
            if (definition := self.classes.get(implementation_key)) is not None
        )

    @staticmethod
    def build_protocol_implementation_keys(
        *,
        class_bases: dict[str, tuple[str, ...]],
        protocol_keys: frozenset[str],
    ) -> dict[str, tuple[str, ...]]:
        """Index every concrete class by its nominal project protocol ancestors."""

        ancestor_cache: dict[str, frozenset[str]] = {}
        implementations: dict[str, list[str]] = {key: [] for key in protocol_keys}
        for class_key in sorted(class_bases):
            if class_key in protocol_keys:
                continue
            ancestors, ancestor_cache = ProjectIndex._protocol_ancestors(
                class_key=class_key,
                class_bases=class_bases,
                protocol_keys=protocol_keys,
                cache=ancestor_cache,
                active=frozenset(),
            )
            for protocol_key in sorted(ancestors):
                implementations[protocol_key].append(class_key)
        return {key: tuple(values) for key, values in implementations.items()}

    @staticmethod
    def _protocol_ancestors(
        *,
        class_key: str,
        class_bases: dict[str, tuple[str, ...]],
        protocol_keys: frozenset[str],
        cache: dict[str, frozenset[str]],
        active: frozenset[str],
    ) -> tuple[frozenset[str], dict[str, frozenset[str]]]:
        cached: frozenset[str] | None = cache.get(class_key)
        if cached is not None:
            return cached, cache
        if class_key in active:
            return frozenset(), cache
        ancestors: set[str] = set()
        next_active: frozenset[str] = active | {class_key}
        for base_key in class_bases.get(class_key, ()):
            if base_key in protocol_keys:
                ancestors.add(base_key)
            inherited, cache = ProjectIndex._protocol_ancestors(
                class_key=base_key,
                class_bases=class_bases,
                protocol_keys=protocol_keys,
                cache=cache,
                active=next_active,
            )
            ancestors.update(inherited)
        result: frozenset[str] = frozenset(ancestors)
        cache[class_key] = result
        return result, cache


@dataclass(frozen=True, slots=True)
class ResolvedCallable:
    """A resolved declaration plus its concrete method dispatch class."""

    definition: FunctionDefinition
    dispatch_class_key: str | None = None


@dataclass(frozen=True, slots=True)
class UnresolvedCall:
    """A dynamic call seam that the active provider cannot resolve."""

    name: str
    line: int
    reason: str


@dataclass(frozen=True, slots=True)
class CallMapNode:
    """One function and its resolved project-local callees."""

    definition: FunctionDefinition
    entries: tuple[CallMapNode | UnresolvedCall, ...]
    dispatch_class_name: str | None = None
    cycle: bool = False
    truncated: bool = False
