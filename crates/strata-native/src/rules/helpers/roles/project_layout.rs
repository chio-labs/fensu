//! Project-data-plane policy for non-file role layout owners.

use std::path::Path;

use crate::rules::constants::{
    HELPERS_PACKAGE_LAYOUT_CODE, LEAF_MAIN_BOUNDARY_CODE, MAIN_PACKAGE_LAYOUT_CODE,
    SHARED_DOMAIN_PREFIX_CODE, TOP_LEVEL_DOMAIN_SHAPE_CODE,
};
use crate::rules::helpers::role_project_layout_paths::{
    direct_modules, domain_dir, file_name, forbidden_bucket, leaf_dir, main_entries, mixed_domain,
    named_subdomains, natural_list, prefix_groups, python_anchor, recursive_python,
    repository_path, role_package, scope_root, HELPERS, INIT_FILE, ROOT_SCOPE,
};
use crate::rules::helpers::roles::path_fault;
use crate::rules::models::{NativeFaultRow, NativeRuleContext};

const MAIN_ROLE: &str = "main";
const MAX_HELPERS_MODULES_THRESHOLD: &str = "max_helpers_container_modules";
const MAX_MAIN_MODULES_THRESHOLD: &str = "max_main_container_modules";
const MAX_ROLE_DEPTH_THRESHOLD: &str = "max_role_depth";
const MINIMUM_DOMAIN_PARTS: usize = 2;
const MINIMUM_SHARED_PREFIX_THRESHOLD: &str = "min_shared_domain_prefix_packages";
const TOOLING_SCOPE: &str = "tooling";

struct DepthContext<'a> {
    code: &'a str,
    context: &'a NativeRuleContext,
    role: &'a str,
    anchor: &'a Path,
    container: &'a Path,
    package: &'a Path,
    depth: usize,
}

pub(crate) fn project_layout_faults(
    code: &str,
    context: &NativeRuleContext,
) -> Option<Vec<NativeFaultRow>> {
    match code {
        HELPERS_PACKAGE_LAYOUT_CODE => Some(container_faults(code, context, HELPERS)),
        MAIN_PACKAGE_LAYOUT_CODE => Some(container_faults(code, context, MAIN_ROLE)),
        TOP_LEVEL_DOMAIN_SHAPE_CODE => Some(domain_shape_faults(code, context)),
        SHARED_DOMAIN_PREFIX_CODE => Some(shared_prefix_faults(code, context)),
        LEAF_MAIN_BOUNDARY_CODE => Some(leaf_main_faults(code, context)),
        _ => None,
    }
}

fn container_faults(code: &str, context: &NativeRuleContext, role: &str) -> Vec<NativeFaultRow> {
    let Some(package) = role_package(context, role) else {
        return Vec::new();
    };
    let anchor = repository_path(context);
    let Some(container) = anchor.parent() else {
        return Vec::new();
    };
    let direct = direct_modules(container);
    if anchor.file_name().and_then(|name| name.to_str()) != Some(INIT_FILE)
        && (container.join(INIT_FILE).exists() || direct.first() != Some(&anchor))
    {
        return Vec::new();
    }
    let mut faults = Vec::new();
    if !direct.is_empty()
        && recursive_python(container)
            .iter()
            .any(|path| path.parent() != Some(container))
    {
        faults.push(message_fault(
            code,
            context,
            format!("{role}/ container mixes direct modules and Python buckets"),
        ));
    }
    let threshold_name = if role == HELPERS {
        MAX_HELPERS_MODULES_THRESHOLD
    } else {
        MAX_MAIN_MODULES_THRESHOLD
    };
    let module_limit = context
        .thresholds
        .get(threshold_name)
        .copied()
        .unwrap_or_default() as usize;
    if direct.len() > module_limit {
        faults.push(message_fault(
            code,
            context,
            format!(
                "{role}/ container has {} modules; effective limit is {module_limit}",
                direct.len()
            ),
        ));
    }
    let depth = container
        .strip_prefix(&package)
        .map(Path::components)
        .map(Iterator::count)
        .unwrap_or_default();
    if depth > 0 {
        append_depth_faults(
            &mut faults,
            DepthContext {
                code,
                context,
                role,
                anchor: &anchor,
                container,
                package: &package,
                depth,
            },
        );
    }
    faults
}

fn append_depth_faults(faults: &mut Vec<NativeFaultRow>, owner: DepthContext<'_>) {
    let depth_limit = owner
        .context
        .thresholds
        .get(MAX_ROLE_DEPTH_THRESHOLD)
        .copied()
        .unwrap_or_default() as usize;
    if owner.depth > depth_limit {
        faults.push(message_fault(
            owner.code,
            owner.context,
            format!(
                "{}/ bucket depth is {}; effective limit is {depth_limit}",
                owner.role, owner.depth
            ),
        ));
    }
    let mut delegated = Vec::new();
    let mut ancestor = owner.container.parent();
    while let Some(path) = ancestor {
        if path == owner.package || python_anchor(path).as_deref() != Some(owner.anchor) {
            break;
        }
        if forbidden_bucket(path) {
            delegated.push(file_name(path).to_owned());
        }
        ancestor = path.parent();
    }
    delegated.reverse();
    if forbidden_bucket(owner.container) {
        delegated.push(file_name(owner.container).to_owned());
    }
    for name in delegated {
        faults.push(message_fault(
            owner.code,
            owner.context,
            format!("{}/ bucket '{name}/' uses a runtime role name", owner.role),
        ));
    }
}

fn domain_shape_faults(code: &str, context: &NativeRuleContext) -> Vec<NativeFaultRow> {
    if context.scope == TOOLING_SCOPE || context.relative_parts.len() < MINIMUM_DOMAIN_PARTS {
        return Vec::new();
    }
    let Some(domain) = domain_dir(context) else {
        return Vec::new();
    };
    if !mixed_domain(&domain) {
        return Vec::new();
    }
    let anchor = domain.join(INIT_FILE);
    let anchor = if anchor.is_file() {
        anchor
    } else if let Some(first) = recursive_python(&domain).into_iter().next() {
        first
    } else {
        return Vec::new();
    };
    vec![reported_fault(
        code,
        context,
        &anchor,
        "top-level domain mixes direct roles and named subdomains".to_owned(),
        None,
    )]
}

fn shared_prefix_faults(code: &str, context: &NativeRuleContext) -> Vec<NativeFaultRow> {
    if context.scope != ROOT_SCOPE {
        return Vec::new();
    }
    let root = scope_root(context);
    let init_path = root.join(INIT_FILE);
    let anchor = if init_path.is_file() {
        init_path
    } else if let Some(first) = recursive_python(&root).into_iter().next() {
        first
    } else {
        return Vec::new();
    };
    let minimum = context
        .thresholds
        .get(MINIMUM_SHARED_PREFIX_THRESHOLD)
        .copied()
        .unwrap_or_default() as usize;
    if minimum == 0 {
        return Vec::new();
    }
    prefix_groups(&root)
        .into_iter()
        .filter(|(_, names)| names.len() >= minimum)
        .map(|(prefix, names)| {
            let suffixes: Vec<String> = names
                .iter()
                .map(|name| format!("{}/", name.trim_start_matches(&format!("{prefix}_"))))
                .collect();
            let remediation = if root.join(&prefix).is_dir() {
                format!(
                    "Move them under the existing {prefix}/ domain as {} subdomains.",
                    natural_list(&suffixes)
                )
            } else {
                format!(
                    "Create {prefix}/ and move them beneath it as {} subdomains.",
                    natural_list(&suffixes)
                )
            };
            reported_fault(
                code,
                context,
                &anchor,
                format!(
                    "sibling domains {} share the {prefix}_ owner prefix",
                    natural_list(&names)
                ),
                Some(remediation),
            )
        })
        .collect()
}

fn leaf_main_faults(code: &str, context: &NativeRuleContext) -> Vec<NativeFaultRow> {
    let Some(leaf) = leaf_dir(context) else {
        return Vec::new();
    };
    let domain = scope_root(context).join(&context.relative_parts[0]);
    if leaf == domain && !named_subdomains(&domain).is_empty() {
        return Vec::new();
    }
    if !main_entries(&leaf).is_empty() {
        return Vec::new();
    }
    let Some(anchor) = python_anchor(&leaf) else {
        return Vec::new();
    };
    let name = leaf
        .strip_prefix(scope_root(context))
        .unwrap_or(&leaf)
        .to_string_lossy()
        .replace('\\', "/");
    vec![reported_fault(
        code,
        context,
        &anchor,
        format!("leaf runtime package '{name}/' has no meaningful main/ entry module"),
        None,
    )]
}

fn message_fault(code: &str, context: &NativeRuleContext, message: String) -> NativeFaultRow {
    let mut fault = path_fault(code, Some(&message));
    fault.path = Some(context.repository_path.clone());
    fault
}

fn reported_fault(
    code: &str,
    context: &NativeRuleContext,
    path: &Path,
    message: String,
    remediation: Option<String>,
) -> NativeFaultRow {
    NativeFaultRow {
        code: code.to_owned(),
        line: 0,
        column: 0,
        message: Some(message),
        remediation,
        path: path
            .strip_prefix(&context.repo_root)
            .ok()
            .map(|relative| relative.to_string_lossy().replace('\\', "/")),
    }
}
