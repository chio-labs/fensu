"""Public-API implementations shared by non-file native rule exemplars."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fensu import Fault, ImportFact, RuleContext, ScopeName, Threshold
from fensu.rules.catalog.main._get_rule_constraint import get_rule_constraint

_INIT: str = "__init__.py"
_INIT_STEM: str = "__init__"
_HELPERS: str = "_helpers"
_LEGACY_HELPERS: str = "helpers"
_MAIN: str = "main"
_PYTHON_SUFFIX: str = ".py"
_PYTHON_CACHE: str = "__pycache__"
_SEPARATOR: str = "_"
_MINIMUM_DOMAIN_PARTS: int = 2
_MINIMUM_SUBDOMAIN_PARTS: int = 3
_NATURAL_PAIR_SIZE: int = 2
_ROLE_NAMES: frozenset[str] = frozenset(
    {"main", _HELPERS, "classes", "models", "types", "constants", "exceptions"}
)
_ROLE_FILES: frozenset[str] = frozenset(
    {
        "main.py",
        "helpers.py",
        "classes.py",
        "models.py",
        "types.py",
        "constants.py",
        "exceptions.py",
    }
)


@dataclass(frozen=True)
class _Module:
    path: Path
    scope: ScopeName
    parts: tuple[str, ...]
    domain: str | None
    ownership_root: Path | None
    first_role: str | None
    tail: tuple[str, ...]
    imports: tuple[ImportFact, ...]


def public_main_entry_external_use_impl(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Require public main entries to be consumed beyond their domain."""

    del module
    modules: list[_Module] = []
    for scope in (ScopeName.ROOT, ScopeName.TOOLING):
        for root in ctx.scope_roots(scope):
            paths: set[Path] = set()
            for pattern in ("*.py", "*.pyi"):
                paths.update(
                    ctx.project.glob(requester=ctx.path, path=root, pattern=pattern, recursive=True)
                )
            for path in sorted(paths):
                analysis: Any = ctx.project.analysis(requester=ctx.path, path=path)
                if analysis is None:
                    continue
                parts: tuple[str, ...] = (*path.relative_to(root.parent).parts[:-1], path.stem)
                if parts[-1] == _INIT_STEM:
                    parts = parts[:-1]
                ownership_root: Path | None = (
                    _effective_ownership_root(path=path, roots=ctx.ownership_roots())
                    if scope is ScopeName.ROOT
                    else root
                )
                owner_start: int = (
                    len(ownership_root.relative_to(root.parent).parts)
                    if ownership_root is not None
                    else len(parts)
                )
                domain, first_role, tail = _ownership(
                    parts=parts,
                    initializer=path.name == _INIT,
                    owner_start=owner_start,
                )
                modules.append(
                    _Module(
                        path=path,
                        scope=scope,
                        parts=parts,
                        domain=domain,
                        ownership_root=ownership_root,
                        first_role=first_role,
                        tail=tail,
                        imports=analysis.facts.references().imports,
                    )
                )
    entries: dict[tuple[str, ...], _Module] = {
        item.parts: item
        for item in modules
        if item.scope is ScopeName.ROOT
        and item.path.suffix == _PYTHON_SUFFIX
        and item.path.name != _INIT
        and item.domain is not None
        and item.first_role == _MAIN
        and item.tail
        and not item.tail[-1].startswith("_")
    }
    used: set[tuple[str, ...]] = {
        tuple(name.split(".")) for name in ctx.project.entrypoint_modules(requester=ctx.path)
    }
    for importer in modules:
        for fact in importer.imports:
            for target_parts in _import_targets(
                fact=fact,
                current_parts=importer.parts,
                initializer=importer.path.name == _INIT,
            ):
                target: _Module | None = entries.get(target_parts)
                if target is not None and (
                    importer.scope is ScopeName.TOOLING
                    or importer.domain is None
                    or importer.domain != target.domain
                    or importer.ownership_root != target.ownership_root
                ):
                    used.add(target_parts)
    return [
        ctx.path_fault(
            path=item.path, message="public main entry has no importer outside its owning domain"
        )
        for parts, item in sorted(entries.items(), key=lambda entry: str(entry[1].path))
        if parts not in used
    ]


def package_layout_impl(
    *, module: ast.Module, ctx: RuleContext, role: str, threshold: Threshold
) -> list[Fault]:
    """Apply the bounded flat-or-grouped contract to one role package owner."""

    del module
    parts: tuple[str, ...] = ctx.relative_parts()
    physical: str = role
    core_code: str = "FFR301" if role == _HELPERS else "FFR302"
    forbidden_bucket_names: tuple[str, ...] = get_rule_constraint(
        code=core_code, name="forbidden_bucket_names"
    )
    role_index: int | None = next(
        (index for index, part in enumerate(parts[:-1]) if part == physical), None
    )
    if role_index is None:
        return []
    package: Path = ctx.scope_root().joinpath(*parts[: role_index + 1])
    relative: tuple[str, ...] = ctx.path.relative_to(package).parts
    container: Path = package if len(relative) == 1 else ctx.path.parent
    if ctx.path.parent != container:
        return []
    init_path: Path = container / _INIT
    if ctx.path.name != _INIT and ctx.project.exists(requester=ctx.path, path=init_path):
        return []
    direct: tuple[Path, ...] = tuple(
        sorted(
            path
            for path in ctx.project.glob(requester=ctx.path, path=container, pattern="*.py")
            if path.name != _INIT
        )
    )
    if ctx.path.name != _INIT and (not direct or ctx.path != direct[0]):
        return []
    faults: list[Fault] = []
    recursive: tuple[Path, ...] = ()
    if direct:
        recursive = ctx.project.glob(
            requester=ctx.path, path=container, pattern="*.py", recursive=True
        )
    if direct and any(path.parent != container for path in recursive):
        faults.append(
            ctx.path_fault(message=f"{physical}/ container mixes direct modules and Python buckets")
        )
    limit: int = ctx.threshold(name=threshold, path=ctx.path)
    if len(direct) > limit:
        faults.append(
            ctx.path_fault(
                message=(
                    f"{physical}/ container has {len(direct)} modules; effective limit is {limit}"
                )
            )
        )
    depth: int = len(container.relative_to(package).parts)
    if depth == 0:
        return faults
    depth_limit: int = ctx.threshold(name=Threshold.MAX_ROLE_DEPTH, path=ctx.path)
    if depth > depth_limit:
        faults.append(
            ctx.path_fault(
                message=f"{physical}/ bucket depth is {depth}; effective limit is {depth_limit}"
            )
        )
    delegated: list[str] = []
    ancestor: Path = container.parent
    while ancestor != package:
        if ctx.project.python_anchor(requester=ctx.path, path=ancestor) != ctx.path:
            break
        if ancestor.name in forbidden_bucket_names:
            delegated.append(ancestor.name)
        ancestor = ancestor.parent
    names: tuple[str, ...] = (
        *reversed(delegated),
        *((container.name,) if container.name in forbidden_bucket_names else ()),
    )
    for name in names:
        faults.append(
            ctx.path_fault(message=f"{physical}/ bucket '{name}/' uses a runtime role name")
        )
    return faults


def top_level_domain_shape_impl(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Reject domains mixing direct role content with named subdomains."""

    del module
    if ctx.scope() is ScopeName.TOOLING:
        return []
    faults: list[Fault] = []
    for group in _grouping_roots(ctx=ctx):
        entries: tuple[Path, ...] = ctx.project.directory_entries(requester=ctx.path, path=group)
        direct: tuple[Path, ...] = _direct_role_entries(entries)
        if direct:
            faults.append(
                ctx.path_fault(
                    path=direct[0],
                    message="structural ownership group contains direct role content",
                    remediation="move role content beneath the required domain level",
                )
            )
    for domain in _domain_roots(ctx=ctx):
        entries = ctx.project.directory_entries(requester=ctx.path, path=domain)
        direct = _direct_role_entries(entries)
        if not direct or not _named_subdomains(ctx=ctx, entries=entries):
            continue
        init_path: Path = domain / _INIT
        if ctx.project.is_file(requester=ctx.path, path=init_path):
            anchor: Path = init_path
        else:
            files: tuple[Path, ...] = tuple(
                sorted(
                    ctx.project.glob(
                        requester=ctx.path, path=domain, pattern="*.py", recursive=True
                    )
                )
            )
            if not files:
                continue
            anchor = files[0]
        faults.append(
            ctx.path_fault(
                path=anchor,
                message="top-level domain mixes direct roles and named subdomains",
            )
        )
    return faults


def shared_domain_prefix_impl(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Reject sibling domain names that encode a missing common parent."""

    del module
    if ctx.scope() is not ScopeName.ROOT:
        return []
    minimum: int = ctx.threshold(
        name=Threshold.MIN_SHARED_DOMAIN_PREFIX_PACKAGES,
        path=ctx.path,
    )
    if minimum == 0:
        return []
    faults: list[Fault] = []
    for root in _ownership_roots(ctx=ctx):
        init_path: Path = root / _INIT
        if ctx.project.is_file(requester=ctx.path, path=init_path):
            anchor: Path | None = init_path
        else:
            files: tuple[Path, ...] = tuple(
                sorted(
                    ctx.project.glob(requester=ctx.path, path=root, pattern="*.py", recursive=True)
                )
            )
            anchor = files[0] if files else None
        if anchor is None:
            continue
        grouped: dict[str, list[str]] = {}
        for entry in sorted(ctx.project.directory_entries(requester=ctx.path, path=root)):
            name: str = entry.name
            if (
                name.startswith("_")
                or name in _ROLE_NAMES
                or name in {_LEGACY_HELPERS, _PYTHON_CACHE}
                or _SEPARATOR not in name
                or not name.isidentifier()
                or not ctx.project.is_dir(requester=ctx.path, path=entry)
            ):
                continue
            prefix, separator, suffix = name.partition(_SEPARATOR)
            if not separator or not prefix or not suffix:
                continue
            if not ctx.project.glob(requester=ctx.path, path=entry, pattern="*.py", recursive=True):
                continue
            grouped.setdefault(prefix, []).append(name)
        for prefix, names_list in sorted(grouped.items()):
            names: tuple[str, ...] = tuple(sorted(names_list))
            if len(names) < minimum:
                continue
            suffixes: tuple[str, ...] = tuple(
                f"{name.removeprefix(f'{prefix}_')}/" for name in names
            )
            destination: Path = root / prefix
            remediation: str = (
                f"Move them under the existing {prefix}/ domain as "
                f"{_natural_list(suffixes)} subdomains."
                if ctx.project.is_dir(requester=ctx.path, path=destination)
                else f"Create {prefix}/ and move them beneath it as "
                f"{_natural_list(suffixes)} subdomains."
            )
            faults.append(
                ctx.path_fault(
                    path=anchor,
                    message=(
                        f"sibling domains {_natural_list(names)} share the {prefix}_ owner prefix"
                    ),
                    remediation=remediation,
                )
            )
    return faults


def leaf_main_boundary_impl(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    """Require each runtime leaf to own at least one meaningful main entry."""

    del module
    ownership_root: Path | None = ctx.ownership_root()
    if ctx.scope() is not ScopeName.ROOT or ownership_root is None:
        return []
    parts: tuple[str, ...] = ctx.ownership_relative_parts()
    if len(parts) <= 1:
        return []
    domain: Path = ownership_root / parts[0]
    leaf: Path = (
        domain
        if parts[1] in _ROLE_NAMES or parts[1].endswith(_PYTHON_SUFFIX)
        else domain / parts[1]
    )
    if leaf == domain:
        entries: tuple[Path, ...] = ctx.project.directory_entries(requester=ctx.path, path=domain)
        if _named_subdomains(ctx=ctx, entries=entries):
            return []
    entries: tuple[Path, ...] = tuple(
        path
        for path in ctx.project.glob(
            requester=ctx.path, path=leaf / "main", pattern="*.py", recursive=True
        )
        if path.name != _INIT
    )
    if entries:
        return []
    anchor: Path | None = ctx.project.python_anchor(requester=ctx.path, path=leaf)
    if anchor is None:
        return []
    name: str = leaf.relative_to(ctx.scope_root()).as_posix()
    return [
        ctx.path_fault(
            path=anchor,
            message=f"leaf runtime package '{name}/' has no meaningful main/ entry module",
        )
    ]


def _ownership(
    *, parts: tuple[str, ...], initializer: bool, owner_start: int
) -> tuple[str | None, str | None, tuple[str, ...]]:
    owner_start = min(owner_start, len(parts))
    role_index: int | None = next(
        (
            index
            for index, part in enumerate(parts[owner_start:], start=owner_start)
            if part in _ROLE_NAMES
        ),
        None,
    )
    if role_index is None:
        end: int = len(parts) if initializer else max(owner_start, len(parts) - 1)
        owner: tuple[str, ...] = parts[owner_start:end]
        return (owner[0] if owner else None, None, parts[end:])
    owner = parts[owner_start:role_index]
    return (owner[0] if owner else None, parts[role_index], parts[role_index + 1 :])


def _import_targets(
    *, fact: ImportFact, current_parts: tuple[str, ...], initializer: bool
) -> tuple[tuple[str, ...], ...]:
    if not fact.from_import:
        return tuple(tuple(alias.imported_parts) for alias in fact.aliases)
    if fact.relative_level == 0:
        bases: tuple[tuple[str, ...], ...] = (
            (tuple(fact.module_parts),) if fact.module_parts else ()
        )
    elif not fact.module_parts:
        bases = ()
    else:
        package: tuple[str, ...] = current_parts if initializer else current_parts[:-1]
        parents: int = fact.relative_level - 1
        bases = (
            ((*package[: len(package) - parents], *fact.module_parts),)
            if parents <= len(package)
            else ()
        )
    targets: list[tuple[str, ...]] = list(bases)
    for base in bases:
        targets.extend((*base, *alias.imported_parts) for alias in fact.aliases)
    return tuple(dict.fromkeys(targets))


def _named_subdomains(*, ctx: RuleContext, entries: tuple[Path, ...]) -> tuple[Path, ...]:
    return tuple(
        entry
        for entry in entries
        if entry.name not in _ROLE_NAMES
        and entry.name != _PYTHON_CACHE
        and ctx.project.is_dir(requester=ctx.path, path=entry)
        and ctx.project.glob(requester=ctx.path, path=entry, pattern="*.py", recursive=True)
    )


def _direct_role_entries(entries: tuple[Path, ...]) -> tuple[Path, ...]:
    return tuple(
        entry
        for entry in entries
        if entry.name in _ROLE_NAMES
        or (entry.suffix == _PYTHON_SUFFIX and entry.name in _ROLE_FILES)
    )


def _grouping_roots(*, ctx: RuleContext) -> tuple[Path, ...]:
    groups: set[Path] = set()
    scope_roots: tuple[Path, ...] = ctx.scope_roots(ScopeName.ROOT)
    for ownership_root in ctx.ownership_roots():
        scope_root: Path | None = next(
            (
                root
                for root in sorted(scope_roots, key=lambda item: len(item.parts), reverse=True)
                if ownership_root == root or ownership_root.is_relative_to(root)
            ),
            None,
        )
        if scope_root is None:
            continue
        current: Path = ownership_root
        while current != scope_root:
            groups.add(current)
            current = current.parent
    return tuple(sorted(groups))


def _ownership_roots(*, ctx: RuleContext) -> tuple[Path, ...]:
    return ctx.ownership_roots()


def _domain_roots(*, ctx: RuleContext) -> tuple[Path, ...]:
    return _owned_directories(ctx=ctx, roots=_ownership_roots(ctx=ctx))


def _owned_directories(*, ctx: RuleContext, roots: tuple[Path, ...]) -> tuple[Path, ...]:
    directories: list[Path] = []
    for root in roots:
        for entry in ctx.project.directory_entries(requester=ctx.path, path=root):
            if entry.name in _ROLE_NAMES or entry.name == _PYTHON_CACHE:
                continue
            if not ctx.project.is_dir(requester=ctx.path, path=entry):
                continue
            if not ctx.project.glob(
                requester=ctx.path,
                path=entry,
                pattern="*.py",
                recursive=True,
            ):
                continue
            directories.append(entry)
    return tuple(sorted(directories))


def _effective_ownership_root(*, path: Path, roots: tuple[Path, ...]) -> Path | None:
    matches: tuple[Path, ...] = tuple(
        root for root in roots if path == root or path.is_relative_to(root)
    )
    return max(matches, key=lambda item: len(item.parts), default=None)


def _natural_list(values: tuple[str, ...]) -> str:
    if len(values) == 1:
        return values[0]
    if len(values) == _NATURAL_PAIR_SIZE:
        return f"{values[0]} and {values[1]}"
    return f"{', '.join(values[:-1])}, and {values[-1]}"
