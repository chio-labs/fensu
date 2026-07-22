use std::collections::{BTreeMap, HashSet};
use std::path::Path;
use std::sync::OnceLock;

use serde_json::{json, Value};

use crate::models::RuleMetadata;
use crate::skills::helpers::content::sections::{
    display_project_path, effective_config_lines, expand_repository_profile, governed_path, py_json,
};
use crate::skills::models::SkillContext;

const GENERATED_MARKER: &str = "<!-- generated-by: fensu skills -->";
const CUSTOM_KIND: &str = "custom";
const TESTS_HEADING: &str = "### Tests";
const TOOLING_HEADING: &str = "### Tooling";
const PROFILE: &[u8] = include_bytes!(concat!(
    env!("CARGO_MANIFEST_DIR"),
    "/assets/skills_invariant.json"
));

pub(crate) fn generate(context: &SkillContext) -> Result<String, String> {
    let governed = governed_path(context);
    let project_name = context
        .identity
        .strip_prefix("fensu-")
        .unwrap_or(&context.identity);
    let mut lines = vec![
        "---".to_owned(),
        format!("name: {}", py_json(&json!(context.identity))?),
        format!(
            "description: {}",
            py_json(&json!(format!(
                "Use when modifying the {project_name} project governed by {governed}. Includes Fensu configuration, commands, FF diagnostics, repository architecture, and multi-module Python call-flow work."
            )))?
        ),
        "---".to_owned(),
        String::new(),
        GENERATED_MARKER.to_owned(),
        String::new(),
        "# Fensu".to_owned(),
        String::new(),
        "Fensu checks code ownership, dependency boundaries, module roles, function shape, and test conventions. This skill is generated from the repository's active rules.".to_owned(),
        "Load this guidance before running any `fensu` command or changing Fensu configuration.".to_owned(),
        String::new(),
        "## Commands".to_owned(),
        String::new(),
        "- Run `fensu check` after architecture-relevant changes.".to_owned(),
        "- Run `fensu rule <CODE>` to inspect a diagnostic and its remediation.".to_owned(),
        "- Run `fensu map <SYMBOL>` for a conservative downstream project call tree.".to_owned(),
        "- Run `fensu skills` after changing rule selection or custom rules.".to_owned(),
        String::new(),
    ];
    if context.config.memory_enabled {
        let memory = profile_lines("memory")?
            .into_iter()
            .map(|line| {
                line.replace(
                    "987654321",
                    &context.config.memory_archive_after_days.to_string(),
                )
            })
            .collect::<Vec<_>>();
        lines.extend(memory);
    }
    lines.extend(profile_lines("navigation")?);
    lines.extend(profile_lines("work_practices")?);
    lines.extend(repository_lines(context)?);
    lines.extend(configured_threshold_lines(context)?);
    lines.extend(effective_config_lines(context)?);
    if !context.warnings.is_empty() {
        lines.extend([
            "## Warning Policy", "",
            "`fensu check` evaluates blocking rules only. `fensu check --warn` additionally evaluates the configured warning tier; warning-only findings do not fail the command. Treat warnings as evidence to investigate, not proof that code is safe to remove or architecture should change.", "",
        ].into_iter().map(str::to_owned));
    }
    lines.extend(profile_lines("custom_authority")?);
    lines.extend(profile_lines("rule_context")?);
    lines.extend(profile_lines("authoring_lookup")?);
    lines.extend(custom_rule_testing_lines(context));
    lines.extend(cacheability_lines(context));
    lines.extend(tier_lines("Blocking Rules", &context.blocking));
    lines.extend(tier_lines("Warning Rules", &context.warnings));
    Ok(format!("{}\n", lines.join("\n").trim_end()))
}

fn profile() -> Result<&'static Value, String> {
    static VALUE: OnceLock<Value> = OnceLock::new();
    if let Some(value) = VALUE.get() {
        return Ok(value);
    }
    let parsed = serde_json::from_slice(PROFILE)
        .map_err(|error| format!("Invalid compiled skills guidance asset: {error}"))?;
    let _ = VALUE.set(parsed);
    VALUE
        .get()
        .ok_or_else(|| "Could not initialize compiled skills guidance.".to_owned())
}

fn profile_lines(name: &str) -> Result<Vec<String>, String> {
    profile()?
        .get(name)
        .and_then(Value::as_array)
        .ok_or_else(|| format!("Compiled skills guidance has no {name} section."))?
        .iter()
        .map(|value| {
            value
                .as_str()
                .map(str::to_owned)
                .ok_or_else(|| format!("Compiled skills guidance {name} contains a non-string."))
        })
        .collect()
}

fn repository_lines(context: &SkillContext) -> Result<Vec<String>, String> {
    let active = context
        .blocking
        .iter()
        .chain(&context.warnings)
        .map(|rule| rule.code.as_str())
        .collect::<HashSet<_>>();
    if !["FFR306", "FFR307"]
        .iter()
        .all(|code| active.contains(code))
    {
        return Ok(Vec::new());
    }
    let name = if context.config.tooling.is_empty() {
        "repository"
    } else {
        "repository_tooling"
    };
    let root = display_project_path(
        context,
        context.config.roots.first().map_or(".", String::as_str),
    );
    let test = display_project_path(
        context,
        context.config.tests.first().map_or("tests", String::as_str),
    );
    let tooling = display_project_path(
        context,
        context
            .config
            .tooling
            .first()
            .map_or("scripts", String::as_str),
    );
    let helper_limit = role_threshold(context, "helpers", "max_helpers_container_modules", 10);
    let main_limit = role_threshold(context, "main", "max_main_container_modules", 20);
    let role_depth = context
        .config
        .thresholds
        .get("max_role_depth")
        .copied()
        .unwrap_or(1);
    let import_root = context
        .config
        .roots
        .first()
        .and_then(|path| Path::new(path).file_name())
        .and_then(|name| name.to_str())
        .unwrap_or(".");
    let mut profile = expand_repository_profile(profile_lines(name)?, context)?;
    if context.config.tests.is_empty() {
        if let Some(tests_index) = profile.iter().position(|line| line == TESTS_HEADING) {
            if let Some(tooling_offset) = profile[tests_index..]
                .iter()
                .position(|line| line == TOOLING_HEADING)
            {
                profile.drain(tests_index..tests_index + tooling_offset);
            } else {
                profile.truncate(tests_index);
            }
        }
    }
    Ok(profile
        .into_iter()
        .map(|line| {
            let line = if line.starts_with("from __TEST__") {
                line.replace("__ROOT__", &root.replace('/', "."))
                    .replace("__TEST__", &test.replace('/', "."))
            } else if line.starts_with("from __ROOT__") {
                line.replace("__ROOT__", import_root)
            } else {
                line.replace("__ROOT__", &root).replace("__TEST__", &test)
            };
            line.replace("__TOOL__", &tooling)
                .replace(
                    "configured role base is 10",
                    &format!("configured role base is {helper_limit}"),
                )
                .replace(
                    "configured role base is 20",
                    &format!("configured role base is {main_limit}"),
                )
                .replace(
                    "Configured base `max_role_depth` is 1.",
                    &format!("Configured base `max_role_depth` is {role_depth}."),
                )
        })
        .collect())
}

fn role_threshold(context: &SkillContext, role: &str, name: &str, fallback: u32) -> u32 {
    context
        .config
        .role_thresholds
        .get(role)
        .and_then(|values| values.get(name))
        .or_else(|| context.config.thresholds.get(name))
        .copied()
        .unwrap_or(fallback)
}

fn configured_threshold_lines(context: &SkillContext) -> Result<Vec<String>, String> {
    let active = context
        .blocking
        .iter()
        .chain(&context.warnings)
        .map(|rule| rule.code.clone())
        .collect::<Vec<_>>();
    let required = crate::helpers::check_policy::required_thresholds(&active);
    let applicable = context
        .config
        .threshold_overrides
        .iter()
        .filter(|item| {
            item.thresholds
                .keys()
                .any(|name| required.contains(name.as_str()))
        })
        .collect::<Vec<_>>();
    if applicable.is_empty() {
        return Ok(Vec::new());
    }
    let mut lines = vec![
        "## Configured Threshold Overrides".to_owned(),
        String::new(),
        "Patterns match reported repository paths. Specificity is compared as `(literal segments, literal characters, -globstars, -wildcards, declaration order)`; the greatest tuple wins. Literal segments contain no `*`, literal characters exclude `/` and `*`, globstars count `**` segments, and wildcards count remaining `*` tokens.".to_owned(),
        String::new(),
        "```toml".to_owned(),
    ];
    for item in applicable {
        let thresholds = item
            .thresholds
            .iter()
            .filter(|(name, _)| required.contains(name.as_str()))
            .collect::<BTreeMap<_, _>>();
        let paths = item
            .paths
            .iter()
            .map(|value| py_json(&json!(value)))
            .collect::<Result<Vec<_>, _>>()?
            .join(", ");
        let thresholds = thresholds
            .into_iter()
            .map(|(key, value)| format!("{key} = {value}"))
            .collect::<Vec<_>>()
            .join(", ");
        lines.extend([
            "[[threshold_overrides]]".to_owned(),
            format!("paths = [{paths}]"),
            format!("reason = {}", py_json(&json!(item.reason))?),
            format!("thresholds = {{ {thresholds} }}"),
            String::new(),
        ]);
    }
    lines.extend(["```".to_owned(), String::new()]);
    Ok(lines)
}

fn custom_rule_testing_lines(context: &SkillContext) -> Vec<String> {
    if context.config.rule_paths.is_empty() && context.config.rule_modules.is_empty() {
        return Vec::new();
    }
    let minimum = context
        .config
        .thresholds
        .get("min_custom_rule_test_cases")
        .copied()
        .unwrap_or(1);
    format!("## Testing Custom Rules\n\nTest approved custom rules through Fensu's real discovery and evaluation pipeline. Import the harness only from the top-level package and pass the decorated rule function as `rule=`. `RuleFile` support sources are available to `ctx.project` but are not direct evaluation targets.\nThe effective minimum is `{minimum}` statically declared `RuleCase` value(s) per configured custom rule, including rules not selected for blocking or warning evaluation. A value of `0` disables this requirement.\n\nWhen FFT413 is active, do not parametrize directly with `RuleCase`. Parametrize with a dataclass imported from local `_test_types.py`, then construct `RuleCase` inside the test. A pair of apparently conflicting diagnostics should only be described as a policy gap after checking whether an adapter or wrapper pattern satisfies both rules.\n\n`_test_types.py`:\n\n```python\nfrom dataclasses import dataclass\n\nfrom fensu import RuleFile\n\n\n@dataclass(frozen=True)\nclass CustomRuleTestCase:\n    description: str\n    path: str\n    source: str\n    expected_fault_count: int\n    files: tuple[RuleFile, ...] = ()\n    scope: str = \"root\"\n    scope_root: str | None = None\n```\n\n`test_client_ownership.py`:\n\n```python\nimport pytest\n\nfrom fensu import RuleCase, RuleResult, evaluate_rule\nfrom scripts.fensu_policy.rules.client_ownership import no_global_client\nfrom tests.unit.scripts.fensu_policy.rules._test_types import CustomRuleTestCase\n\n\n@pytest.mark.parametrize(\n    \"test_case\",\n    [\n        CustomRuleTestCase(\n            description=\"reports a forbidden global client\",\n            path=\"package/example.py\",\n            source=\"GLOBAL_CLIENT = build_client()\\n\",\n            expected_fault_count=1,\n        ),\n        CustomRuleTestCase(\n            description=\"allows a function-local client\",\n            path=\"package/example.py\",\n            source=\"def run() -> None:\\n    client = build_client()\\n\",\n            expected_fault_count=0,\n        ),\n    ],\n    ids=lambda case: case.description,\n)\ndef test_given_source_when_checking_rule_then_returns_expected_faults(\n    test_case: CustomRuleTestCase,\n) -> None:\n    result: RuleResult = evaluate_rule(\n        rule=no_global_client,\n        test_case=RuleCase(\n            description=test_case.description,\n            path=test_case.path,\n            source=test_case.source,\n            expected_fault_count=test_case.expected_fault_count,\n            files=test_case.files,\n            scope=test_case.scope,\n            scope_root=test_case.scope_root,\n        ),\n    )\n\n    assert result.fault_count == test_case.expected_fault_count\n```\n\nCover a failing example, a passing example, near misses, scope exclusions, deterministic ordering, and cross-file invalidation when the rule uses `ctx.project`. Verify cold and warm cache behavior. Dynamic case generators cannot prove the configured static minimum.\n")
        .split('\n').map(str::to_owned).collect()
}

fn cacheability_lines(context: &SkillContext) -> Vec<String> {
    let mut text = format!("## Cacheability\n\nConfigured cache enabled: `{}`. Configured `require_cacheable`: `{}`.\n\n", context.config.cache_enabled, context.config.cache_require_cacheable);
    let selected_custom = context
        .blocking
        .iter()
        .chain(&context.warnings)
        .any(|rule| rule.kind == CUSTOM_KIND);
    if selected_custom {
        if context.config.cache_require_cacheable {
            text.push_str("Because `require_cacheable = true`, every selected custom rule must satisfy the cacheability contract.\n\n");
        } else {
            text.push_str("Undeclared custom rules re-run fresh on every check while cacheable rules keep using the cache. Declare `cacheable=True` on `@rule` only when the rule satisfies the cacheability contract (the declaration is validated and stops the run on violations), or `cacheable=False` to silence the appears-cacheable notice. Set `require_cacheable = true` to demand the contract from every selected custom rule.\n\n");
        }
        text.push_str("Cacheable custom rules use only allowlisted pure imports; never call `open`, `eval`, `exec`, `input`, or `__import__`; perform no direct filesystem access; make every cross-file query through `ctx.project` with `requester=ctx.path`; and emit deterministic diagnostics. Configure concrete `rule_modules`. Keep decorated declarations in `rules/`, shared implementation in the sibling `_helpers/`, and constants in the policy package's sibling `constants.py`. A configured rule package does not mean helpers belong beneath `rules/`; that layout violates FFR704.\n\n");
    }
    text.push_str("Verify cache behavior with separate commands so a deliberate baseline fault does not prevent later observations:\n\n```bash\nfensu check --no-cache\nfensu check --cache-stats\nfensu check --cache-stats\n```\n\nFor a cacheable ruleset, the second cached run must report all hits, zero misses, `non_cacheable=0`, and diagnostics byte-identical to the uncached run.\n");
    text.split('\n').map(str::to_owned).collect()
}

fn tier_lines(heading: &str, rules: &[RuleMetadata]) -> Vec<String> {
    let mut lines = vec![format!("## {heading}"), String::new()];
    if rules.is_empty() {
        lines.extend(["None.".to_owned(), String::new()]);
        return lines;
    }
    let mut rules = rules.iter().collect::<Vec<_>>();
    rules.sort_by(|left, right| left.code.cmp(&right.code));
    for rule in rules {
        lines.extend([
            format!("### {}: {}", rule.code, rule.slug),
            String::new(),
            format!("Family: `{}`", rule.family),
            String::new(),
            rule.message.clone(),
            String::new(),
            format!(
                "Remediation: {}",
                rule.remediation
                    .as_deref()
                    .unwrap_or("No remediation provided.")
            ),
            String::new(),
        ]);
    }
    lines
}
