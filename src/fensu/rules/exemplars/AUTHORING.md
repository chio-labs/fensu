# Installed Custom Rule Authoring

Use only top-level `fensu` imports in repository custom rules. Installed private
modules may be read to understand the active version, but they are not supported
imports.

## Start Here

- Semantic facts:
  `main/annotations/_parameter_annotation.py`
- Cross-file and project-owned policy:
  `main/layers/_public_main_entry_external_use.py`
- Package ownership and configured thresholds:
  `main/roles/_helpers_package_layout.py`
- Public callback contract and available context methods:
  `../authoring/types.py`
- Public isolated test harness:
  `../testing/main/evaluate_rule.py`

## Minimal Rule

```python
import ast

from fensu import Family, Fault, RuleContext, rule


@rule(
    code="XPR001",
    family=Family.CUSTOM,
    slug="no-bare-except",
    message="bare except handlers hide unexpected failures",
)
def no_bare_except(*, module: ast.Module, ctx: RuleContext) -> list[Fault]:
    return [
        ctx.fault(node=node)
        for node in ast.walk(module)
        if isinstance(node, ast.ExceptHandler) and node.type is None
    ]
```

Prefer `ctx.facts`, `ctx.syntax`, `ctx.relations`, `ctx.text`, and `ctx.project`
when they express the required policy. Use raw `ast.Module` traversal only when
the public backend-neutral zones do not expose the needed syntax.

## Test The Real Pipeline

```python
import pytest

from fensu import RuleCase, RuleResult, evaluate_rule
from scripts.fensu_policy.rules.no_bare_except import no_bare_except


@pytest.mark.parametrize(
    "test_case",
    [
        RuleCase(
            description="reports a bare except handler",
            source="try:\n    run()\nexcept:\n    recover()\n",
            expected_fault_count=1,
        ),
        RuleCase(
            description="allows a typed handler",
            source="try:\n    run()\nexcept ValueError:\n    recover()\n",
            expected_fault_count=0,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_handler_when_checking_then_returns_expected_faults(
    test_case: RuleCase,
) -> None:
    result: RuleResult = evaluate_rule(rule=no_bare_except, test_case=test_case)

    assert result.fault_count == test_case.expected_fault_count
```

## Configure Discovery

Store project policy under the configured tooling scope and load it explicitly:

```toml
tooling = ["scripts"]
rule_paths = ["scripts/fensu_policy/rules"]
```

Custom rule codes begin with `X`. Run `fensu check`, `fensu rule XPR001`, and
`fensu skills` after configuration. Generated skills include the active
`RuleContext` summary, cacheability requirements, and custom-rule testing policy.
