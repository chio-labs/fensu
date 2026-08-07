"""Build the native Dagster rule-pack catalogue."""

from __future__ import annotations

from dataclasses import replace

from fensu.rules.annotations.constants import FFA_RULES
from fensu.rules.authoring.models import RuleOption, RuleSpec
from fensu.rules.authoring.types import Family, RuleKind
from fensu.rules.hygiene.constants import FFH_RULES
from fensu.rules.layers.constants import FFL_RULES
from fensu.rules.naming.constants import FFN_RULES
from fensu.rules.roles.constants import FFR_RULES
from fensu.rules.shape.constants import FFS_RULES
from fensu.rules.tests.constants import FFT_RULES

_DAGSTER_PACK_NAME: str = "dagster"
_APPROVED_LOADER_BOUNDARIES: RuleOption[tuple[str, ...]] = RuleOption.string_list(
    name="approved_loader_boundaries",
    default=(),
    description=(
        "Exact project functions allowed to encapsulate external discovery during Dagster autoload."
    ),
)
_CORE_RULES: tuple[RuleSpec, ...] = (
    *FFA_RULES,
    *FFL_RULES,
    *FFH_RULES,
    *FFS_RULES,
    *FFT_RULES,
    *FFR_RULES,
    *FFN_RULES,
)
_REPLACED_CORE_CODES: frozenset[str] = frozenset(
    {
        "FFL101",
        "FFL102",
        "FFR101",
        "FFR102",
        "FFR104",
        "FFR204",
        "FFS120",
    }
)
_OMITTED_CORE_CODES: frozenset[str] = frozenset({"FFR304", "FFR305", "FFR309"})


def build_dagster_rules() -> tuple[RuleSpec, ...]:
    """Return native Dagster rules and unchanged retained core aliases."""

    aliases: tuple[RuleSpec, ...] = tuple(
        _alias(rule=rule)
        for rule in _CORE_RULES
        if rule.code not in _REPLACED_CORE_CODES | _OMITTED_CORE_CODES
    )
    return (*_native_rules(), *aliases)


def _native_rules() -> tuple[RuleSpec, ...]:
    return (
        _native(
            code="FPDG001",
            slug="dagster-asset-package-layout",
            message="Dagster asset packages must use asset units without legacy pipeline files",
            remediation=(
                "Require sibling assets.py and main.py files, use nearest-owner roles, and "
                "remove pipeline_assets.py and pipeline_constants.py."
            ),
        ),
        _native(
            code="FPDG002",
            slug="dagster-assets-module-shape",
            message=(
                "assets.py must define one asset, multi-asset, or asset factory and no private "
                "helpers"
            ),
            remediation=(
                "Keep one public Dagster definition in assets.py and move helper functions under "
                "_helpers/."
            ),
        ),
        _native(
            code="FPDG003",
            slug="dagster-assets-delegate-to-main",
            message="assets.py must import and call main from its sibling main.py",
            remediation=(
                "Import main from the exact sibling module and use only return main(...) or a "
                "precisely typed yield from main(...)."
            ),
        ),
        _native(
            code="FPDG004",
            slug="dagster-main-module-shape",
            message=(
                "Dagster main.py must contain only imports and one main() with an approved result "
                "contract"
            ),
            remediation=(
                "Use dg.MaterializeResult for single results, a precise Iterator/Generator of "
                "Dagster events for event streams, or NoReturn/Never for an intentional "
                "non-returning probe."
            ),
        ),
        _native(
            code="FPDG007",
            slug="dagster-asset-callback-signature",
            message=(
                "Dagster asset callbacks must accept positional context and keyword-only "
                "injected dependencies"
            ),
            remediation=(
                "Keep context as the sole positional argument and place * before resources and "
                "configuration."
            ),
        ),
        _native(
            code="FPDG008",
            slug="dagster-import-boundaries",
            message=(
                "Dagster asset imports must use approved owner, dependency, utility, and "
                "resource boundaries"
            ),
            remediation=(
                "Use owner-local support, public utilities, or resources; import another asset "
                "definition only for statically provable deps."
            ),
        ),
        _native(
            code="FPDG009",
            slug="dagster-definition-role-public-surface",
            message="job, schedule, and sensor modules may expose only Dagster definitions",
            remediation=(
                "Make supporting constants and selections private or move substantive behavior "
                "to its owning module."
            ),
        ),
        _native(
            code="FPDG010",
            slug="dagster-definition-role-module-layout",
            message=(
                "job, schedule, and sensor trees must use semantic modules and sanctioned private "
                "support roles"
            ),
            remediation=(
                "Flatten generic wrappers into role/domain/<capability>.py and use only "
                "directory-private _models.py, _types.py, _exceptions.py, _constants.py, or "
                "_helpers/ for extracted support."
            ),
        ),
        _native(
            code="FPDG011",
            slug="dagster-definition-private-support-imports",
            message=(
                "private job, schedule, and sensor support modules may only be imported within "
                "their owning directory"
            ),
            remediation=(
                "Keep the import in the support module's immediate owning directory or move "
                "genuinely shared behavior outside defs/ to its runtime owner."
            ),
        ),
        _native(
            code="FPDG012",
            slug="dagster-operational-resource-layout",
            message="operational resource packages must use explicit resource and support roles",
            remediation=(
                "Keep the ConfigurableResource, factory, and binding in "
                "<capability>/resource.py; use explicit public support roles, semantic _helpers "
                "modules for private functions, and semantic _classes modules for private "
                "collaborator classes."
            ),
        ),
        _native(
            code="FPDG013",
            slug="dagster-definition-provider-type-honesty",
            message=(
                "definitions providers must be declared honestly instead of cast to another "
                "Dagster definition type"
            ),
            remediation=(
                "Declare a semantic @dg.definitions function returning dg.Definitions and remove "
                "casts or misleading JobDefinition, ScheduleDefinition, or SensorDefinition "
                "annotations."
            ),
        ),
        _native(
            code="FPDG014",
            slug="dagster-asset-config-module-shape",
            message=(
                "asset configs must use semantic modules with one concrete config and one "
                "same-file binding"
            ),
            remediation=(
                "Move the config to defs/resources/asset_configs/<asset-domain>/<capability>.py, "
                "rename BaseConfig scopes to <Scope>PipelineConfig in pipeline.py, and bind that "
                "class from the module's sole @dg.definitions provider."
            ),
        ),
        _native(
            code="FPDG015",
            slug="no-dynamic-or-string-module-references",
            message="dynamic imports and string-based module references are forbidden",
            remediation=(
                "Use a concrete import, patch.object(module, name, ...), module.__name__, or "
                "package-module definition discovery instead of module-path strings."
            ),
        ),
        _native(
            code="FPDG016",
            slug="dagster-model-declaration-placement",
            message=(
                "structured runtime models must use the models role or an automation-private "
                "_models.py alias"
            ),
            remediation=(
                "Move the model to models.py, a models/ package, or an owner-local _models.py "
                "beneath defs/jobs, defs/schedules, or defs/sensors."
            ),
        ),
        _native(
            code="FPDG017",
            slug="dagster-exception-declaration-placement",
            message=(
                "custom exceptions must use the exceptions role or an automation-private "
                "_exceptions.py alias"
            ),
            remediation=(
                "Move the exception to exceptions.py, an exceptions/ package, or an owner-local "
                "_exceptions.py beneath defs/jobs, defs/schedules, or defs/sensors."
            ),
        ),
        _native(
            code="FPDG018",
            slug="private-helper-boundary",
            message=(
                "private support packages may only be imported within their owning package subtree"
            ),
            remediation=(
                "Import _helpers and _classes modules only from within their owning package "
                "subtree; move shared public APIs to an explicit public role."
            ),
        ),
        _native(
            code="FPDG019",
            slug="private-classes-role-shape",
            message="_classes modules may contain only private class declarations and imports",
            remediation=(
                "Prefix every class with `_`; move functions to _helpers, models to models.py, "
                "constants to constants.py, and module state inside the owning class or resource."
            ),
        ),
        _native(
            code="FPDG020",
            slug="source-root-path-allowlist",
            message="source-root paths must belong to the explicit architecture allowlist",
            remediation=(
                "Keep only package and definition entrypoints at the source root; move runtime "
                "modules beneath defs or utils."
            ),
        ),
        _native(
            code="FPDG021",
            slug="tooling-import-boundary",
            message="production modules must not import from the tooling root",
            remediation=(
                "Move shared runtime behavior beneath defs or utils and keep tooling as a one-way "
                "command boundary."
            ),
        ),
        _native(
            code="FPDG022",
            slug="runtime-package-owner-names",
            message="runtime package directories must identify an owner",
            remediation=(
                "Rename generic packages after their business or technical capability; only the "
                "sanctioned source-root utils boundary is exempt."
            ),
        ),
        _native(
            code="FPDG023",
            slug="test-root-directory-allowlist",
            message="test-root directories must be supported scopes",
            remediation=(
                "Move tests beneath unit, integration, or e2e; configure deliberate non-Python "
                "test roots separately."
            ),
        ),
        _native(
            code="FPDG024",
            slug="dagster-autoload-external-discovery",
            message=(
                "Dagster autoload must not reach external discovery outside an approved loader "
                "boundary"
            ),
            remediation=(
                "Move subprocess, network, database, SSH, and remote-client discovery behind an "
                "exact approved project function."
            ),
            options=(_APPROVED_LOADER_BOUNDARIES,),
        ),
        _native(
            code="FPDG025",
            slug="dagster-type-declaration-placement",
            message=(
                "type-layer declarations must use the types role or an automation-private "
                "_types.py alias"
            ),
            remediation=(
                "Move the type to types.py or an owner-local _types.py beneath defs/jobs, "
                "defs/schedules, or defs/sensors."
            ),
        ),
    )


def _native(
    *,
    code: str,
    slug: str,
    message: str,
    remediation: str,
    options: tuple[RuleOption[object], ...] = (),
) -> RuleSpec:
    return RuleSpec(
        code=code,
        family=Family.CUSTOM,
        slug=slug,
        message=message,
        remediation=remediation,
        kind=RuleKind.PACK,
        pack=_DAGSTER_PACK_NAME,
        options=options,
    )


def _alias(*, rule: RuleSpec) -> RuleSpec:
    return replace(
        rule,
        code=f"FPDG{rule.code[2:]}",
        kind=RuleKind.PACK,
        pack=_DAGSTER_PACK_NAME,
        alias_of=rule.code,
    )
