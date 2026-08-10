const ARTIFACT_DIRECTORIES: [&str; 6] = [
    "node_modules",
    ".svelte-kit",
    "build",
    "dist",
    "coverage",
    "__pycache__",
];
const AUXILIARY_PROJECT_INPUT_NAMES: [&str; 5] = [
    "package.json",
    "svelte.config.js",
    "svelte.config.cjs",
    "svelte.config.mjs",
    "svelte.config.ts",
];
const SVELTEKIT_DIRECTORY: &str = ".svelte-kit";
const TSCONFIG_FILE: &str = "tsconfig.json";
const RESOLUTION_EXTENSIONS: [&str; 12] = [
    "", ".ts", ".tsx", ".mts", ".cts", ".d.ts", ".d.mts", ".d.cts", ".js", ".jsx",
    ".mjs", ".cjs",
];

pub(crate) fn is_artifact_entry(entry: &DirEntry) -> bool {
    !entry.file_type().is_dir()
        || !ARTIFACT_DIRECTORIES.contains(&entry.file_name().to_string_lossy().as_ref())
}

pub(crate) fn is_web_source(path: &Path, analyzer: AnalyzerId) -> bool {
    let name = path
        .file_name()
        .and_then(|value| value.to_str())
        .unwrap_or_default();
    let supported = is_declaration_source(name)
        || matches!(
            path.extension().and_then(|value| value.to_str()),
            Some("ts" | "tsx" | "mts" | "cts" | "js" | "jsx" | "mjs" | "cjs")
        );
    supported || analyzer == AnalyzerId::Svelte && name.ends_with(".svelte")
}

pub(crate) fn is_direct_source(path: &Path, analyzer: AnalyzerId) -> bool {
    if analyzer == AnalyzerId::Svelte {
        return path.extension().and_then(|value| value.to_str()) == Some("svelte");
    }
    !path
        .file_name()
        .and_then(|value| value.to_str())
        .is_some_and(is_declaration_source)
}

pub(crate) fn is_web_test_source(path: &Path) -> bool {
    let name = path
        .file_name()
        .and_then(|value| value.to_str())
        .unwrap_or_default();
    if is_declaration_source(name) {
        return false;
    }
    let stem = [
        ".svelte.ts",
        ".svelte.js",
        ".tsx",
        ".jsx",
        ".mts",
        ".cts",
        ".mjs",
        ".cjs",
        ".ts",
        ".js",
    ]
    .iter()
    .find_map(|suffix| name.strip_suffix(suffix))
    .unwrap_or(name);
    stem.ends_with(".test") || stem.ends_with(".spec")
}

pub(crate) fn web_test_identity(path: &Path) -> Option<String> {
    let stem = web_module_stem(path.file_name()?.to_str()?);
    let identity = [".test", ".spec"]
        .iter()
        .find_map(|suffix| stem.strip_suffix(suffix))?;
    Some(
        [".integration", ".e2e"]
            .iter()
            .find_map(|scope| identity.strip_suffix(scope))
            .unwrap_or(identity)
            .to_owned(),
    )
}

pub(crate) fn web_source_identity(path: &Path) -> Option<String> {
    let stem = web_module_stem(path.file_name()?.to_str()?);
    Some(stem.strip_suffix(".svelte").unwrap_or(stem).to_owned())
}

fn web_module_stem(name: &str) -> &str {
    [
        ".svelte.ts",
        ".svelte.js",
        ".tsx",
        ".jsx",
        ".mts",
        ".cts",
        ".mjs",
        ".cjs",
        ".ts",
        ".js",
    ]
    .iter()
    .find_map(|suffix| name.strip_suffix(suffix))
    .unwrap_or(name)
}

fn is_declaration_source(name: &str) -> bool {
    name.ends_with(".d.ts") || name.ends_with(".d.mts") || name.ends_with(".d.cts")
}

pub(crate) fn discover_project_inputs(
    repository_root: &Path,
    project_root: &Path,
    config: &crate::models::Config,
) -> Result<Vec<ProjectInput>, String> {
    let repository_root = dunce::canonicalize(repository_root).map_err(|error| {
        format!(
            "Could not canonicalize repository root {}: {error}",
            repository_root.display()
        )
    })?;
    let project_root = dunce::canonicalize(project_root).map_err(|error| {
        format!(
            "Could not canonicalize target root {}: {error}",
            project_root.display()
        )
    })?;
    if relative_path(&project_root, &repository_root).is_none() {
        return Err(format!(
            "Target root escapes the repository: {}.",
            project_root.display()
        ));
    }
    let mut inputs: Vec<ProjectInput> = Vec::new();
    let mut loaded: HashSet<PathBuf> = HashSet::new();
    let mut visiting: Vec<PathBuf> = Vec::new();
    let optional_generated = (config.framework.as_deref() == Some("sveltekit"))
        .then(|| project_root.join(SVELTEKIT_DIRECTORY).join(TSCONFIG_FILE));
    let root_config = [TSCONFIG_FILE, "jsconfig.json"]
        .iter()
        .map(|name| project_root.join(name))
        .find(|path| path.is_file());
    if let Some(path) = root_config {
        collect_config_inputs(
            &repository_root,
            &project_root,
            &path,
            optional_generated.as_deref(),
            &mut loaded,
            &mut visiting,
            &mut inputs,
        )?;
    }
    let mut auxiliary_names = AUXILIARY_PROJECT_INPUT_NAMES
        .iter()
        .map(|name| (*name).to_owned())
        .collect::<Vec<_>>();
    auxiliary_names.extend(config.shadcn.iter().cloned());
    auxiliary_names.extend(config.openapi.iter().cloned());
    auxiliary_names.sort();
    auxiliary_names.dedup();
    for name in auxiliary_names {
        let path = project_root.join(&name);
        if !path.is_file() {
            if config.shadcn.as_deref() == Some(&name) || config.openapi.as_deref() == Some(&name) {
                return Err(format!("Configured target-local web dependency does not exist: {name}."));
            }
            continue;
        }
        let canonical_path = dunce::canonicalize(&path).map_err(|error| error.to_string())?;
        if relative_path(&canonical_path, &project_root).is_none() {
            return Err(format!(
                "Configured target-local web dependency escapes the target: {name}."
            ));
        }
        let content = fs::read(&path).map_err(|error| error.to_string())?;
        if config.shadcn.as_deref() == Some(&name) || config.openapi.as_deref() == Some(&name) {
            serde_json::from_slice::<Value>(&content).map_err(|error| {
                format!("Could not parse target-local web dependency {name}: {error}")
            })?;
        }
        inputs.push(ProjectInput {
            path: canonical_path.clone(),
            extended_configs: Vec::new(),
            repository_path: relative_text(&canonical_path, &repository_root)?,
            target_path: relative_text(&canonical_path, &project_root)?,
            fingerprint: hex_digest(&content),
            content,
            present: true,
        });
    }
    if let Some(ui_kit) = config.ui_kit.as_deref() {
        let path = project_root.join(ui_kit);
        if path.exists() {
            let canonical_path = dunce::canonicalize(&path).map_err(|error| error.to_string())?;
            if relative_path(&canonical_path, &project_root).is_none() {
                return Err(format!(
                    "Configured target-local UI-kit path escapes the target: {ui_kit}."
                ));
            }
        }
    }
    inputs.sort_by(|left, right| left.repository_path.cmp(&right.repository_path));
    Ok(inputs)
}

fn collect_config_inputs(
    repository_root: &Path,
    project_root: &Path,
    path: &Path,
    optional_generated: Option<&Path>,
    loaded: &mut HashSet<PathBuf>,
    visiting: &mut Vec<PathBuf>,
    inputs: &mut Vec<ProjectInput>,
) -> Result<(), String> {
    let repository_root = dunce::canonicalize(repository_root).map_err(|error| {
        format!(
            "Could not canonicalize repository root {}: {error}",
            repository_root.display()
        )
    })?;
    let path = canonicalize_config_path(&repository_root, path)?;
    let repository_path = relative_text(&path, &repository_root).map_err(|_| {
        format!(
            "TypeScript config escapes the repository: {}.",
            path.display()
        )
    })?;
    if let Some(index) = visiting.iter().position(|candidate| candidate == &path) {
        let mut cycle = visiting[index..]
            .iter()
            .map(|candidate| relative_text(candidate, &repository_root))
            .collect::<Result<Vec<_>, _>>()?;
        cycle.push(repository_path);
        return Err(format!(
            "TypeScript config extends cycle: {}.",
            cycle.join(" -> ")
        ));
    }
    if loaded.contains(&path) {
        return Ok(());
    }
    let content = fs::read(&path).map_err(|error| {
        format!(
            "Could not read TypeScript config {repository_path}: {error}"
        )
    })?;
    let parsed = parse_jsonc(&content, &repository_path)?;
    let extends = config_extends(&parsed, &repository_path)?;
    visiting.push(path.clone());
    let mut extended_configs: Vec<PathBuf> = Vec::new();
    for specifier in extends {
        let resolved = resolve_config_extends(
            &repository_root,
            &path,
            specifier,
            optional_generated,
        )?;
        match resolved {
            ResolvedConfigExtends::Present(path) => {
                collect_config_inputs(
                    &repository_root,
                    project_root,
                    &path,
                    optional_generated,
                    loaded,
                    visiting,
                    inputs,
                )?;
                extended_configs.push(path);
            }
            ResolvedConfigExtends::OptionalMissing(path) => {
                if loaded.insert(path.clone()) {
                    let repository_path = relative_text(&path, &repository_root)?;
                    inputs.push(ProjectInput {
                        path: path.clone(),
                        extended_configs: Vec::new(),
                        repository_path,
                        target_path: relative_text(&path, project_root)?,
                        content: b"{}".to_vec(),
                        fingerprint: hex_digest(b"fensu-optional-generated-config-missing-v1"),
                        present: false,
                    });
                }
                extended_configs.push(path);
            }
        }
    }
    let _ = visiting.pop();
    loaded.insert(path.clone());
    inputs.push(ProjectInput {
        path: path.clone(),
        extended_configs,
        repository_path: repository_path.clone(),
        target_path: relative_text(&path, project_root)?,
        fingerprint: hex_digest(&content),
        content,
        present: true,
    });
    Ok(())
}

fn config_extends<'a>(parsed: &'a Value, path: &str) -> Result<Vec<&'a str>, String> {
    let Some(value) = parsed.get("extends") else {
        return Ok(Vec::new());
    };
    if let Some(value) = value.as_str() {
        return Ok(vec![value]);
    }
    let values = value.as_array().ok_or_else(|| {
        format!("TypeScript config {path} key extends must be a string or array of strings.")
    })?;
    let mut extends: Vec<&str> = Vec::with_capacity(values.len());
    for (index, value) in values.iter().enumerate() {
        extends.push(value.as_str().ok_or_else(|| {
            format!(
                "TypeScript config {path} key extends item {index} must be a string."
            )
        })?);
    }
    Ok(extends)
}

enum ResolvedConfigExtends {
    Present(PathBuf),
    OptionalMissing(PathBuf),
}

fn resolve_config_extends(
    repository_root: &Path,
    config: &Path,
    specifier: &str,
    optional_generated: Option<&Path>,
) -> Result<ResolvedConfigExtends, String> {
    let parent = config
        .parent()
        .ok_or_else(|| format!("TypeScript config has no parent: {}.", config.display()))?;
    let mut bases: Vec<PathBuf> = Vec::new();
    if specifier.starts_with('.') {
        bases.push(parent.join(specifier));
    } else if Path::new(specifier).is_absolute() {
        bases.push(PathBuf::from(specifier));
    } else {
        for ancestor in parent.ancestors() {
            if relative_path(ancestor, repository_root).is_none() {
                break;
            }
            bases.push(ancestor.join("node_modules").join(specifier));
        }
    }
    for base in bases {
        for candidate in config_candidates(&base) {
            let canonical = canonicalize_config_path(repository_root, &candidate)?;
            if canonical.is_file() {
                return Ok(ResolvedConfigExtends::Present(canonical));
            }
            if optional_generated.is_some_and(|optional| canonical == optional) {
                return Ok(ResolvedConfigExtends::OptionalMissing(canonical));
            }
        }
    }
    let owner = relative_text(config, repository_root)
        .unwrap_or_else(|_| config.to_string_lossy().into_owned());
    Err(format!(
        "Could not resolve TypeScript config extends {specifier:?} from {owner}."
    ))
}

fn canonicalize_config_path(repository_root: &Path, path: &Path) -> Result<PathBuf, String> {
    let mut existing = path;
    let mut missing: Vec<std::ffi::OsString> = Vec::new();
    while !existing.exists() {
        let name = existing.file_name().ok_or_else(|| {
            format!(
                "Could not resolve TypeScript config path: {}.",
                path.display()
            )
        })?;
        missing.push(name.to_os_string());
        existing = existing.parent().ok_or_else(|| {
            format!(
                "Could not resolve TypeScript config path: {}.",
                path.display()
            )
        })?;
    }
    let mut canonical = dunce::canonicalize(existing).map_err(|error| {
        format!(
            "Could not canonicalize TypeScript config path {}: {error}",
            existing.display()
        )
    })?;
    for part in missing.into_iter().rev() {
        canonical.push(part);
    }
    canonical = normalize(&canonical);
    if relative_path(&canonical, repository_root).is_none() {
        return Err(format!(
            "TypeScript config path escapes the repository: {}.",
            path.display()
        ));
    }
    Ok(canonical)
}

fn config_candidates(base: &Path) -> Vec<PathBuf> {
    let mut candidates = vec![base.to_path_buf()];
    if base.extension().and_then(|value| value.to_str()) != Some("json") {
        let mut with_extension = base.as_os_str().to_os_string();
        with_extension.push(".json");
        candidates.push(PathBuf::from(with_extension));
    }
    candidates.push(base.join("tsconfig.json"));
    candidates
}

fn parse_jsonc(content: &[u8], path: &str) -> Result<Value, String> {
    let normalized = normalize_jsonc(content, path)?;
    let parsed: Value = serde_json::from_slice(&normalized).map_err(|error| {
        format!("Could not parse TypeScript config {path}: {error}")
    })?;
    if !parsed.is_object() {
        return Err(format!(
            "TypeScript config {path} must contain a JSON object."
        ));
    }
    Ok(parsed)
}

fn normalize_jsonc(content: &[u8], path: &str) -> Result<Vec<u8>, String> {
    let mut normalized = content.to_vec();
    let mut index = 0;
    let mut in_string = false;
    let mut escaped = false;
    while index < normalized.len() {
        let byte = normalized[index];
        if in_string {
            if escaped {
                escaped = false;
            } else if byte == b'\\' {
                escaped = true;
            } else if byte == b'"' {
                in_string = false;
            }
            index += 1;
            continue;
        }
        if byte == b'"' {
            in_string = true;
            index += 1;
            continue;
        }
        if normalized[index..].starts_with(b"//") {
            normalized[index] = b' ';
            normalized[index + 1] = b' ';
            index += 2;
            while index < normalized.len() && normalized[index] != b'\n' {
                if normalized[index] != b'\r' {
                    normalized[index] = b' ';
                }
                index += 1;
            }
            continue;
        }
        if normalized[index..].starts_with(b"/*") {
            let start = index;
            normalized[index] = b' ';
            normalized[index + 1] = b' ';
            index += 2;
            let mut terminated = false;
            while index < normalized.len() {
                if normalized[index..].starts_with(b"*/") {
                    normalized[index] = b' ';
                    normalized[index + 1] = b' ';
                    index += 2;
                    terminated = true;
                    break;
                }
                if !matches!(normalized[index], b'\n' | b'\r') {
                    normalized[index] = b' ';
                }
                index += 1;
            }
            if !terminated {
                let line = content[..start].iter().filter(|byte| **byte == b'\n').count() + 1;
                return Err(format!(
                    "Could not parse TypeScript config {path}: unterminated block comment at line {line}."
                ));
            }
            continue;
        }
        index += 1;
    }
    strip_trailing_commas(&mut normalized);
    Ok(normalized)
}

fn strip_trailing_commas(content: &mut [u8]) {
    let mut in_string = false;
    let mut escaped = false;
    for index in 0..content.len() {
        let byte = content[index];
        if in_string {
            if escaped {
                escaped = false;
            } else if byte == b'\\' {
                escaped = true;
            } else if byte == b'"' {
                in_string = false;
            }
            continue;
        }
        if byte == b'"' {
            in_string = true;
            continue;
        }
        if byte != b',' {
            continue;
        }
        let next = content[index + 1..]
            .iter()
            .copied()
            .find(|candidate| !candidate.is_ascii_whitespace());
        if matches!(next, Some(b'}' | b']')) {
            content[index] = b' ';
        }
    }
}

pub(crate) fn parse_sources(
    analyzer: AnalyzerId,
    project_root: &Path,
    mut sources: Vec<ScopedSource>,
    project_inputs: &[ProjectInput],
    source_roots: &[String],
) -> Result<Vec<ScopedSource>, String> {
    let project_root = dunce::canonicalize(project_root).map_err(|error| {
        format!(
            "Could not canonicalize target root {}: {error}",
            project_root.display()
        )
    })?;
    let source_roots = canonical_source_roots(&project_root, source_roots)?;
    for source in sources.iter_mut() {
        source.program = Some(parse_source(analyzer, source)?);
    }
    populate_import_graph(&project_root, sources, project_inputs, &source_roots)
}

fn canonical_source_roots(
    project_root: &Path,
    configured_roots: &[String],
) -> Result<Vec<PathBuf>, String> {
    let mut roots: Vec<PathBuf> = Vec::with_capacity(configured_roots.len());
    for configured in configured_roots {
        let candidate = project_root.join(configured);
        let resolved = if candidate.exists() {
            dunce::canonicalize(&candidate).map_err(|error| {
                format!("Could not canonicalize web source root {configured}: {error}")
            })?
        } else {
            normalize(&candidate)
        };
        if relative_path(&resolved, project_root).is_none() {
            return Err(format!(
                "Web source root escapes the target: {configured}."
            ));
        }
        roots.push(resolved);
    }
    Ok(roots)
}

fn parse_source(analyzer: AnalyzerId, source: &ScopedSource) -> Result<ParsedProgram, String> {
    if source.path.extension().and_then(|value| value.to_str()) == Some("svelte") {
        if analyzer != AnalyzerId::Svelte {
            return Err(format!(
                "Parser dispatch rejected unsupported TypeScript source: {}",
                source.repository_path
            ));
        }
        return Ok(fensu_svelte::parse(&source.content)
            .map(ParsedProgram::Svelte)
            .unwrap_or_else(|diagnostic| ParsedProgram::Malformed(WebParseFailure {
                message: diagnostic.message,
                line: diagnostic.span.line as u32,
                column: diagnostic.span.column as u32,
            })));
    }
    let kind = source_kind(&source.path).ok_or_else(|| {
        format!(
            "Parser dispatch rejected unsupported {analyzer} source: {}",
            source.repository_path
        )
    })?;
    Ok(fensu_typescript::parse(&source.content, kind)
        .map(Box::new)
        .map(ParsedProgram::TypeScript)
        .unwrap_or_else(|diagnostic| ParsedProgram::Malformed(WebParseFailure {
            message: diagnostic.message,
            line: diagnostic.span.line as u32,
            column: diagnostic.span.column as u32,
        })))
}

pub(crate) fn source_kind(path: &Path) -> Option<fensu_typescript::SourceKind> {
    let name = path.file_name()?.to_str()?;
    if name.ends_with(".d.mts") {
        Some(fensu_typescript::SourceKind::TypeScriptModuleDefinition)
    } else if name.ends_with(".d.cts") {
        Some(fensu_typescript::SourceKind::TypeScriptCommonJsDefinition)
    } else if name.ends_with(".d.ts") {
        Some(fensu_typescript::SourceKind::TypeScriptDefinition)
    } else if name.ends_with(".mts") {
        Some(fensu_typescript::SourceKind::TypeScriptModule)
    } else if name.ends_with(".cts") {
        Some(fensu_typescript::SourceKind::TypeScriptCommonJs)
    } else if name.ends_with(".ts") {
        Some(fensu_typescript::SourceKind::TypeScript)
    } else if name.ends_with(".tsx") {
        Some(fensu_typescript::SourceKind::TypeScriptJsx)
    } else if name.ends_with(".mjs") {
        Some(fensu_typescript::SourceKind::JavaScriptModule)
    } else if name.ends_with(".cjs") {
        Some(fensu_typescript::SourceKind::JavaScriptCommonJs)
    } else if name.ends_with(".js") {
        Some(fensu_typescript::SourceKind::JavaScript)
    } else if name.ends_with(".jsx") {
        Some(fensu_typescript::SourceKind::JavaScriptJsx)
    } else {
        None
    }
}

fn populate_import_graph(
    project_root: &Path,
    mut sources: Vec<ScopedSource>,
    project_inputs: &[ProjectInput],
    source_roots: &[PathBuf],
) -> Result<Vec<ScopedSource>, String> {
    let mut known: HashMap<PathBuf, String> = HashMap::new();
    for source in &sources {
        let path = dunce::canonicalize(&source.path).map_err(|error| {
            format!(
                "Could not canonicalize web source {}: {error}",
                source.path.display()
            )
        })?;
        if relative_path(&path, project_root).is_none() {
            return Err(format!(
                "Web source escapes the target: {}.",
                source.path.display()
            ));
        }
        known.insert(path, source.target_path.clone());
    }
    let aliases = aliases(project_root, project_inputs)?;
    let resolution = ResolutionContext {
        project_root,
        known: &known,
        aliases: &aliases,
        source_roots,
    };
    for source in &mut sources {
        let specifiers = import_specifiers(source);
        let importer = dunce::canonicalize(&source.path).map_err(|error| {
            format!(
                "Could not canonicalize web source {}: {error}",
                source.path.display()
            )
        })?;
        source.imports = specifiers
            .into_iter()
            .map(|specifier| {
                Ok(ImportGraphFact {
                    resolved_path: resolve_import(&specifier, &importer, &resolution)?,
                    specifier,
                })
            })
            .collect::<Result<Vec<_>, String>>()?;
    }
    Ok(sources)
}

fn import_specifiers(source: &ScopedSource) -> Vec<String> {
    let mut specifiers = if let Some(program) = source
        .program
        .as_ref()
        .and_then(ParsedProgram::as_typescript)
    {
        program
            .imports
            .iter()
            .map(|fact| fact.specifier.clone())
            .collect()
    } else if let Some(program) = source.program.as_ref().and_then(ParsedProgram::as_svelte) {
        program
            .scripts
            .iter()
            .flat_map(|script| script.facts.imports.iter())
            .map(|fact| fact.specifier.clone())
            .collect()
    } else {
        Vec::new()
    };
    specifiers.sort();
    specifiers.dedup();
    specifiers
}

#[derive(Debug)]
struct AliasConfig {
    base: Option<PathBuf>,
    paths: Vec<AliasPath>,
    paths_defined: bool,
    dynamic_paths: Vec<DynamicAlias>,
    unknown_dynamic: Option<String>,
}

#[derive(Debug)]
struct AliasPath {
    pattern: String,
    targets: Vec<PathBuf>,
}

#[derive(Debug)]
struct DynamicAlias {
    pattern: String,
    config_path: String,
}

fn aliases(project_root: &Path, inputs: &[ProjectInput]) -> Result<AliasConfig, String> {
    let mut root: Option<(PathBuf, &ProjectInput)> = None;
    for name in ["tsconfig.json", "jsconfig.json"] {
        let candidate = project_root.join(name);
        if !candidate.is_file() {
            continue;
        }
        let canonical = dunce::canonicalize(&candidate).map_err(|error| {
            format!(
                "Could not canonicalize TypeScript config {}: {error}",
                candidate.display()
            )
        })?;
        root = inputs.iter().find_map(|input| {
            let identity = project_input_identity(&input.path);
            (identity == canonical).then_some((identity, input))
        });
        break;
    }
    let mut config = if let Some((root_path, root)) = root {
        let by_path = inputs
            .iter()
            .map(|input| (project_input_identity(&input.path), input))
            .collect::<HashMap<_, _>>();
        effective_aliases(&root_path, root, &by_path)?
    } else {
        AliasConfig {
            base: None,
            paths: Vec::new(),
            paths_defined: false,
            dynamic_paths: Vec::new(),
            unknown_dynamic: None,
        }
    };
    merge_svelte_config_aliases(project_root, inputs, &mut config)?;
    Ok(config)
}

fn project_input_identity(path: &Path) -> PathBuf {
    dunce::canonicalize(path).unwrap_or_else(|_| normalize(path))
}

fn effective_aliases(
    input_path: &Path,
    input: &ProjectInput,
    by_path: &HashMap<PathBuf, &ProjectInput>,
) -> Result<AliasConfig, String> {
    let mut config = AliasConfig {
        base: None,
        paths: Vec::new(),
        paths_defined: false,
        dynamic_paths: Vec::new(),
        unknown_dynamic: None,
    };
    for path in &input.extended_configs {
        let parent_path = project_input_identity(path);
        let parent = by_path.get(&parent_path).ok_or_else(|| {
            format!(
                "Extended TypeScript config was not discovered: {}.",
                path.display()
            )
        })?;
        merge_aliases(
            &mut config,
            effective_aliases(&parent_path, parent, by_path)?,
        );
    }
    let parsed = parse_jsonc(&input.content, &input.repository_path)?;
    let Some(compiler) = parsed.get("compilerOptions") else {
        return Ok(config);
    };
    let compiler = compiler.as_object().ok_or_else(|| {
        format!(
            "TypeScript config {} key compilerOptions must be an object.",
            input.repository_path
        )
    })?;
    if let Some(value) = compiler.get("baseUrl") {
        let value = value.as_str().ok_or_else(|| {
            format!(
                "TypeScript config {} key compilerOptions.baseUrl must be a string.",
                input.repository_path
            )
        })?;
        let parent = input_path.parent().ok_or_else(|| {
            format!("TypeScript config has no parent: {}.", input.repository_path)
        })?;
        config.base = Some(normalize(&parent.join(value)));
    }
    if let Some(value) = compiler.get("paths") {
        let values = value.as_object().ok_or_else(|| {
            format!(
                "TypeScript config {} key compilerOptions.paths must be an object.",
                input.repository_path
            )
        })?;
        let fallback = input_path.parent().ok_or_else(|| {
            format!("TypeScript config has no parent: {}.", input.repository_path)
        })?;
        let target_base = config.base.as_deref().unwrap_or(fallback);
        let mut paths: Vec<AliasPath> = Vec::new();
        for (pattern, value) in values {
            let targets = value.as_array().ok_or_else(|| {
                format!(
                    "TypeScript config {} path alias {pattern:?} must be an array of strings.",
                    input.repository_path
                )
            })?;
            let mut resolved_targets: Vec<PathBuf> = Vec::new();
            for target in targets {
                let target = target.as_str().ok_or_else(|| {
                    format!(
                        "TypeScript config {} path alias {pattern:?} must contain only strings.",
                        input.repository_path
                    )
                })?;
                resolved_targets.push(normalize(&target_base.join(target)));
            }
            paths.push(AliasPath {
                pattern: pattern.clone(),
                targets: resolved_targets,
            });
        }
        paths.sort_by(alias_specificity);
        config.paths = paths;
        config.paths_defined = true;
    }
    Ok(config)
}

fn merge_aliases(config: &mut AliasConfig, base: AliasConfig) {
    if base.base.is_some() {
        config.base = base.base;
    }
    if base.paths_defined {
        config.paths = base.paths;
        config.paths_defined = true;
    }
    config.dynamic_paths.extend(base.dynamic_paths);
    if base.unknown_dynamic.is_some() {
        config.unknown_dynamic = base.unknown_dynamic;
    }
}

fn merge_svelte_config_aliases(
    project_root: &Path,
    inputs: &[ProjectInput],
    config: &mut AliasConfig,
) -> Result<(), String> {
    for input in inputs.iter().filter(|input| {
        input
            .path
            .file_name()
            .and_then(|name| name.to_str())
            .is_some_and(|name| AUXILIARY_PROJECT_INPUT_NAMES[1..].contains(&name))
    }) {
        let parsed = parse_svelte_aliases(&input.content, &input.repository_path)?;
        for (pattern, target) in parsed.literal {
            let resolved = normalize(&project_root.join(target));
            config.paths.retain(|alias| {
                alias.pattern != pattern && alias.pattern != format!("{pattern}/*")
            });
            config.paths.push(AliasPath {
                pattern: pattern.clone(),
                targets: vec![resolved.clone()],
            });
            config.paths.push(AliasPath {
                pattern: format!("{pattern}/*"),
                targets: vec![resolved.join("*")],
            });
        }
        config.dynamic_paths.extend(
            parsed
                .dynamic
                .into_iter()
                .map(|pattern| DynamicAlias {
                    pattern,
                    config_path: input.repository_path.clone(),
                }),
        );
        if parsed.unknown_dynamic {
            config.unknown_dynamic = Some(input.repository_path.clone());
        }
    }
    config.paths.sort_by(alias_specificity);
    Ok(())
}

#[derive(Default)]
struct ParsedSvelteAliases {
    literal: Vec<(String, String)>,
    dynamic: Vec<String>,
    unknown_dynamic: bool,
}

#[derive(Clone)]
struct JsToken {
    text: String,
    literal: bool,
}

fn parse_svelte_aliases(content: &[u8], path: &str) -> Result<ParsedSvelteAliases, String> {
    let source = std::str::from_utf8(content)
        .map_err(|_| format!("Could not parse Svelte config {path}: source is not valid UTF-8."))?;
    let tokens = tokenize_javascript(source, path)?;
    for index in 0..tokens.len().saturating_sub(2) {
        if tokens[index].text != "kit"
            || tokens[index + 1].text != ":"
            || tokens[index + 2].text != "{"
        {
            continue;
        }
        let end = matching_token(&tokens, index + 2, "{", "}")?;
        for alias_index in index + 3..end.saturating_sub(1) {
            if tokens[alias_index].text != "alias"
                || tokens.get(alias_index + 1).map(|token| token.text.as_str()) != Some(":")
            {
                continue;
            }
            let value_index = alias_index + 2;
            if tokens.get(value_index).map(|token| token.text.as_str()) != Some("{") {
                return Ok(ParsedSvelteAliases {
                    unknown_dynamic: true,
                    ..ParsedSvelteAliases::default()
                });
            }
            return parse_svelte_alias_object(&tokens, value_index);
        }
    }
    Ok(ParsedSvelteAliases::default())
}

fn parse_svelte_alias_object(
    tokens: &[JsToken],
    start: usize,
) -> Result<ParsedSvelteAliases, String> {
    let end = matching_token(tokens, start, "{", "}")?;
    let mut parsed = ParsedSvelteAliases::default();
    let mut index = start + 1;
    while index < end {
        if tokens[index].text == "," {
            index += 1;
            continue;
        }
        if tokens[index].text == "..." {
            parsed.unknown_dynamic = true;
            index = next_object_entry(tokens, index + 1, end);
            continue;
        }
        let key = tokens[index].text.clone();
        if tokens.get(index + 1).map(|token| token.text.as_str()) != Some(":") {
            parsed.unknown_dynamic = true;
            index = next_object_entry(tokens, index + 1, end);
            continue;
        }
        let value_index = index + 2;
        if let Some(value) = tokens.get(value_index).filter(|token| token.literal) {
            parsed.literal.push((key, value.text.clone()));
        } else {
            parsed.dynamic.push(key);
        }
        index = next_object_entry(tokens, value_index + 1, end);
    }
    Ok(parsed)
}

fn next_object_entry(tokens: &[JsToken], mut index: usize, end: usize) -> usize {
    let mut depth = 0usize;
    while index < end {
        match tokens[index].text.as_str() {
            "{" | "[" | "(" => depth += 1,
            "}" | "]" | ")" if depth > 0 => depth -= 1,
            "," if depth == 0 => return index + 1,
            _ => {}
        }
        index += 1;
    }
    end
}

fn matching_token(
    tokens: &[JsToken],
    start: usize,
    open: &str,
    close: &str,
) -> Result<usize, String> {
    let mut depth = 0usize;
    for (index, token) in tokens.iter().enumerate().skip(start) {
        if token.text == open {
            depth += 1;
        } else if token.text == close {
            depth -= 1;
            if depth == 0 {
                return Ok(index);
            }
        }
    }
    Err("Svelte config contains an unterminated object literal.".to_owned())
}

fn tokenize_javascript(source: &str, path: &str) -> Result<Vec<JsToken>, String> {
    let bytes = source.as_bytes();
    let mut tokens = Vec::new();
    let mut index = 0usize;
    while index < bytes.len() {
        if bytes[index].is_ascii_whitespace() {
            index += 1;
        } else if bytes[index..].starts_with(b"//") {
            index += 2;
            while index < bytes.len() && bytes[index] != b'\n' {
                index += 1;
            }
        } else if bytes[index..].starts_with(b"/*") {
            let Some(offset) = bytes[index + 2..].windows(2).position(|value| value == b"*/") else {
                return Err(format!("Could not parse Svelte config {path}: unterminated block comment."));
            };
            index += offset + 4;
        } else if matches!(bytes[index], b'\'' | b'"' | b'`') {
            let quote = bytes[index];
            let start = index + 1;
            index += 1;
            let mut escaped = false;
            let mut dynamic = false;
            while index < bytes.len() {
                if escaped {
                    escaped = false;
                } else if bytes[index] == b'\\' {
                    escaped = true;
                } else if bytes[index] == quote {
                    break;
                } else if quote == b'`' && bytes[index..].starts_with(b"${") {
                    dynamic = true;
                }
                index += 1;
            }
            if index == bytes.len() {
                return Err(format!("Could not parse Svelte config {path}: unterminated string literal."));
            }
            tokens.push(JsToken {
                text: unescape_javascript_string(&source[start..index]),
                literal: !dynamic,
            });
            index += 1;
        } else if bytes[index..].starts_with(b"...") {
            tokens.push(JsToken {
                text: "...".to_owned(),
                literal: false,
            });
            index += 3;
        } else if bytes[index].is_ascii_alphanumeric()
            || matches!(bytes[index], b'_' | b'$')
        {
            let start = index;
            index += 1;
            while index < bytes.len()
                && (bytes[index].is_ascii_alphanumeric()
                    || matches!(bytes[index], b'_' | b'$'))
            {
                index += 1;
            }
            tokens.push(JsToken {
                text: source[start..index].to_owned(),
                literal: false,
            });
        } else {
            tokens.push(JsToken {
                text: char::from(bytes[index]).to_string(),
                literal: false,
            });
            index += 1;
        }
    }
    Ok(tokens)
}

fn unescape_javascript_string(value: &str) -> String {
    let mut decoded = String::new();
    let mut escaped = false;
    for character in value.chars() {
        if escaped {
            decoded.push(character);
            escaped = false;
        } else if character == '\\' {
            escaped = true;
        } else {
            decoded.push(character);
        }
    }
    if escaped {
        decoded.push('\\');
    }
    decoded
}

fn alias_specificity(left: &AliasPath, right: &AliasPath) -> std::cmp::Ordering {
    let left_wildcard = left.pattern.find('*');
    let right_wildcard = right.pattern.find('*');
    match (left_wildcard, right_wildcard) {
        (None, None) => left.pattern.cmp(&right.pattern),
        (None, Some(_)) => std::cmp::Ordering::Less,
        (Some(_), None) => std::cmp::Ordering::Greater,
        (Some(left_prefix), Some(right_prefix)) => right_prefix
            .cmp(&left_prefix)
            .then_with(|| right.pattern.len().cmp(&left.pattern.len()))
            .then_with(|| left.pattern.cmp(&right.pattern)),
    }
}

struct ResolutionContext<'a> {
    project_root: &'a Path,
    known: &'a HashMap<PathBuf, String>,
    aliases: &'a AliasConfig,
    source_roots: &'a [PathBuf],
}

fn resolve_import(
    specifier: &str,
    importer: &Path,
    resolution: &ResolutionContext<'_>,
) -> Result<Option<String>, String> {
    if relative_path(importer, resolution.project_root).is_none() {
        return Err(format!(
            "Web importer escapes the target: {}.",
            importer.display()
        ));
    }
    let mut candidates: Vec<PathBuf> = Vec::new();
    let relative = specifier.starts_with("./") || specifier.starts_with("../");
    if relative {
        let Some(parent) = importer.parent() else {
            return Ok(None);
        };
        candidates.push(parent.join(specifier));
    } else if specifier == "$lib" || specifier.starts_with("$lib/") {
        let rest = specifier.strip_prefix("$lib/").unwrap_or_default();
        if let Some(root) = resolution
            .source_roots
            .iter()
            .filter(|root| relative_path(importer, root).is_some())
            .max_by_key(|root| root.components().count())
        {
            candidates.push(root.join("lib").join(rest));
        }
    } else {
        for alias in &resolution.aliases.paths {
            let Some(capture) = alias_capture(&alias.pattern, specifier) else {
                continue;
            };
            for target in &alias.targets {
                candidates.push(alias_target(target, capture));
            }
            break;
        }
        if let Some(base) = &resolution.aliases.base {
            candidates.push(base.join(specifier));
        }
    }
    for candidate in candidates {
        for path in resolution_candidates(&candidate) {
            let identity = if path.exists() {
                dunce::canonicalize(&path).map_err(|error| {
                    format!(
                        "Could not canonicalize web import candidate {}: {error}",
                        path.display()
                    )
                })?
            } else {
                normalize(&path)
            };
            if relative_path(&identity, resolution.project_root).is_none() {
                return Err(format!(
                    "Web import candidate escapes the target: {}.",
                    path.display()
                ));
            }
            if let Some(resolved) = resolution.known.get(&identity) {
                return Ok(Some(resolved.clone()));
            }
        }
    }
    if let Some(dynamic) = resolution
        .aliases
        .dynamic_paths
        .iter()
        .find(|alias| alias_matches(&alias.pattern, specifier))
    {
        return Err(format!(
            "SvelteKit alias {:?} in {} uses a dynamic value required to resolve import {:?}; use a literal kit.alias value.",
            dynamic.pattern, dynamic.config_path, specifier
        ));
    }
    if specifier.starts_with('$') {
        if let Some(path) = &resolution.aliases.unknown_dynamic {
            return Err(format!(
                "SvelteKit aliases in {path} are dynamic and import {specifier:?} cannot be resolved statically; use literal kit.alias entries."
            ));
        }
    }
    Ok(None)
}

fn alias_matches(pattern: &str, specifier: &str) -> bool {
    alias_capture(pattern, specifier).is_some()
        || pattern == specifier
        || specifier
            .strip_prefix(pattern)
            .is_some_and(|rest| rest.starts_with('/'))
}

fn alias_capture<'a>(pattern: &str, specifier: &'a str) -> Option<&'a str> {
    match pattern.split_once('*') {
        Some((prefix, suffix)) => specifier
            .strip_prefix(prefix)
            .and_then(|value| value.strip_suffix(suffix)),
        None if pattern == specifier => Some(""),
        None => None,
    }
}

fn resolution_candidates(path: &Path) -> Vec<PathBuf> {
    if let Some(candidates) = explicit_javascript_candidates(path) {
        return candidates;
    }
    let mut candidates = RESOLUTION_EXTENSIONS
        .iter()
        .map(|extension| {
            let mut candidate = path.as_os_str().to_os_string();
            candidate.push(extension);
            PathBuf::from(candidate)
        })
        .collect::<Vec<_>>();
    candidates.extend(
        RESOLUTION_EXTENSIONS
            .iter()
            .skip(1)
            .map(|extension| path.join(format!("index{extension}"))),
    );
    candidates.push(path.join("index.svelte"));
    candidates
}

fn explicit_javascript_candidates(path: &Path) -> Option<Vec<PathBuf>> {
    let extension = path.extension()?.to_str()?;
    let stem = path.with_extension("");
    let replacements: &[&str] = match extension {
        "js" => &["ts", "tsx", "d.ts", "js"],
        "jsx" => &["tsx", "d.ts", "jsx"],
        "mjs" => &["mts", "d.mts", "mjs"],
        "cjs" => &["cts", "d.cts", "cjs"],
        _ => return None,
    };
    Some(
        replacements
            .iter()
            .map(|replacement| stem.with_extension(replacement))
            .collect(),
    )
}

fn alias_target(target: &Path, capture: &str) -> PathBuf {
    let mut resolved = PathBuf::new();
    for component in target.components() {
        match component {
            Component::Normal(part) => {
                resolved.push(part.to_string_lossy().replace('*', capture));
            }
            value => resolved.push(value.as_os_str()),
        }
    }
    resolved
}

fn normalize(path: &Path) -> PathBuf {
    let mut normalized = PathBuf::new();
    for component in path.components() {
        match component {
            Component::ParentDir => {
                let _ = normalized.pop();
            }
            Component::CurDir => {}
            value => normalized.push(value.as_os_str()),
        }
    }
    normalized
}

fn relative_text(path: &Path, root: &Path) -> Result<String, String> {
    Ok(relative_path(path, root)
        .ok_or_else(|| format!("{} is outside {}", path.display(), root.display()))?
        .to_string_lossy()
        .replace('\\', "/"))
}
