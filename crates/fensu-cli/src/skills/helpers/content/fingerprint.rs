use std::collections::BTreeMap;
use std::path::Path;

use serde_json::{json, Value};
use sha2::{Digest, Sha256};

use crate::models::{Config, RuleMetadata};
use crate::skills::models::{Ownership, ProjectSkillBundle, SkillContext};

const GENERATED_MARKER: &str = "<!-- generated-by: fensu skills -->";
const OWNER_PREFIX: &str = "<!-- fensu-skill-owner: ";
const OWNER_SUFFIX: &str = " -->";
const PROJECT_MARKER: &str = "<!-- synchronized-project-skill-by: fensu skills -->";
const UNICODE_BASIC_PLANE_MAX: u32 = 0xffff;

pub(crate) fn input_fingerprint(context: &SkillContext) -> Result<String, String> {
    let payload = input_value(context);
    let encoded = canonical_ascii(&payload)?;
    Ok(digest(encoded.as_bytes()))
}

pub(crate) fn input_value(context: &SkillContext) -> BTreeMap<&'static str, Value> {
    let mut payload = BTreeMap::new();
    payload.insert("schema", json!(1));
    payload.insert(
        "config_source",
        json!({
            "kind": context.config.source_kind,
            "path": posix(&context.config_path),
        }),
    );
    payload.insert("project_root", json!(posix(&context.project_root)));
    payload.insert("install_root", json!(posix(&context.install_root)));
    payload.insert(
        "git_root",
        context
            .git_root
            .as_ref()
            .map(|path| json!(posix(path)))
            .unwrap_or(Value::Null),
    );
    payload.insert("project_prefix", json!(context.project_prefix));
    payload.insert("identity", json!(context.identity));
    payload.insert("config", config_value(&context.config));
    payload.insert("catalogue", rules_value(&context.catalogue));
    payload.insert("blocking", rules_value(&context.blocking));
    payload.insert("warnings", rules_value(&context.warnings));
    payload.insert("ignored", rules_value(&context.ignored));
    payload
}

pub(crate) fn owner(context: &SkillContext) -> String {
    digest(posix(&context.config_path).as_bytes())
}

pub(crate) fn owned_generated_content(
    context: &SkillContext,
    content: &[u8],
) -> Result<Vec<u8>, String> {
    let text = std::str::from_utf8(content).map_err(|error| error.to_string())?;
    if text.matches(GENERATED_MARKER).count() != 1 {
        return Err("Generated skill content contains an invalid generated marker.".to_owned());
    }
    let mut ownership = Ownership {
        schema: 1,
        identity: context.identity.clone(),
        owner: owner(context),
        input_fingerprint: input_fingerprint(context)?,
        content_fingerprint: String::new(),
    };
    let provisional_marker = ownership_marker(&ownership)?;
    let provisional = text.replacen(
        GENERATED_MARKER,
        &format!("{GENERATED_MARKER}\n{provisional_marker}"),
        1,
    );
    ownership.content_fingerprint = digest(provisional.as_bytes());
    Ok(provisional
        .replacen(&provisional_marker, &ownership_marker(&ownership)?, 1)
        .into_bytes())
}

pub(crate) fn owned_project_content(
    context: &SkillContext,
    bundle: &ProjectSkillBundle,
) -> Result<Vec<u8>, String> {
    let document = bundle
        .files
        .iter()
        .find(|file| file.relative_path == Path::new("SKILL.md"))
        .ok_or_else(|| format!("project skill {:?} has no SKILL.md", bundle.identity))?;
    let mut ownership = Ownership {
        schema: 1,
        identity: bundle.identity.clone(),
        owner: owner(context),
        input_fingerprint: project_input_fingerprint(context, bundle)?,
        content_fingerprint: String::new(),
    };
    let provisional_marker = ownership_marker(&ownership)?;
    let mut provisional = document.content.clone();
    if !provisional.ends_with(b"\n") {
        provisional.push(b'\n');
    }
    provisional.extend_from_slice(PROJECT_MARKER.as_bytes());
    provisional.push(b'\n');
    provisional.extend_from_slice(provisional_marker.as_bytes());
    provisional.push(b'\n');
    ownership.content_fingerprint = digest(&provisional);
    let final_marker = ownership_marker(&ownership)?;
    replace_once(
        &provisional,
        provisional_marker.as_bytes(),
        final_marker.as_bytes(),
    )
    .ok_or_else(|| "Could not publish project skill ownership marker.".to_owned())
}

pub(crate) fn project_input_fingerprint(
    context: &SkillContext,
    bundle: &ProjectSkillBundle,
) -> Result<String, String> {
    let mut hash = Sha256::new();
    hash.update(input_fingerprint(context)?.as_bytes());
    hash.update(b"\0");
    hash.update(bundle.identity.as_bytes());
    for file in &bundle.files {
        hash.update(b"\0");
        hash.update(
            file.relative_path
                .to_string_lossy()
                .replace('\\', "/")
                .as_bytes(),
        );
        hash.update(b"\0");
        hash.update(file.mode.to_string().as_bytes());
        hash.update(b"\0");
        hash.update(&file.content);
    }
    Ok(format!("{:x}", hash.finalize()))
}

pub(crate) fn parse_ownership(content: &[u8]) -> Option<Ownership> {
    let matches = content
        .split(|byte| *byte == b'\n')
        .map(|line| line.strip_suffix(b"\r").unwrap_or(line))
        .filter(|line| line.starts_with(OWNER_PREFIX.as_bytes()))
        .collect::<Vec<_>>();
    let [line] = matches.as_slice() else {
        return None;
    };
    if !line.ends_with(OWNER_SUFFIX.as_bytes()) {
        return None;
    }
    let raw = &line[OWNER_PREFIX.len()..line.len() - OWNER_SUFFIX.len()];
    let value: Value = serde_json::from_slice(raw).ok()?;
    let object = value.as_object()?;
    let expected = [
        "schema",
        "identity",
        "owner",
        "input_fingerprint",
        "content_fingerprint",
    ];
    if object.len() != expected.len() || expected.iter().any(|key| !object.contains_key(*key)) {
        return None;
    }
    let ownership: Ownership = serde_json::from_value(value).ok()?;
    (ownership.schema == 1).then_some(ownership)
}

pub(crate) fn content_fingerprint_matches(content: &[u8], ownership: &Ownership) -> bool {
    let Ok(final_marker) = ownership_marker(ownership) else {
        return false;
    };
    if content
        .split(|byte| *byte == b'\n')
        .filter(|line| line.strip_suffix(b"\r").unwrap_or(line) == final_marker.as_bytes())
        .count()
        != 1
    {
        return false;
    }
    let mut provisional = ownership.clone();
    provisional.content_fingerprint.clear();
    let Ok(marker) = ownership_marker(&provisional) else {
        return false;
    };
    replace_once(content, final_marker.as_bytes(), marker.as_bytes())
        .is_some_and(|bytes| digest(&bytes) == ownership.content_fingerprint)
}

pub(crate) fn generated_marker_present(content: &[u8]) -> bool {
    line_present(content, GENERATED_MARKER)
        || line_present(content, "<!-- generated-by: fensu skills update -->")
}

pub(crate) fn project_marker_present(content: &[u8]) -> bool {
    line_present(content, PROJECT_MARKER)
}

fn line_present(content: &[u8], marker: &str) -> bool {
    content
        .split(|byte| *byte == b'\n')
        .map(|line| line.strip_suffix(b"\r").unwrap_or(line))
        .any(|line| line == marker.as_bytes())
}

fn ownership_marker(ownership: &Ownership) -> Result<String, String> {
    let value = json!({
        "content_fingerprint": ownership.content_fingerprint,
        "identity": ownership.identity,
        "input_fingerprint": ownership.input_fingerprint,
        "owner": ownership.owner,
        "schema": ownership.schema,
    });
    Ok(format!(
        "{OWNER_PREFIX}{}{OWNER_SUFFIX}",
        canonical_ascii(&value)?
    ))
}

fn config_value(config: &Config) -> Value {
    let thresholds = config
        .thresholds
        .iter()
        .map(|(key, value)| (key.clone(), json!(value)))
        .collect::<BTreeMap<_, _>>();
    let role_thresholds = config
        .role_thresholds
        .iter()
        .map(|(role, values)| {
            let values = values
                .iter()
                .map(|(key, value)| (key.clone(), json!(value)))
                .collect::<BTreeMap<_, _>>();
            (role.clone(), json!(values))
        })
        .collect::<BTreeMap<_, _>>();
    let contracts = config.contracts.iter().cloned().collect::<BTreeMap<_, _>>();
    json!({
        "roots": config.roots,
        "tests": config.tests,
        "tooling": config.tooling,
        "select": config.select,
        "warn": config.warn,
        "ignore": config.ignore,
        "rule_paths": config.rule_paths,
        "rule_modules": config.rule_modules,
        "rule_exceptions": config.exceptions.iter().map(|item| json!({
            "rule": item.rule, "path": item.path, "reason": item.reason, "symbols": item.symbols,
        })).collect::<Vec<_>>(),
        "rule_ignores": config.rule_ignores.iter().map(|item| json!({
            "rules": item.rules, "paths": item.paths, "reason": item.reason,
        })).collect::<Vec<_>>(),
        "cache": {"enabled": config.cache_enabled, "require_cacheable": config.cache_require_cacheable},
        "evaluation": {"include": config.evaluation_include, "exclude": config.evaluation_exclude},
        "experimental": {"memory": config.memory_enabled},
        "memory": {"tasks": {"archive_after_days": config.memory_archive_after_days}},
        "skills": {"name": config.skills_name},
        "thresholds": thresholds,
        "role_thresholds": role_thresholds,
        "threshold_overrides": config.threshold_overrides.iter().map(|item| {
            let values = item.thresholds.iter().map(|(key, value)| (key.clone(), json!(value))).collect::<BTreeMap<_, _>>();
            json!({"paths": item.paths, "thresholds": values, "reason": item.reason})
        }).collect::<Vec<_>>(),
        "contracts": contracts,
    })
}

fn rules_value(rules: &[RuleMetadata]) -> Value {
    let mut sorted = rules.iter().collect::<Vec<_>>();
    sorted.sort_by(|left, right| left.code.cmp(&right.code).then(left.slug.cmp(&right.slug)));
    Value::Array(
        sorted
            .into_iter()
            .map(|rule| {
                json!({
                    "code": rule.code,
                    "family": rule.family,
                    "slug": rule.slug,
                    "message": rule.message,
                    "remediation": rule.remediation,
                    "severity": rule.severity,
                    "kind": rule.kind,
                    "source": rule.source,
                    "enabled_by_default": rule.enabled_by_default,
                    "cacheable": rule.cacheable,
                    "execution_owner": rule.execution_owner,
                })
            })
            .collect(),
    )
}

pub(crate) fn canonical_ascii<T: serde::Serialize>(value: &T) -> Result<String, String> {
    let value = serde_json::to_value(value).map_err(|error| error.to_string())?;
    let encoded = serde_json::to_string(&sorted_value(value)).map_err(|error| error.to_string())?;
    let mut output = String::new();
    for character in encoded.chars() {
        if character.is_ascii() {
            output.push(character);
            continue;
        }
        let code = character as u32;
        if code <= UNICODE_BASIC_PLANE_MAX {
            output.push_str(&format!("\\u{code:04x}"));
        } else {
            let adjusted = code - 0x10000;
            output.push_str(&format!(
                "\\u{:04x}\\u{:04x}",
                0xd800 + (adjusted >> 10),
                0xdc00 + (adjusted & 0x3ff)
            ));
        }
    }
    Ok(output)
}

fn sorted_value(value: Value) -> Value {
    match value {
        Value::Object(values) => {
            let sorted = values
                .into_iter()
                .map(|(key, value)| (key, sorted_value(value)))
                .collect::<BTreeMap<_, _>>();
            Value::Object(sorted.into_iter().collect())
        }
        Value::Array(values) => Value::Array(values.into_iter().map(sorted_value).collect()),
        other => other,
    }
}

fn replace_once(content: &[u8], old: &[u8], new: &[u8]) -> Option<Vec<u8>> {
    let index = content
        .windows(old.len())
        .position(|window| window == old)?;
    let mut output = Vec::with_capacity(content.len() + new.len().saturating_sub(old.len()));
    output.extend_from_slice(&content[..index]);
    output.extend_from_slice(new);
    output.extend_from_slice(&content[index + old.len()..]);
    Some(output)
}

fn digest(content: &[u8]) -> String {
    format!("{:x}", Sha256::digest(content))
}

fn posix(path: &Path) -> String {
    path.to_string_lossy().replace('\\', "/")
}
