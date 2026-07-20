use std::path::Path;

use crate::models::CliOutput;
use crate::skills::helpers::content::{discovery, fingerprint, rendering};
use crate::skills::helpers::context::build as context;
use crate::skills::helpers::installation::install as installation;
use crate::skills::models::{FreshnessReason, SkillOptions};

pub(crate) fn execute(
    invocation: &Path,
    options: &SkillOptions,
    authoritative: bool,
) -> Result<CliOutput, String> {
    let context = context::build(invocation, options)?;
    let bundles = if authoritative {
        Some(discovery::discover_project_skills(&context)?)
    } else {
        None
    };
    let plan = installation::build_plan(&context, options, bundles.as_deref())?;
    if options.check || !authoritative {
        return check_plan(&plan, authoritative);
    }
    let generated =
        fingerprint::owned_generated_content(&context, rendering::generate(&context)?.as_bytes())?;
    let written = installation::install(&plan, &generated, options.force)?;
    let mut output = "Updated Fensu skill files:\n".to_owned();
    for path in written {
        output.push_str(&format!("  {}\n", path.display()));
    }
    Ok(CliOutput::success(output))
}

pub(crate) fn core_freshness(invocation: &Path) -> Result<String, String> {
    let options = SkillOptions {
        check: true,
        ..SkillOptions::default()
    };
    Ok(execute(invocation, &options, false)?.stdout)
}

fn check_plan(
    plan: &crate::skills::models::InstallPlan,
    authoritative: bool,
) -> Result<CliOutput, String> {
    let result = installation::check(plan, authoritative)?;
    if !authoritative {
        return Ok(CliOutput::success(if result.issues.is_empty() {
            String::new()
        } else {
            "\nFensu skill files are out of date\n  Run: fensu skills\n".to_owned()
        }));
    }
    if result.issues.is_empty() {
        let mut output = "Fensu skill files are current:\n".to_owned();
        for path in result.inspected_paths {
            output.push_str(&format!("  {}\n", path.display()));
        }
        return Ok(CliOutput::success(output));
    }
    let collision = result
        .issues
        .iter()
        .any(|issue| issue.reason == FreshnessReason::Collision);
    let mut output = "Fensu skill files require update:\n".to_owned();
    for issue in result.issues {
        output.push_str(&format!("  {}: {}\n", issue.path.display(), issue.reason));
    }
    Ok(CliOutput {
        stdout: output,
        stderr: String::new(),
        exit_code: if collision { 2 } else { 1 },
    })
}
