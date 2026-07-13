"""Render public custom-rule authoring and cacheability guidance."""

from __future__ import annotations

from strata.agentdocs.models import SkillGenerationContext
from strata.config.models import Config
from strata.rules.authoring.types import RuleKind


def rule_context_lines() -> tuple[str, ...]:
    """Return a compact complete inventory of the public RuleContext protocol."""

    return (
        "## RuleContext Public API",
        "",
        "Approved custom rules receive `ctx: RuleContext`. Import authoring APIs only from the "
        "top-level `strata` package. The five public analysis zones are:",
        "",
        "- `ctx.facts`: `annotations()`, `comments()`, `dataclasses()`, "
        "`complex_comprehensions()`, `function_conditionals()`, `functions()`, "
        "`function_contracts()`, `hygiene()`, `meaningful_returns(name_patterns=())`, "
        "`module_declarations()`, `outer_state_mutations()`, `parameter_mutations()`, "
        "`project_calls()`, `project_functions()`, `references()`, `test_functions()`, "
        "`top_level_definition_conditionals()`, and `test_module()`.",
        "- `ctx.text`: `source`, `line(line_number)`, and `slice(source_range)`.",
        "- `ctx.syntax`: `handles(kind=None)`, `kind(handle)`, and `range(handle)`.",
        "- `ctx.relations`: `parent(handle)`, `children(handle)`, and `ancestors(handle)`.",
        "- `ctx.project`: dependency-recording cross-file and filesystem queries. Use "
        "`analysis(requester=ctx.path, path=path)`, "
        "`dataclasses(requester=ctx.path, path=path)`, "
        "`directory_entries(requester=ctx.path, path=path)`, "
        "`module_function(requester=ctx.path, module_name=name, function_name=name)`, "
        "`python_anchor(requester=ctx.path, path=path)`, "
        "`exists(requester=ctx.path, path=path)`, "
        "`is_dir(requester=ctx.path, path=path)`, "
        "`is_file(requester=ctx.path, path=path)`, and "
        "`glob(requester=ctx.path, path=path, pattern=pattern, recursive=False)`. Inspect "
        "recorded observations with `dependencies()` or "
        "`dependencies_for(requester=ctx.path)`.",
        "",
        "Position and ownership helpers: `ctx.path`, `ctx.repo_root`, `ctx.source`, "
        "`relative_parts()`, `repo_relative_parts()`, `scope_root()`, `scope_roots(scope)`, "
        "`module_parts()`, `scope()`, `role_of()`, `in_role(role)`, `is_entry_module()`, "
        "`is_main_module()`, `domain()`, and `subdomain()`. `role_of()` describes the current "
        "file here; use project facts rather than assuming arbitrary paths share its position.",
        "",
        "AST helpers: `nodes(node_type)`, `call_name(node)`, `base_name(node)`, "
        "`top_level_functions(module)`, `non_docstring_body(module)`, `distinct_callees(fn)`, "
        "`assigned_locals(fn)`, `complex_comprehensions()`, `parameter_names(fn)`, and "
        "`inside_loop(node)`.",
        "",
        "Policy helpers: `threshold(name=..., path=None)` and `contracts()`. Fault constructors: "
        "`fault(node=..., message=None, remediation=None)`, "
        "`fault_at(location=..., message=None, remediation=None)`, "
        "`fault_for(path=..., line=..., column=..., message=None, remediation=None)`, and "
        "`path_fault(path=None, message=None, remediation=None)`.",
        "",
    )


def authoring_lookup_lines() -> tuple[str, ...]:
    """Return the approved custom-rule API lookup order."""

    return (
        "## Approved Custom Rule Authoring Lookup",
        "",
        "When authoring an approved custom rule, use the generated RuleContext summary first. If "
        "exact signatures or returned public models are unclear, inspect existing repository "
        "custom rules, then the public Strata exports and type definitions from the project's "
        "active Python environment. This targets the installed Strata version rather than "
        "remembered or generic API knowledge.",
        "",
        "It is acceptable to locate the active installation through `strata.__file__` or the "
        "project's `.venv` and read definitions behind public exports such as `RuleContext`, "
        "semantic fact protocols, project-query protocols, and public result models. Consult "
        "public documentation after those installed public definitions. Read private "
        "implementation only to diagnose a suspected Strata defect.",
        "",
        "Only import authoring APIs from top-level `strata`. Reading installed implementation for "
        "understanding does not make private `_helpers/` modules a supported dependency. Do not "
        "import from or couple custom rules to Strata's private modules.",
        "",
    )


def rule_testing_lines(context: SkillGenerationContext) -> tuple[str, ...]:
    """Return harness usage when repository custom rules are configured."""

    if not context.config.rule_paths and not context.config.rule_modules:
        return ()
    return (
        "## Testing Custom Rules",
        "",
        "Test approved custom rules through Strata's real discovery and evaluation pipeline. "
        "Import the harness only from the top-level package and pass the decorated rule function "
        "as `rule=`. `RuleFile` support sources are available to `ctx.project` but are not direct "
        "evaluation targets.",
        "",
        "```python",
        "import pytest",
        "",
        "from strata import RuleCase, RuleResult, evaluate_rule",
        "from scripts.policy.rules import no_global_client",
        "",
        "@pytest.mark.parametrize(",
        '    "test_case",',
        "    [",
        "        RuleCase(",
        '            description="reports a forbidden global client",',
        '            source="GLOBAL_CLIENT = build_client()\\n",',
        "            expected_fault_count=1,",
        "        ),",
        "        RuleCase(",
        '            description="allows a function-local client",',
        '            source="def run() -> None:\\n    client = build_client()\\n",',
        "            expected_fault_count=0,",
        "        ),",
        "    ],",
        "    ids=lambda case: case.description,",
        ")",
        "def test_given_source_when_checking_rule_then_returns_expected_faults(",
        "    test_case: RuleCase,",
        ") -> None:",
        "    result: RuleResult = evaluate_rule(rule=no_global_client, test_case=test_case)",
        "",
        "    assert result.fault_count == test_case.expected_fault_count",
        "```",
        "",
        "Cover failing and passing boundaries, near misses, relevant scopes and roles, configured "
        "threshold or contract behavior, deterministic ordering, and cross-file dependency "
        "observations when the rule uses `ctx.project`.",
        "",
    )


def cacheability_lines(context: SkillGenerationContext) -> tuple[str, ...]:
    """Return effective cache policy and conditional custom-rule constraints."""

    config: Config = context.config
    selected_custom_rules: bool = any(
        rule.kind is RuleKind.CUSTOM for rule in (*context.blocking_rules, *context.warning_rules)
    )
    lines: list[str] = [
        "## Cacheability",
        "",
        f"Configured cache enabled: `{str(config.cache.enabled).lower()}`. Configured "
        f"`require_cacheable`: `{str(config.cache.require_cacheable).lower()}`.",
        "",
    ]
    if selected_custom_rules:
        lines.extend(_custom_cacheability_lines(require_cacheable=config.cache.require_cacheable))
    lines.extend(
        (
            "Verify cache behavior with separate commands so a deliberate baseline fault does not "
            "prevent later observations:",
            "",
            "```bash",
            "strata check --no-cache",
            "strata check --cache-stats",
            "strata check --cache-stats",
            "```",
            "",
            "For a cacheable ruleset, the second cached run must report all hits, zero misses, "
            "`non_cacheable=0`, and diagnostics byte-identical to the uncached run.",
            "",
        )
    )
    return tuple(lines)


def _custom_cacheability_lines(*, require_cacheable: bool) -> tuple[str, ...]:
    requirement: str = (
        "Because `require_cacheable = true`, every selected custom rule must satisfy the "
        "cacheability contract."
        if require_cacheable
        else "Selected custom rules disable persistent caching by default. Set "
        "`require_cacheable = true` only when every selected custom rule satisfies the "
        "cacheability contract."
    )
    return (
        requirement,
        "",
        "Cacheable custom rules use only allowlisted pure imports; never call `open`, `eval`, "
        "`exec`, `input`, or `__import__`; perform no direct filesystem access; make every "
        "cross-file query through `ctx.project` with `requester=ctx.path`; emit deterministic "
        "diagnostics; and keep helpers inside configured rule packages.",
        "",
    )
