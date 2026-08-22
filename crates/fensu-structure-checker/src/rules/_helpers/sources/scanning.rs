//! Collect workspace source files and dispatch per-file rule families.

use std::fs;
use std::path;

use crate::constants;
use crate::models;
use crate::rules::_helpers::functions::hygiene;
use crate::rules::_helpers::functions::naming;
use crate::rules::_helpers::functions::shape;
use crate::rules::_helpers::imports::layers;
use crate::rules::_helpers::roles::containers;
use crate::rules::_helpers::roles::placement;
use crate::rules::_helpers::roles::role_files;
use crate::rules::_helpers::test_conventions::tests_layout;
use crate::rules::_helpers::test_conventions::tests_shape;
use crate::types::FileKind;

/// Ask Cargo for the workspace's actual packages, targets, and dependency identities.
pub(crate) fn scan_workspace(repo_root: &path::Path) -> models::WorkspaceScan {
    let manifest_path = repo_root.join(constants::CARGO_MANIFEST_FILE);
    let source = match fs::read_to_string(&manifest_path) {
        Ok(value) => value,
        Err(error) => {
            return models::WorkspaceScan {
                crates: Vec::new(),
                violations: vec![manifest_setup_violation(
                    repo_root,
                    &manifest_path,
                    format!("cannot read workspace manifest: {error}"),
                )],
            };
        }
    };
    let manifest = match toml::from_str::<toml::Value>(&source) {
        Ok(value) => value,
        Err(error) => {
            return models::WorkspaceScan {
                crates: Vec::new(),
                violations: vec![manifest_setup_violation(
                    repo_root,
                    &manifest_path,
                    format!("cannot parse workspace manifest: {error}"),
                )],
            };
        }
    };
    let mut violations = workspace_lint_violations(repo_root, &manifest_path, &manifest);
    let relative_manifest = manifest_path
        .strip_prefix(repo_root)
        .unwrap_or(&manifest_path);
    violations.extend(layers::workspace_dependency_policy_violations(
        relative_manifest,
        &manifest,
    ));
    let mut command = cargo_metadata::MetadataCommand::new();
    command.manifest_path(&manifest_path).no_deps();
    let metadata = match command.exec() {
        Ok(value) => value,
        Err(error) => {
            violations.push(manifest_setup_violation(
                repo_root,
                &manifest_path,
                format!("Cargo could not discover workspace packages and targets: {error}"),
            ));
            return models::WorkspaceScan {
                crates: Vec::new(),
                violations,
            };
        }
    };
    let metadata_root_matches = metadata
        .workspace_root
        .as_std_path()
        .canonicalize()
        .is_ok_and(|root| root == repo_root);
    if !metadata_root_matches {
        violations.push(manifest_setup_violation(
            repo_root,
            &manifest_path,
            "Cargo metadata resolved a different canonical workspace root",
        ));
        return models::WorkspaceScan {
            crates: Vec::new(),
            violations,
        };
    }
    let resolved_metadata = match resolved_metadata(repo_root, &manifest_path) {
        Ok(value) => Some(value),
        Err(error) => {
            violations.push(manifest_setup_violation(
                repo_root,
                &manifest_path,
                format!("Cargo could not resolve exact dependency identities: {error}"),
            ));
            None
        }
    };
    let mut crates: Vec<models::WorkspaceCrate> = Vec::new();
    for package in metadata
        .packages
        .iter()
        .filter(|package| metadata.workspace_members.contains(&package.id))
    {
        let (workspace_crate, package_violations) =
            discover_workspace_crate(repo_root, package, resolved_metadata.as_ref());
        violations.extend(package_violations);
        if let Some(workspace_crate) = workspace_crate {
            crates.push(workspace_crate);
        }
    }
    crates.sort_by(|left, right| left.directory.cmp(&right.directory));
    crates.dedup_by(|left, right| left.directory == right.directory);
    if crates.is_empty() {
        violations.push(manifest_setup_violation(
            repo_root,
            &manifest_path,
            "Cargo workspace contains no Rust packages",
        ));
    }
    models::WorkspaceScan { crates, violations }
}

fn resolved_metadata(
    repo_root: &path::Path,
    manifest_path: &path::Path,
) -> Result<cargo_metadata::Metadata, String> {
    let mut command = cargo_metadata::MetadataCommand::new();
    command
        .manifest_path(manifest_path)
        .features(cargo_metadata::CargoOpt::AllFeatures);
    let metadata = command
        .exec()
        .map_err(|error| format!("Cargo metadata failed: {error}"))?;
    let root = metadata
        .workspace_root
        .as_std_path()
        .canonicalize()
        .map_err(|error| format!("workspace root cannot be canonicalized: {error}"))?;
    if root != repo_root {
        return Err("Cargo metadata resolved a different canonical workspace root".to_owned());
    }
    Ok(metadata)
}

fn discover_workspace_crate(
    repo_root: &path::Path,
    package: &cargo_metadata::Package,
    metadata: Option<&cargo_metadata::Metadata>,
) -> (Option<models::WorkspaceCrate>, Vec<models::Violation>) {
    let mut violations: Vec<models::Violation> = Vec::new();
    let package_manifest = package.manifest_path.as_std_path();
    let package_dir = match package_manifest.parent() {
        Some(directory) => contained_canonical_path(repo_root, directory),
        None => Err("has no manifest directory".to_owned()),
    };
    let package_dir = match package_dir {
        Ok(value) => value,
        Err(error) => {
            violations.push(manifest_setup_violation(
                repo_root,
                package_manifest,
                format!("workspace package {} {error}", package.name),
            ));
            return (None, violations);
        }
    };
    let (targets, target_violations) = discover_targets(repo_root, package, &package_dir);
    violations.extend(target_violations);
    if targets.is_empty() {
        violations.push(manifest_setup_violation(
            repo_root,
            package_manifest,
            format!(
                "workspace package {} has no contained Rust targets",
                package.name
            ),
        ));
    }
    let (dependencies, dependency_violations) = discover_dependencies(repo_root, package, metadata);
    violations.extend(dependency_violations);
    let package_identity = format!(
        "workspace:{}:{}",
        relative_display(repo_root, &package_dir),
        package.name
    );
    let workspace_crate = models::WorkspaceCrate {
        directory: package_dir,
        package_name: Some(package.name.clone()),
        package_identity,
        library_name: library_target_name(package),
        targets,
        dependencies,
    };
    (Some(workspace_crate), violations)
}

fn discover_targets(
    repo_root: &path::Path,
    package: &cargo_metadata::Package,
    package_dir: &path::Path,
) -> (Vec<models::WorkspaceTarget>, Vec<models::Violation>) {
    let package_manifest = package.manifest_path.as_std_path();
    let mut targets: Vec<models::WorkspaceTarget> = Vec::new();
    let mut excluded: Vec<(path::PathBuf, String)> = Vec::new();
    let mut included: Vec<path::PathBuf> = Vec::new();
    let mut violations: Vec<models::Violation> = Vec::new();
    for target in &package.targets {
        let source_path = match contained_canonical_path(package_dir, target.src_path.as_std_path())
        {
            Ok(value) => value,
            Err(error) => {
                violations.push(manifest_setup_violation(
                    repo_root,
                    package_manifest,
                    format!(
                        "Cargo target {} for package {} {error}",
                        target.name, package.name
                    ),
                ));
                continue;
            }
        };
        if excluded_target(target) {
            excluded.push((source_path, target.name.clone()));
            continue;
        }
        let is_test = target
            .kind
            .iter()
            .any(|kind| matches!(kind, cargo_metadata::TargetKind::Test));
        let conventional_root = package_dir.join(if is_test {
            constants::TESTS_DIRECTORY
        } else {
            constants::SOURCE_DIRECTORY
        });
        if !supported_target_entry(target, &source_path, &conventional_root, is_test) {
            violations.push(manifest_setup_violation(
                repo_root,
                package_manifest,
                format!(
                    "Cargo target {} for package {} uses unsupported source path {}; library, binary, and integration-test targets must remain beneath src/ or tests/",
                    target.name,
                    package.name,
                    source_path.display()
                ),
            ));
            continue;
        }
        targets.push(models::WorkspaceTarget {
            source_root: conventional_root,
            test: is_test,
        });
        included.push(source_path);
    }
    targets = add_conventional_tests(package_dir, targets);
    targets.sort_by(|left, right| {
        left.source_root
            .cmp(&right.source_root)
            .then(left.test.cmp(&right.test))
    });
    targets.dedup();
    let source_root = package_dir.join(constants::SOURCE_DIRECTORY);
    let tests_root = package_dir.join(constants::TESTS_DIRECTORY);
    for (entry, name) in excluded {
        if included.contains(&entry)
            || !entry.starts_with(&source_root) && !entry.starts_with(&tests_root)
        {
            continue;
        }
        violations.push(manifest_setup_violation(
            repo_root,
            package_manifest,
            format!(
                "excluded Cargo target {name} for package {} uses source-tree entry {}; examples, benchmarks, and build scripts must remain outside src/ and tests/",
                package.name,
                entry.display()
            ),
        ));
    }
    (targets, violations)
}

fn library_target_name(package: &cargo_metadata::Package) -> Option<String> {
    package
        .targets
        .iter()
        .find(|target| target.kind.iter().any(library_target))
        .map(|target| target.name.replace('-', "_"))
}

fn library_target(kind: &cargo_metadata::TargetKind) -> bool {
    matches!(
        kind,
        cargo_metadata::TargetKind::Lib
            | cargo_metadata::TargetKind::RLib
            | cargo_metadata::TargetKind::DyLib
            | cargo_metadata::TargetKind::CDyLib
            | cargo_metadata::TargetKind::StaticLib
            | cargo_metadata::TargetKind::ProcMacro
    )
}

fn excluded_target(target: &cargo_metadata::Target) -> bool {
    target.kind.iter().any(|kind| {
        matches!(
            kind,
            cargo_metadata::TargetKind::CustomBuild
                | cargo_metadata::TargetKind::Example
                | cargo_metadata::TargetKind::Bench
        )
    })
}

fn add_conventional_tests(
    package_dir: &path::Path,
    mut targets: Vec<models::WorkspaceTarget>,
) -> Vec<models::WorkspaceTarget> {
    let tests = package_dir.join(constants::TESTS_DIRECTORY);
    if tests.is_dir()
        && !targets
            .iter()
            .any(|target| target.test && target.source_root == tests)
    {
        targets.push(models::WorkspaceTarget {
            source_root: tests,
            test: true,
        });
    }
    targets
}

fn discover_dependencies(
    repo_root: &path::Path,
    package: &cargo_metadata::Package,
    metadata: Option<&cargo_metadata::Metadata>,
) -> (Vec<models::WorkspaceDependency>, Vec<models::Violation>) {
    let package_manifest = package.manifest_path.as_std_path();
    let (mut dependencies, mut violations) = discover_declared_dependencies(repo_root, package);
    let Some(metadata) = metadata else {
        return (dependencies, violations);
    };
    let Some(resolve) = &metadata.resolve else {
        violations.push(manifest_setup_violation(
            repo_root,
            package_manifest,
            format!(
                "Cargo metadata omitted the resolved dependency graph for package {}",
                package.name
            ),
        ));
        return (dependencies, violations);
    };
    let Some(node) = resolve.nodes.iter().find(|node| node.id == package.id) else {
        violations.push(manifest_setup_violation(
            repo_root,
            package_manifest,
            format!(
                "Cargo metadata omitted the resolved dependency node for package {}",
                package.name
            ),
        ));
        return (dependencies, violations);
    };
    for dependency in &node.deps {
        let Some(resolved) = metadata
            .packages
            .iter()
            .find(|candidate| candidate.id == dependency.pkg)
        else {
            violations.push(manifest_setup_violation(
                repo_root,
                package_manifest,
                format!(
                    "Cargo metadata omitted resolved package {} for dependency {}",
                    dependency.pkg, dependency.name
                ),
            ));
            continue;
        };
        let (path, path_violations) =
            resolved_dependency_path(repo_root, package_manifest, resolved, &resolved.name);
        violations.extend(path_violations);
        dependencies.push(models::WorkspaceDependency {
            package_name: resolved.name.clone(),
            source_name: dependency.name.replace('-', "_"),
            path,
            resolved: true,
        });
    }
    dependencies.sort_by(|left, right| {
        left.package_name
            .cmp(&right.package_name)
            .then(left.source_name.cmp(&right.source_name))
    });
    dependencies.dedup();
    (dependencies, violations)
}

fn discover_declared_dependencies(
    repo_root: &path::Path,
    package: &cargo_metadata::Package,
) -> (Vec<models::WorkspaceDependency>, Vec<models::Violation>) {
    let package_manifest = package.manifest_path.as_std_path();
    let mut dependencies: Vec<models::WorkspaceDependency> = Vec::new();
    let mut violations: Vec<models::Violation> = Vec::new();
    for dependency in &package.dependencies {
        let (path, path_violations) = match &dependency.path {
            Some(value) => dependency_path(
                repo_root,
                package_manifest,
                value.as_std_path(),
                &dependency.name,
            ),
            None => (None, Vec::new()),
        };
        violations.extend(path_violations);
        let source_name = dependency
            .rename
            .as_ref()
            .unwrap_or(&dependency.name)
            .replace('-', "_");
        dependencies.push(models::WorkspaceDependency {
            package_name: dependency.name.clone(),
            source_name,
            path,
            resolved: false,
        });
    }
    dependencies.sort_by(|left, right| {
        left.package_name
            .cmp(&right.package_name)
            .then(left.source_name.cmp(&right.source_name))
    });
    dependencies.dedup();
    (dependencies, violations)
}

fn resolved_dependency_path(
    repo_root: &path::Path,
    package_manifest: &path::Path,
    resolved: &cargo_metadata::Package,
    source_name: &str,
) -> (Option<path::PathBuf>, Vec<models::Violation>) {
    if resolved.source.is_some() {
        return (None, Vec::new());
    }
    let Some(directory) = resolved.manifest_path.as_std_path().parent() else {
        return (
            None,
            vec![manifest_setup_violation(
                repo_root,
                package_manifest,
                format!("resolved dependency {source_name} has no manifest directory"),
            )],
        );
    };
    dependency_path(repo_root, package_manifest, directory, source_name)
}

fn dependency_path(
    repo_root: &path::Path,
    package_manifest: &path::Path,
    directory: &path::Path,
    source_name: &str,
) -> (Option<path::PathBuf>, Vec<models::Violation>) {
    match contained_canonical_path(repo_root, directory) {
        Ok(path) => (Some(path), Vec::new()),
        Err(error) => (
            None,
            vec![models::Violation::new(models::ViolationRequest {
                code: "RSL306",
                path: package_manifest
                    .strip_prefix(repo_root)
                    .unwrap_or(package_manifest),
                line: None,
                message: format!("path dependency {source_name} {error}"),
                remediation: "keep local dependencies canonically contained by the repository root",
            })],
        ),
    }
}

fn supported_target_entry(
    target: &cargo_metadata::Target,
    source_path: &path::Path,
    conventional_root: &path::Path,
    is_test: bool,
) -> bool {
    if is_test {
        return source_path.parent() == Some(conventional_root)
            && source_path.extension().and_then(|suffix| suffix.to_str())
                == Some(constants::RUST_SUFFIX);
    }
    if target
        .kind
        .iter()
        .any(|kind| matches!(kind, cargo_metadata::TargetKind::Bin))
    {
        return source_path == conventional_root.join(constants::MAIN_FILE)
            || source_path
                .strip_prefix(conventional_root.join(constants::BIN_DIRECTORY))
                .is_ok_and(|inside| {
                    inside.extension().and_then(|suffix| suffix.to_str())
                        == Some(constants::RUST_SUFFIX)
                        && inside.components().count() == constants::DIRECT_BIN_TARGET_COMPONENTS
                        || inside.file_name().and_then(|name| name.to_str())
                            == Some(constants::MAIN_FILE)
                            && inside.components().count()
                                == constants::NESTED_BIN_TARGET_COMPONENTS
                });
    }
    source_path == conventional_root.join(constants::LIB_FILE)
}

fn contained_canonical_path(
    root: &path::Path,
    candidate: &path::Path,
) -> Result<path::PathBuf, String> {
    let canonical = candidate
        .canonicalize()
        .map_err(|error| format!("path cannot be canonicalized: {error}"))?;
    if !canonical.starts_with(root) {
        return Err(format!(
            "path {} escapes the canonical root {}",
            canonical.display(),
            root.display()
        ));
    }
    Ok(canonical)
}

pub(crate) fn rust_files(repo_root: &path::Path, root: &path::Path) -> models::SourceScan {
    let mut files: Vec<models::SourceFile> = Vec::new();
    let mut violations: Vec<models::Violation> = Vec::new();
    if !root.exists() {
        return models::SourceScan { files, violations };
    }
    let canonical_root = match contained_canonical_path(repo_root, root) {
        Ok(value) => value,
        Err(error) => {
            violations.push(models::Violation::new(models::ViolationRequest {
                code: "RSH901",
                path: path::Path::new(&relative_display(repo_root, root)),
                line: None,
                message: format!("Rust source root {error}"),
                remediation: "keep Cargo source targets canonically contained by the repository",
            }));
            return models::SourceScan { files, violations };
        }
    };
    let mut paths: Vec<path::PathBuf> = Vec::new();
    for result in walkdir::WalkDir::new(&canonical_root).follow_links(false) {
        match result {
            Ok(entry) => {
                if entry.file_type().is_symlink() {
                    violations.push(models::Violation::new(models::ViolationRequest {
                        code: "RSH901",
                        path: path::Path::new(&relative_display(repo_root, entry.path())),
                        line: None,
                        message: "Rust source trees must not contain symlink entries".to_owned(),
                        remediation:
                            "replace the symlink with an owned repository source file or directory",
                    }));
                    continue;
                }
                let extension = entry.path().extension().and_then(|value| value.to_str());
                if entry.file_type().is_file() && extension == Some(constants::RUST_SUFFIX) {
                    paths.push(entry.path().to_path_buf());
                }
            }
            Err(error) => {
                let failed_path = error.path().unwrap_or(root);
                violations.push(models::Violation::new(models::ViolationRequest {
                    code: "RSH901",
                    path: path::Path::new(&relative_display(repo_root, failed_path)),
                    line: None,
                    message: format!("cannot traverse Rust source tree: {error}"),
                    remediation: "restore a readable source tree before checking structure",
                }));
            }
        }
    }
    paths.sort();
    for path in paths {
        match fs::read_to_string(&path) {
            Ok(source) => files.push(models::SourceFile {
                relative: relative_display(repo_root, &path),
                source_root_relative: relative_display(repo_root, &canonical_root),
                source_relative: relative_display(&canonical_root, &path),
                path,
                source,
            }),
            Err(error) => violations.push(models::Violation::new(models::ViolationRequest {
                code: "RSH901",
                path: path::Path::new(&relative_display(repo_root, &path)),
                line: None,
                message: format!("cannot read Rust source: {error}"),
                remediation: "restore a readable UTF-8 source file before checking structure",
            })),
        }
    }
    models::SourceScan { files, violations }
}

/// Scan all Cargo-discovered source roots of one package without duplicate files.
pub(crate) fn rust_target_files(
    repo_root: &path::Path,
    workspace_crate: &models::WorkspaceCrate,
    test: bool,
) -> models::SourceScan {
    let mut files: Vec<models::SourceFile> = Vec::new();
    let mut violations: Vec<models::Violation> = Vec::new();
    for target in workspace_crate
        .targets
        .iter()
        .filter(|target| target.test == test)
    {
        let scan = rust_files(repo_root, &target.source_root);
        files.extend(scan.files);
        violations.extend(scan.violations);
    }
    files.sort_by(|left, right| left.path.cmp(&right.path));
    files.dedup_by(|left, right| left.path == right.path);
    violations.sort_by(|left, right| left.sort_key().cmp(&right.sort_key()));
    violations.dedup_by(|left, right| left.sort_key() == right.sort_key());
    models::SourceScan { files, violations }
}

pub(crate) fn check_source_file(request: models::SourceCheckRequest<'_>) -> Vec<models::Violation> {
    let models::SourceCheckRequest {
        repo_root,
        src_root,
        file,
        config,
        dependencies,
        is_tooling_crate,
    } = request;
    if let Some(kind) = inline_test_file_kind(file) {
        return check_test_syntax(file, kind, config, dependencies);
    }
    let kind = source_file_kind(file, repo_root, src_root);
    let syntax = syn::parse_file(&file.source);
    let mut violations: Vec<models::Violation> = match syntax.as_ref() {
        Ok(syntax) => hygiene::check_source(file, Some(syntax), kind),
        Err(_) => hygiene::check_source(file, None, kind),
    };
    violations.extend(placement::check_common(file, &config.repository.thresholds));
    match syntax.as_ref() {
        Ok(syntax) => {
            violations.extend(tests_layout::check_source_scope(file, syntax));
            violations.extend(layers::check_uses(layers::UseCheckRequest {
                file,
                syntax,
                library_source: true,
                raw_parser_boundary: &config.raw_parser_boundary,
                dependencies,
            }));
            violations.extend(placement::check_source(
                file,
                syntax,
                kind,
                &config.repository.thresholds,
            ));
            violations.extend(containers::check_file(
                file,
                syntax,
                kind,
                &config.repository.thresholds,
            ));
            violations.extend(role_files::check(file, syntax, kind));
            violations.extend(naming::check(file, syntax));
            violations.extend(shape::check(models::SourceShapeCheckRequest {
                file,
                syntax,
                kind,
                is_tooling_crate,
                thresholds: &config.repository.thresholds,
            }));
        }
        Err(error) => violations.push(parse_violation(file, error)),
    }
    violations
}

pub(crate) fn check_test_file(request: models::TestCheckRequest<'_>) -> Vec<models::Violation> {
    let models::TestCheckRequest {
        repo_root,
        tests_root,
        file,
        config,
        dependencies,
    } = request;
    let kind = test_file_kind(file, repo_root, tests_root);
    check_test_syntax(file, kind, config, dependencies)
}

fn check_test_syntax(
    file: &models::SourceFile,
    kind: FileKind,
    config: &models::CheckerConfig,
    dependencies: &[models::WorkspaceDependency],
) -> Vec<models::Violation> {
    let syntax = syn::parse_file(&file.source);
    let mut violations: Vec<models::Violation> = match syntax.as_ref() {
        Ok(syntax) => hygiene::check_test_file(file, Some(syntax)),
        Err(_) => hygiene::check_test_file(file, None),
    };
    violations.extend(placement::check_common(file, &config.repository.thresholds));
    match syntax.as_ref() {
        Ok(syntax) => {
            violations.extend(layers::check_uses(layers::UseCheckRequest {
                file,
                syntax,
                library_source: false,
                raw_parser_boundary: &config.raw_parser_boundary,
                dependencies,
            }));
            violations.extend(tests_layout::check(file, syntax, kind));
            violations.extend(tests_shape::check(file, syntax, kind));
        }
        Err(error) => violations.push(parse_violation(file, error)),
    }
    violations
}

fn inline_test_file_kind(file: &models::SourceFile) -> Option<FileKind> {
    if file.file_name() == constants::INLINE_TEST_HARNESS_FILE
        && file.path.with_extension("").is_dir()
    {
        return Some(FileKind::TestHarness);
    }
    let tests_directory = file.path.ancestors().find(|path| {
        path.file_name().and_then(|name| name.to_str()) == Some(constants::TESTS_DIRECTORY)
            && path.with_extension("rs").is_file()
    })?;
    (file.path != tests_directory).then(|| match file.file_name() {
        "test_types.rs" => FileKind::TestTypes,
        "helpers.rs" => FileKind::TestHelpers,
        _ => FileKind::TestTopic,
    })
}

fn parse_violation(file: &models::SourceFile, error: &syn::Error) -> models::Violation {
    models::Violation::new(models::ViolationRequest {
        code: "RSH902",
        path: file.relative_path(),
        line: Some(error.span().start().line),
        message: format!("cannot parse Rust source: {error}"),
        remediation: "fix the syntax error before checking structure",
    })
}

pub(crate) fn manifest_setup_violation(
    repo_root: &path::Path,
    manifest_path: &path::Path,
    message: impl Into<String>,
) -> models::Violation {
    let relative = manifest_path
        .strip_prefix(repo_root)
        .unwrap_or(manifest_path);
    models::Violation::new(models::ViolationRequest {
        code: "RSL901",
        path: relative,
        line: None,
        message,
        remediation: "restore a readable, valid Cargo manifest before checking structure",
    })
}

fn workspace_lint_violations(
    repo_root: &path::Path,
    manifest_path: &path::Path,
    manifest: &toml::Value,
) -> Vec<models::Violation> {
    let relative = manifest_path
        .strip_prefix(repo_root)
        .unwrap_or(manifest_path);
    let mut violations: Vec<models::Violation> = Vec::new();
    let workspace = manifest.get(constants::WORKSPACE_KEY);
    let lint_root = workspace.and_then(|value| value.get(constants::LINTS_KEY));
    for (name, level) in constants::REQUIRED_RUST_LINTS {
        let actual = lint_root
            .and_then(|value| value.get(constants::RUST_KEY))
            .and_then(|value| value.get(*name))
            .and_then(toml::Value::as_str);
        if actual != Some(*level) {
            violations.push(models::Violation::new(models::ViolationRequest {
                code: "RSL303",
                path: relative,
                line: None,
                message: format!("workspace Rust lint {name} is not set to {level}"),
                remediation: "declare the required lint level under [workspace.lints.rust]",
            }));
        }
    }
    for (name, level) in constants::REQUIRED_CLIPPY_LINTS {
        let actual = lint_root
            .and_then(|value| value.get(constants::CLIPPY_KEY))
            .and_then(|value| value.get(*name))
            .and_then(toml::Value::as_str);
        if actual != Some(*level) {
            violations.push(models::Violation::new(models::ViolationRequest {
                code: "RSL303",
                path: relative,
                line: None,
                message: format!("workspace Clippy lint {name} is not set to {level}"),
                remediation: "declare the required lint level under [workspace.lints.clippy]",
            }));
        }
    }
    violations
}

pub(crate) fn relative_display(repo_root: &path::Path, path: &path::Path) -> String {
    let relative = path.strip_prefix(repo_root).unwrap_or(path);
    let parts: Vec<String> = relative
        .components()
        .map(|component| component.as_os_str().to_string_lossy().into_owned())
        .collect();
    parts.join("/")
}

fn source_file_kind(
    file: &models::SourceFile,
    repo_root: &path::Path,
    src_root: &path::Path,
) -> FileKind {
    let lib_root = relative_display(repo_root, &src_root.join(constants::LIB_FILE));
    let bin_adapter = relative_display(repo_root, &src_root.join(constants::MAIN_FILE));
    if file.relative == lib_root {
        return FileKind::LibraryRoot;
    }
    if file.relative == bin_adapter {
        return FileKind::BinAdapter;
    }
    if file
        .path
        .strip_prefix(src_root)
        .is_ok_and(|relative| relative.starts_with(constants::BIN_DIRECTORY))
    {
        return FileKind::BinAdapter;
    }
    if file.file_name() == constants::MOD_FILE {
        return FileKind::ModRoot;
    }
    FileKind::ModuleFile
}

fn test_file_kind(
    file: &models::SourceFile,
    repo_root: &path::Path,
    tests_root: &path::Path,
) -> FileKind {
    let tests_prefix = relative_display(repo_root, tests_root);
    let inside = file
        .relative
        .strip_prefix(&format!("{tests_prefix}/"))
        .unwrap_or(&file.relative);
    if !inside.contains('/') {
        return FileKind::TestHarness;
    }
    match file.file_name() {
        "test_types.rs" => FileKind::TestTypes,
        "helpers.rs" => FileKind::TestHelpers,
        _ => FileKind::TestTopic,
    }
}
