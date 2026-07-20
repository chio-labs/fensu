use std::collections::HashSet;
use std::path::{Path, PathBuf};

use crate::skills::helpers::content::fingerprint::{input_fingerprint, owner};
use crate::skills::helpers::context::identity::home_dir;
use crate::skills::models::{
    InstallPlan, InstallTarget, ProjectInstallTarget, ProjectSkillBundle, SkillContext,
    SkillOptions, SkillTarget,
};

pub(crate) fn build(
    context: &SkillContext,
    options: &SkillOptions,
    bundles: Option<&[ProjectSkillBundle]>,
) -> Result<InstallPlan, String> {
    let mut requested = if options.targets.is_empty() {
        vec![
            SkillTarget::Opencode,
            SkillTarget::Claude,
            SkillTarget::Agents,
        ]
    } else {
        options.targets.clone()
    };
    let mut seen_targets = HashSet::new();
    requested.retain(|target| seen_targets.insert(*target));
    let home = if options.global_install {
        Some(home_dir()?)
    } else {
        None
    };
    let targets = requested
        .iter()
        .map(|target| target_path(*target, options.global_install, home.as_deref(), context))
        .collect::<Result<Vec<_>, _>>()?;
    let synchronize_project_skills = bundles.is_some();
    let bundles = bundles.unwrap_or(&[]);
    let mut identities = HashSet::from([context.identity.to_ascii_lowercase()]);
    for bundle in bundles {
        if !identities.insert(bundle.identity.to_ascii_lowercase()) {
            return Err(
                "duplicate normalized identity across generated and project skills".to_owned(),
            );
        }
    }
    let mut project_targets = Vec::new();
    for target in &targets {
        let skills = skills_directory(&target.path)?;
        for bundle in bundles {
            project_targets.push(ProjectInstallTarget {
                path: skills.join(&bundle.identity),
                bundle: bundle.clone(),
            });
        }
    }
    let mut roots = vec![context.project_root.clone(), context.install_root.clone()];
    if let Some(root) = &context.git_root {
        roots.insert(1, root.clone());
    }
    roots.sort();
    roots.dedup();
    let mut legacy_paths = Vec::new();
    if options.global_install {
        for target in &targets {
            legacy_paths.push(skills_directory(&target.path)?.join("fensu/SKILL.md"));
        }
    } else {
        for root in roots {
            for requested_target in &requested {
                let agent = match requested_target {
                    SkillTarget::Opencode => ".opencode",
                    SkillTarget::Claude => ".claude",
                    SkillTarget::Agents => ".agents",
                };
                legacy_paths.push(root.join(agent).join("skills/fensu/SKILL.md"));
            }
        }
    }
    legacy_paths.sort();
    legacy_paths.dedup();
    Ok(InstallPlan {
        context: context.clone(),
        targets,
        project_targets,
        legacy_paths,
        owner: owner(context),
        input_fingerprint: input_fingerprint(context)?,
        synchronize_project_skills,
    })
}

fn target_path(
    target: SkillTarget,
    global: bool,
    home: Option<&Path>,
    context: &SkillContext,
) -> Result<InstallTarget, String> {
    let base = match (target, global) {
        (SkillTarget::Opencode, true) => required_home(home)?.join(".config/opencode"),
        (SkillTarget::Claude, true) => required_home(home)?.join(".claude"),
        (SkillTarget::Agents, true) => required_home(home)?.join(".agents"),
        (SkillTarget::Opencode, false) => context.install_root.join(".opencode"),
        (SkillTarget::Claude, false) => context.install_root.join(".claude"),
        (SkillTarget::Agents, false) => context.install_root.join(".agents"),
    };
    Ok(InstallTarget {
        path: base.join("skills").join(&context.identity).join("SKILL.md"),
    })
}

fn required_home(home: Option<&Path>) -> Result<&Path, String> {
    home.ok_or_else(|| "Global skill installation has no resolved home directory.".to_owned())
}

pub(crate) fn skills_directory(path: &Path) -> Result<PathBuf, String> {
    path.parent()
        .and_then(Path::parent)
        .map(Path::to_path_buf)
        .ok_or_else(|| "Skill target has no skills directory.".to_owned())
}
