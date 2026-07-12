"""Call-map models."""

from __future__ import annotations

import ast
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
class ClassReference:
    """A class expression and the import context that owns it."""

    expression: ast.expr
    annotation: bool


@dataclass(frozen=True, slots=True)
class FunctionDefinition:
    """A project-owned function or direct class method definition."""

    module_name: str
    name: str
    path: Path
    node: ast.FunctionDef | ast.AsyncFunctionDef
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
    node: ast.ClassDef
    imports: ModuleImports
    bases: tuple[ast.expr, ...]
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
