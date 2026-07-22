use std::collections::BTreeMap;
use std::path::Path;

use serde_json::{json, Value};

use crate::models::RuleMetadata;
use crate::skills::helpers::content::fingerprint::canonical_ascii;
use crate::skills::models::SkillContext;

const PYPROJECT_SOURCE: &str = "pyproject";
const DOMAIN_SHAPE_HEADING: &str = "### Domain Shape";
const RUNTIME_HEADING: &str = "### Runtime";
const TESTS_HEADING: &str = "### Tests";
const TOOLING_HEADING: &str = "### Tooling";
const TOOLING_TEST_PREFIX: &str = "Tooling-backed tests mirror under `";
const TREE_FENCE_CLOSE: &str = "```";
const TREE_FENCE_OPEN: &str = "```text";

pub(crate) fn expand_repository_profile(
    mut lines: Vec<String>,
    context: &SkillContext,
) -> Result<Vec<String>, String> {
    expand_runtime_trees(&mut lines, context)?;
    expand_test_trees(&mut lines, context)?;
    expand_tooling_test_lines(&mut lines, context);
    expand_tooling_trees(&mut lines, context)?;
    Ok(lines)
}

fn expand_runtime_trees(lines: &mut Vec<String>, context: &SkillContext) -> Result<(), String> {
    let heading = marker_index(lines, RUNTIME_HEADING)?;
    let end = marker_index(lines, DOMAIN_SHAPE_HEADING)?;
    let start = heading + 2;
    let template = lines[start..end].to_vec();
    let expanded = context
        .config
        .roots
        .iter()
        .flat_map(|root| {
            let root = display_project_path(context, root);
            template
                .iter()
                .map(move |line| line.replace("__ROOT__", &root))
        })
        .collect::<Vec<_>>();
    lines.splice(start..end, expanded);
    Ok(())
}

fn expand_test_trees(lines: &mut Vec<String>, context: &SkillContext) -> Result<(), String> {
    if context.config.tests.is_empty() {
        return Ok(());
    }
    let heading = marker_index(lines, TESTS_HEADING)?;
    let start = lines[heading..]
        .iter()
        .position(|line| line == TREE_FENCE_OPEN)
        .map(|offset| heading + offset)
        .ok_or_else(|| "Compiled repository guidance has no test tree.".to_owned())?;
    let close = lines[start + 1..]
        .iter()
        .position(|line| line == TREE_FENCE_CLOSE)
        .map(|offset| start + 1 + offset)
        .ok_or_else(|| "Compiled repository guidance has an unterminated test tree.".to_owned())?;
    let end = close + 2;
    let template = lines[start..end].to_vec();
    let mut expanded = Vec::new();
    for test in &context.config.tests {
        for root in &context.config.roots {
            let test = display_project_path(context, test);
            let root = display_project_path(context, root);
            expanded.extend(
                template
                    .iter()
                    .map(|line| line.replace("__TEST__", &test).replace("__ROOT__", &root)),
            );
        }
    }
    lines.splice(start..end, expanded);
    Ok(())
}

fn expand_tooling_test_lines(lines: &mut Vec<String>, context: &SkillContext) {
    let Some(start) = lines
        .iter()
        .position(|line| line.starts_with(TOOLING_TEST_PREFIX))
    else {
        return;
    };
    let template = lines[start].clone();
    let mut expanded = Vec::new();
    for test in &context.config.tests {
        for tooling in &context.config.tooling {
            expanded.push(
                template
                    .replace("__TEST__", &display_project_path(context, test))
                    .replace("__TOOL__", &display_project_path(context, tooling)),
            );
            expanded.push(String::new());
        }
    }
    lines.splice(start..start + 2, expanded);
}

fn expand_tooling_trees(lines: &mut Vec<String>, context: &SkillContext) -> Result<(), String> {
    if context.config.tooling.is_empty() {
        return Ok(());
    }
    let heading = marker_index(lines, TOOLING_HEADING)?;
    let start = heading + 2;
    let close = lines[start..]
        .iter()
        .position(|line| line == TREE_FENCE_CLOSE)
        .map(|offset| start + offset)
        .ok_or_else(|| {
            "Compiled repository guidance has an unterminated tooling tree.".to_owned()
        })?;
    let end = close + 2;
    let template = lines[start..end].to_vec();
    let expanded = context
        .config
        .tooling
        .iter()
        .flat_map(|tooling| {
            let tooling = display_project_path(context, tooling);
            template
                .iter()
                .map(move |line| line.replace("__TOOL__", &tooling))
        })
        .collect::<Vec<_>>();
    lines.splice(start..end, expanded);
    Ok(())
}

fn marker_index(lines: &[String], marker: &str) -> Result<usize, String> {
    lines
        .iter()
        .position(|line| line == marker)
        .ok_or_else(|| format!("Compiled repository guidance has no {marker} section."))
}

pub(crate) fn effective_config_lines(context: &SkillContext) -> Result<Vec<String>, String> {
    let config = &context.config;
    let mut lines = vec![
        "## Effective Project Configuration".to_owned(), String::new(),
        "This is the loaded effective configuration, not a template. Lists and mappings are rendered deterministically; path-threshold declarations retain declaration order because that order breaks equally specific matches.".to_owned(), String::new(),
        format!("- Configuration source: {}", config_source(context)?),
        format!("- Project root from installation root: {}", relative_json(&context.project_root, &context.install_root)?),
        format!("- Installation root: {}", relative_json(&context.install_root, &context.install_root)?),
        format!("- Current skill identity: {}", py_json(&json!(context.identity))?),
        format!("- Complete loaded catalogue size: {}", context.catalogue.len()), String::new(),
        "### Scopes".to_owned(), String::new(),
        format!("- Product roots: {}", path_list(context, &config.roots)?),
        format!("- Test roots: {}", path_list(context, &config.tests)?),
        format!("- Tooling roots: {}", path_list(context, &config.tooling)?), String::new(),
        "### Configured Rule Selectors".to_owned(), String::new(),
        format!("- Blocking selectors (`select`): {}", sorted_json(&config.select)?),
        format!("- Warning selectors (`warn`): {}", sorted_json(&config.warn)?),
        format!("- Ignore selectors (`ignore`): {}", sorted_json(&config.ignore)?), String::new(),
        "### Resolved Rule Sets".to_owned(), String::new(),
        format!("- Blocking rule codes: {}", rule_codes(&context.blocking)?),
        format!("- Warning rule codes: {}", rule_codes(&context.warnings)?),
        format!("- Ignored matched rule codes: {}", rule_codes(&context.ignored)?), String::new(),
        "Normal work must satisfy blocking policy. Warnings are review signals, not scope authorization. Run `fensu check --warn` after substantial changes when practical, and never delete code or change architecture solely because of an advisory warning without verifying the actual contract.".to_owned(), String::new(),
        "### Custom Rule Sources".to_owned(), String::new(),
        format!("- `rule_paths`: {}", path_list(context, &config.rule_paths)?),
        format!("- `rule_modules`: {}", sorted_json(&config.rule_modules)?), String::new(),
        "### Cache And Evaluation".to_owned(), String::new(),
        format!("- Cache enabled: `{}`", config.cache_enabled),
        format!("- Cache requires cacheable rules: `{}`", config.cache_require_cacheable),
        format!("- Evaluation include boundaries: {}", path_list(context, &config.evaluation_include)?),
        format!("- Evaluation exclude boundaries: {}", path_list(context, &config.evaluation_exclude)?), String::new(),
        "### Effective Global Thresholds".to_owned(), String::new(),
    ];
    for (name, value) in config.thresholds.iter().collect::<BTreeMap<_, _>>() {
        lines.push(format!("- `{name}` = {value}"));
    }
    lines.extend([
        String::new(),
        "### Configured Role Threshold Overrides".to_owned(),
        String::new(),
    ]);
    let mut role_count = 0;
    for (role, values) in config.role_thresholds.iter().collect::<BTreeMap<_, _>>() {
        for (name, value) in values.iter().collect::<BTreeMap<_, _>>() {
            lines.push(format!(
                "- Role {}: `{name}` = {value}",
                py_json(&json!(role))?
            ));
            role_count += 1;
        }
    }
    if role_count == 0 {
        lines.push("- None.".to_owned());
    }
    lines.extend([
        String::new(),
        "### Configured Path Threshold Overrides".to_owned(),
        String::new(),
    ]);
    if config.threshold_overrides.is_empty() {
        lines.push("- None.".to_owned());
    } else {
        for (index, item) in config.threshold_overrides.iter().enumerate() {
            let values = item.thresholds.iter().collect::<BTreeMap<_, _>>();
            lines.push(format!(
                "- Declaration {}: paths={}; thresholds={}; reason={}",
                index + 1,
                path_list(context, &item.paths)?,
                py_json(&json!(values))?,
                py_json(&json!(item.reason))?
            ));
        }
    }
    lines.extend([
        String::new(),
        "### Effective Naming Contracts".to_owned(),
        String::new(),
    ]);
    for (pattern, behavior) in config.contracts.iter().cloned().collect::<BTreeMap<_, _>>() {
        lines.push(format!(
            "- {} = {}",
            py_json(&json!(pattern))?,
            py_json(&json!(behavior))?
        ));
    }
    lines.extend([
        String::new(),
        "### Configured Rule Exceptions".to_owned(),
        String::new(),
    ]);
    if config.exceptions.is_empty() {
        lines.push("- None.".to_owned());
    } else {
        let mut exceptions = config.exceptions.iter().collect::<Vec<_>>();
        exceptions.sort_by(|left, right| {
            (&left.rule, &left.path, &left.symbols, &left.reason).cmp(&(
                &right.rule,
                &right.path,
                &right.symbols,
                &right.reason,
            ))
        });
        for item in exceptions {
            let scope = if item.symbols.is_empty() {
                "\"file-level\"".to_owned()
            } else {
                sorted_json(&item.symbols)?
            };
            lines.push(format!(
                "- Rule {}; path={}; scope={scope}; reason={}",
                py_json(&json!(item.rule))?,
                py_json(&json!(display_project_path(context, &item.path)))?,
                py_json(&json!(item.reason))?
            ));
        }
    }
    lines.extend([
        String::new(),
        "### Configured Path-Scoped Rule Ignores".to_owned(),
        String::new(),
    ]);
    if config.rule_ignores.is_empty() {
        lines.push("- None.".to_owned());
    } else {
        for (index, item) in config.rule_ignores.iter().enumerate() {
            lines.push(format!(
                "- Declaration {}: rules={}; paths={}; reason={}",
                index + 1,
                sorted_json(&item.rules)?,
                path_list(context, &item.paths)?,
                py_json(&json!(item.reason))?
            ));
        }
        lines.push("- Rules remain active outside matching paths, matching files remain available as project context, and exact exceptions remain separately stale-validated.".to_owned());
    }
    lines.push(String::new());
    Ok(lines)
}

pub(crate) fn governed_path(context: &SkillContext) -> String {
    context
        .config_path
        .strip_prefix(&context.install_root)
        .or_else(|_| context.config_path.strip_prefix(&context.project_root))
        .unwrap_or(&context.config_path)
        .to_string_lossy()
        .replace('\\', "/")
}

fn config_source(context: &SkillContext) -> Result<String, String> {
    let root = if context.project_prefix.is_empty() {
        &context.project_root
    } else {
        &context.install_root
    };
    let path = relative_json(&context.config_path, root)?;
    Ok(if context.config.source_kind == PYPROJECT_SOURCE {
        format!("`[tool.fensu]` in {path}")
    } else {
        path
    })
}

fn relative_json(path: &Path, root: &Path) -> Result<String, String> {
    let display = path
        .strip_prefix(root)
        .map(|value| {
            if value.as_os_str().is_empty() {
                ".".to_owned()
            } else {
                value.to_string_lossy().replace('\\', "/")
            }
        })
        .unwrap_or_else(|_| path.to_string_lossy().replace('\\', "/"));
    py_json(&json!(display))
}

pub(crate) fn display_project_path(context: &SkillContext, path: &str) -> String {
    if context.project_prefix.is_empty() {
        path.to_owned()
    } else {
        format!("{}/{path}", context.project_prefix)
    }
}

fn path_list(context: &SkillContext, paths: &[String]) -> Result<String, String> {
    let mut values = paths
        .iter()
        .map(|path| display_project_path(context, path))
        .collect::<Vec<_>>();
    values.sort();
    py_json(&json!(values))
}

fn sorted_json(values: &[String]) -> Result<String, String> {
    let mut values = values.to_vec();
    values.sort();
    py_json(&json!(values))
}

fn rule_codes(rules: &[RuleMetadata]) -> Result<String, String> {
    let mut codes = rules
        .iter()
        .map(|rule| rule.code.clone())
        .collect::<Vec<_>>();
    codes.sort();
    py_json(&json!(codes))
}

pub(crate) fn py_json(value: &Value) -> Result<String, String> {
    let compact = canonical_ascii(value)?;
    let mut output = String::new();
    let mut string = false;
    let mut escaped = false;
    for character in compact.chars() {
        if string {
            output.push(character);
            if escaped {
                escaped = false;
            } else if character == '\\' {
                escaped = true;
            } else if character == '"' {
                string = false;
            }
        } else {
            match character {
                '"' => {
                    string = true;
                    output.push(character);
                }
                ',' => output.push_str(", "),
                ':' => output.push_str(": "),
                _ => output.push(character),
            }
        }
    }
    Ok(output)
}
