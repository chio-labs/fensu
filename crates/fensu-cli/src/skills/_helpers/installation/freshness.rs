use std::collections::{HashMap, HashSet};
use std::fs;
use std::path::{Path, PathBuf};

use crate::skills::_helpers::content::fingerprint::{
    content_fingerprint_matches, generated_marker_present, legacy_ownership_matches,
    owned_generated_content, owned_project_content, parse_ownership, project_input_fingerprint,
    project_marker_present, LEGACY_OWNERSHIP_SCHEMA,
};
use crate::skills::_helpers::content::rendering;
use crate::skills::_helpers::installation::filesystem::{
    capture_bundle, normalization_collision, safe_read, sorted_entries,
};
use crate::skills::_helpers::installation::plan::skills_directory;
use crate::skills::models::{
    FreshnessIssue, FreshnessReason, FreshnessResult, GeneratedSkillMigration, InstallPlan,
    Ownership,
};

pub(crate) fn check(plan: &InstallPlan, authoritative: bool) -> Result<FreshnessResult, String> {
    let expected = if authoritative {
        let rendered = rendering::generate(&plan.context)?;
        Some(owned_generated_content(&plan.context, rendered.as_bytes())?)
    } else {
        None
    };
    let mut issues: Vec<FreshnessIssue> = Vec::new();
    let mut inspected: Vec<PathBuf> = Vec::new();
    let mut targets = plan.targets.clone();
    targets.sort_by(|left, right| left.path.cmp(&right.path));
    for target in targets {
        inspected.push(target.path.clone());
        if let Some(reason) =
            inspect_generated(plan, &target.path, expected.as_deref(), authoritative)?
        {
            issues.push(FreshnessIssue {
                path: target.path,
                reason,
            });
        }
    }
    let mut result = FreshnessResult {
        inspected_paths: inspected,
        issues,
    };
    if authoritative {
        result = inspect_project_targets(plan, result)?;
    }
    result = inspect_migrations(plan, result)?;
    result.inspected_paths.sort();
    result
        .issues
        .sort_by(|left, right| left.path.cmp(&right.path));
    Ok(result)
}

fn inspect_migrations(
    plan: &InstallPlan,
    mut result: FreshnessResult,
) -> Result<FreshnessResult, String> {
    for migration in &plan.migrations {
        if plan
            .targets
            .iter()
            .any(|target| target.path == migration.path)
        {
            continue;
        }
        let Some(content) = safe_read(&migration.path)? else {
            continue;
        };
        if !generated_marker_present(&content) {
            continue;
        }
        let Some(ownership) = parse_ownership(&content) else {
            continue;
        };
        let current = ownership.identity == migration.identity
            && ownership.owner == migration.owner
            && content_fingerprint_matches(&content, &ownership);
        let legacy = legacy_ownership_matches(&content, &ownership, &migration.identity);
        if current || legacy {
            result.inspected_paths.push(migration.path.clone());
            result.issues.push(FreshnessIssue {
                path: migration.path.clone(),
                reason: FreshnessReason::Stale,
            });
        }
    }
    Ok(result)
}

fn inspect_generated(
    plan: &InstallPlan,
    path: &Path,
    expected: Option<&[u8]>,
    authoritative: bool,
) -> Result<Option<FreshnessReason>, String> {
    if normalization_collision(path)?.is_some() {
        return Ok(authoritative.then_some(FreshnessReason::Collision));
    }
    let content = match safe_read(path) {
        Ok(Some(content)) => content,
        Ok(None) => return Ok(authoritative.then_some(FreshnessReason::Missing)),
        Err(_) => return Ok(authoritative.then_some(FreshnessReason::Collision)),
    };
    if !generated_marker_present(&content) {
        return Ok(authoritative.then_some(FreshnessReason::Collision));
    }
    let Some(ownership) = parse_ownership(&content) else {
        return Ok(authoritative.then_some(FreshnessReason::MalformedMarker));
    };
    if ownership.identity != plan.context.identity {
        if matching_migration(plan, path, &content, &ownership) {
            return Ok(Some(FreshnessReason::Stale));
        }
        return Ok(authoritative.then_some(FreshnessReason::Collision));
    }
    if ownership.schema == LEGACY_OWNERSHIP_SCHEMA {
        return Ok(Some(
            if legacy_ownership_matches(&content, &ownership, &plan.context.identity) {
                FreshnessReason::Stale
            } else {
                FreshnessReason::Divergent
            },
        ));
    }
    if ownership.owner != plan.owner {
        return Ok(authoritative.then_some(FreshnessReason::Collision));
    }
    if ownership.input_fingerprint != plan.input_fingerprint {
        return Ok(Some(FreshnessReason::Stale));
    }
    if !content_fingerprint_matches(&content, &ownership) {
        return Ok(Some(FreshnessReason::Divergent));
    }
    if expected.is_some_and(|bytes| bytes != content) {
        return Ok(Some(FreshnessReason::Divergent));
    }
    Ok(None)
}

fn matching_migration(
    plan: &InstallPlan,
    path: &Path,
    content: &[u8],
    ownership: &Ownership,
) -> bool {
    plan.migrations
        .iter()
        .any(|migration| migration.path == path && migration_matches(migration, content, ownership))
}

fn migration_matches(
    migration: &GeneratedSkillMigration,
    content: &[u8],
    ownership: &Ownership,
) -> bool {
    generated_marker_present(content)
        && ownership.identity == migration.identity
        && ownership.owner == migration.owner
        && content_fingerprint_matches(content, ownership)
}

fn inspect_project_targets(
    plan: &InstallPlan,
    mut result: FreshnessResult,
) -> Result<FreshnessResult, String> {
    let mut desired = HashMap::<PathBuf, HashSet<String>>::new();
    for target in &plan.targets {
        desired
            .entry(skills_directory(&target.path)?)
            .or_default()
            .insert(plan.context.identity.to_ascii_lowercase());
    }
    let mut targets = plan.project_targets.clone();
    targets.sort_by(|left, right| left.path.cmp(&right.path));
    for target in &targets {
        for source in &target.bundle.files {
            result
                .inspected_paths
                .push(target.path.join(&source.relative_path));
        }
        if normalization_collision(&target.path.join("SKILL.md"))?.is_some() {
            result.issues.push(FreshnessIssue {
                path: target.path.join("SKILL.md"),
                reason: FreshnessReason::Collision,
            });
            continue;
        }
        let skills = target
            .path
            .parent()
            .map(Path::to_path_buf)
            .ok_or_else(|| "Project skill target has no skills directory.".to_owned())?;
        desired
            .entry(skills)
            .or_default()
            .insert(target.bundle.identity.to_ascii_lowercase());
        let installed = match capture_bundle(&target.path) {
            Ok(value) => value,
            Err(_) => {
                result.issues.push(FreshnessIssue {
                    path: target.path.join("SKILL.md"),
                    reason: FreshnessReason::Collision,
                });
                continue;
            }
        };
        let installed_by_path = installed
            .iter()
            .map(|snapshot| (snapshot.path.clone(), snapshot))
            .collect::<HashMap<_, _>>();
        let document_path = target.path.join("SKILL.md");
        if target.path.exists() && !installed_by_path.contains_key(&document_path) {
            result.issues.push(FreshnessIssue {
                path: document_path,
                reason: FreshnessReason::Collision,
            });
            continue;
        }
        let expected_document = owned_project_content(&plan.context, &target.bundle)?;
        let input = project_input_fingerprint(&plan.context, &target.bundle)?;
        let mut expected_paths: HashSet<PathBuf> = HashSet::new();
        for source in &target.bundle.files {
            let path = target.path.join(&source.relative_path);
            expected_paths.insert(path.clone());
            let Some(snapshot) = installed_by_path.get(&path) else {
                result.issues.push(FreshnessIssue {
                    path,
                    reason: FreshnessReason::Missing,
                });
                continue;
            };
            let content = snapshot.content.as_deref().unwrap_or_default();
            let expected = if source.relative_path == Path::new("SKILL.md") {
                &expected_document
            } else {
                &source.content
            };
            let reason = if source.relative_path == Path::new("SKILL.md") {
                project_document_reason(ProjectDocumentRequest {
                    plan,
                    identity: &target.bundle.identity,
                    content,
                    expected,
                    input: &input,
                })
            } else if content != expected || snapshot.mode != Some(source.mode) {
                Some(FreshnessReason::Divergent)
            } else {
                None
            };
            if let Some(reason) = reason.or_else(|| {
                (snapshot.mode != Some(source.mode)).then_some(FreshnessReason::Divergent)
            }) {
                result.issues.push(FreshnessIssue { path, reason });
            }
        }
        for snapshot in installed {
            if !expected_paths.contains(&snapshot.path) {
                result.issues.push(FreshnessIssue {
                    path: snapshot.path,
                    reason: FreshnessReason::Divergent,
                });
            }
        }
    }
    result.issues = inspect_stale_targets(plan, desired, result.issues)?;
    Ok(result)
}

fn inspect_stale_targets(
    plan: &InstallPlan,
    desired: HashMap<PathBuf, HashSet<String>>,
    mut issues: Vec<FreshnessIssue>,
) -> Result<Vec<FreshnessIssue>, String> {
    if !plan.synchronize_project_skills {
        return Ok(issues);
    }
    for (directory, desired_names) in desired {
        if !directory.is_dir()
            || fs::symlink_metadata(&directory)
                .is_ok_and(|metadata| metadata.file_type().is_symlink())
        {
            continue;
        }
        for entry in sorted_entries(&directory)? {
            let name = entry
                .file_name()
                .and_then(|value| value.to_str())
                .unwrap_or_default();
            if desired_names.contains(&name.to_ascii_lowercase()) || !entry.is_dir() {
                continue;
            }
            let document = entry.join("SKILL.md");
            let Ok(content) = safe_read(&document) else {
                continue;
            };
            let Some(content) = content else {
                continue;
            };
            let Some(ownership) = parse_ownership(&content) else {
                continue;
            };
            if project_marker_present(&content)
                && ownership.identity == name
                && (ownership.owner == plan.owner
                    || legacy_ownership_matches(&content, &ownership, name))
            {
                issues.push(FreshnessIssue {
                    path: document,
                    reason: FreshnessReason::Stale,
                });
            }
        }
    }
    Ok(issues)
}

struct ProjectDocumentRequest<'a> {
    plan: &'a InstallPlan,
    identity: &'a str,
    content: &'a [u8],
    expected: &'a [u8],
    input: &'a str,
}

fn project_document_reason(request: ProjectDocumentRequest<'_>) -> Option<FreshnessReason> {
    let ProjectDocumentRequest {
        plan,
        identity,
        content,
        expected,
        input,
    } = request;
    if !project_marker_present(content) {
        return Some(FreshnessReason::Collision);
    }
    let Some(ownership) = parse_ownership(content) else {
        return Some(FreshnessReason::MalformedMarker);
    };
    if ownership.identity != identity {
        return Some(FreshnessReason::Collision);
    }
    if ownership.schema == LEGACY_OWNERSHIP_SCHEMA {
        return Some(if legacy_ownership_matches(content, &ownership, identity) {
            FreshnessReason::Stale
        } else {
            FreshnessReason::Divergent
        });
    }
    if ownership.owner != plan.owner {
        return Some(FreshnessReason::Collision);
    }
    if ownership.input_fingerprint != input {
        return Some(FreshnessReason::Stale);
    }
    if !content_fingerprint_matches(content, &ownership) || content != expected {
        return Some(FreshnessReason::Divergent);
    }
    None
}
