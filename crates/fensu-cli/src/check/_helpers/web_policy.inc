//! Native framework-independent TypeScript and JavaScript architecture policy.

use std::collections::{HashMap, HashSet};
use std::path::{Path, PathBuf};

use fensu_typescript::{FunctionFact, ModelFact, ModuleFacts, SourceSpan, StringFact};

use crate::analyzer::AnalyzerId;
use crate::models::{Config, ParsedProgram, ProjectInput, ScopedSource, SourcePurpose, TestLayout};

const GENERIC_OWNERS: &[&str] = &[
    "common",
    "components",
    "composables",
    "config",
    "core",
    "data",
    "domains",
    "features",
    "misc",
    "platform",
    "schemas",
    "services",
    "shared",
    "stores",
    "types",
    "utils",
];
const GENERIC_FILE_STEMS: &[&str] = &["common", "helpers", "services", "store", "utils"];
const INTERNAL_ROLES: &[&str] = &["api", "helpers", "resources", "state", "test"];
const LEAF_ROLES: &[&str] = &[
    "main",
    "components",
    "schemas",
    "types",
    "_api",
    "_adapters",
    "_components",
    "_helpers",
    "_resources",
    "_state",
    "_test",
];
const ROLE_FILE_STEMS: &[&str] = &["constants", "errors", "models", "schemas", "types"];

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct WebDiagnostic {
    pub(crate) code: &'static str,
    pub(crate) path: String,
    pub(crate) line: Option<u32>,
    pub(crate) column: Option<u32>,
    pub(crate) message: String,
}

pub(crate) struct WebPolicyRequest<'a> {
    pub(crate) config: &'a Config,
    pub(crate) sources: &'a [ScopedSource],
    pub(crate) project_inputs: &'a [ProjectInput],
    pub(crate) selected_codes: &'a HashSet<&'a str>,
    pub(crate) thresholds: &'a HashMap<(String, String), u32>,
}

pub(crate) fn evaluate(request: WebPolicyRequest<'_>) -> Vec<WebDiagnostic> {
    let mut diagnostics = project_diagnostics(&request);
    let by_path = request
        .sources
        .iter()
        .map(|source| (source.target_path.as_str(), source))
        .collect::<HashMap<_, _>>();
    for source in request.sources {
        let malformed = matches!(source.program, Some(ParsedProgram::Malformed(_)));
        if participates_in_file_policy(source, request.config)
            || malformed && source.purpose.reports_parse_failure()
        {
            diagnostics.extend(module_diagnostics(source, &request, &by_path));
        }
    }
    diagnostics.sort_by(|left, right| {
        (&left.path, left.line, left.column, left.code).cmp(&(
            &right.path,
            right.line,
            right.column,
            right.code,
        ))
    });
    diagnostics
}

fn module_diagnostics(
    source: &ScopedSource,
    request: &WebPolicyRequest<'_>,
    by_path: &HashMap<&str, &ScopedSource>,
) -> Vec<WebDiagnostic> {
    let mut diagnostics = Vec::new();
    if let Some(ParsedProgram::Malformed(failure)) = source.program.as_ref() {
        diagnostics.push(WebDiagnostic {
            code: "FWP001",
            path: source.target_path.clone(),
            line: Some(failure.line),
            column: Some(failure.column),
            message: failure.message.clone(),
        });
        return diagnostics;
    }
    role_diagnostics(source, request, &mut diagnostics);
    import_diagnostics(source, request, by_path, &mut diagnostics);
    shape_diagnostics(source, request, &mut diagnostics);
    api_budget_diagnostics(source, request, &mut diagnostics);
    annotation_diagnostics(source, request, &mut diagnostics);
    hygiene_and_contract_diagnostics(source, request, &mut diagnostics);
    naming_diagnostics(source, request, &mut diagnostics);
    test_diagnostics(source, request, by_path, &mut diagnostics);
    sveltekit_diagnostics(source, request, by_path, &mut diagnostics);
    diagnostics
}

fn role_diagnostics(
    source: &ScopedSource,
    request: &WebPolicyRequest<'_>,
    diagnostics: &mut Vec<WebDiagnostic>,
) {
    let basename = basename(source);
    let role = role_for(source, request.config);
    let owner_segments = owner_segments(source, request.config);
    let runtime_declarations = module_facts(source)
        .iter()
        .map(|facts| facts.runtime_declaration_count)
        .sum::<usize>();
    let functions = functions(source);
    let classes = module_facts(source)
        .iter()
        .flat_map(|facts| &facts.classes)
        .collect::<Vec<_>>();
    let top_level_bindings = module_facts(source)
        .iter()
        .flat_map(|facts| &facts.top_level_bindings)
        .collect::<Vec<_>>();
    if active(request, "FWS201") && role.as_deref() == Some("models") {
        for model in module_facts(source)
            .iter()
            .flat_map(|facts| &facts.models)
            .filter(|model| model.exported && !model.readonly_shape)
        {
            push_span(
                diagnostics,
                "FWS201",
                source,
                &model.span,
                &format!("model '{}' exposes mutable properties", model.name),
            );
        }
    }
    if is_ui_kit(source, request.config) {
        return;
    }
    if active(request, "FWR001") && role.as_deref() == Some("types") && runtime_declarations > 0 {
        push_path(
            diagnostics,
            "FWR001",
            source,
            "type role contains a runtime declaration",
        );
    }
    if active(request, "FWR002")
        && role.as_deref() == Some("constants")
        && (!functions.is_empty() || !classes.is_empty())
    {
        push_path(
            diagnostics,
            "FWR002",
            source,
            "constant role contains runtime behavior",
        );
    }
    if active(request, "FWR003")
        && role.as_deref() == Some("errors")
        && (classes.iter().any(|class| !class.error_class)
            || module_facts(source)
                .iter()
                .any(|facts| facts.top_level_function_count > 0)
            || !top_level_bindings.is_empty())
    {
        push_path(
            diagnostics,
            "FWR003",
            source,
            "error role contains a non-error runtime declaration",
        );
    }
    if active(request, "FWR201") && GENERIC_FILE_STEMS.contains(&module_stem(basename).as_str()) {
        push_path(
            diagnostics,
            "FWR201",
            source,
            &format!("generic filename '{basename}' hides its responsibility"),
        );
    }
    if active(request, "FWR304") && owner_segments.len() == 1 && !is_role_file(basename) {
        push_path(
            diagnostics,
            "FWR304",
            source,
            "module is loose at the owner root",
        );
    }
    if active(request, "FWR310") {
        for segment in owner_segments
            .iter()
            .take(owner_segments.len().saturating_sub(1))
        {
            if INTERNAL_ROLES.contains(&segment.as_str()) {
                push_path(
                    diagnostics,
                    "FWR310",
                    source,
                    &format!("internal role '{segment}' requires an underscore prefix"),
                );
            }
        }
    }
    if role.as_deref() == Some("main") && active(request, "FWR401") {
        let public_functions = functions.iter().filter(|fact| fact.exported).count();
        if public_functions != 1 {
            push_path(
                diagnostics,
                "FWR401",
                source,
                &format!("main entry exposes {public_functions} public functions; expected 1"),
            );
        }
    }
    if role.as_deref() == Some("_state")
        && active(request, "FWR404")
        && !basename.ends_with(".state.svelte.ts")
        && !basename.ends_with(".state.svelte.js")
        && !basename.ends_with(".state.svelte.mjs")
        && !basename.ends_with(".state.svelte.cjs")
    {
        push_path(
            diagnostics,
            "FWR404",
            source,
            "state role file does not use the state.svelte suffix",
        );
    }
    if role.as_deref() == Some("_resources")
        && active(request, "FWR405")
        && !resource_suffix(basename)
    {
        push_path(
            diagnostics,
            "FWR405",
            source,
            "resource role file does not use the resource suffix",
        );
    }
    if active(request, "FWR403") {
        for span in module_facts(source)
            .iter()
            .flat_map(|facts| &facts.re_exports)
        {
            push_span(
                diagnostics,
                "FWR403",
                source,
                span,
                "module re-exports declarations from another module",
            );
        }
    }
    if active(request, "FWR501") && !source_is_test(source) && role.as_deref() != Some("errors") {
        let exported = classes
            .iter()
            .copied()
            .filter(|class| class.exported)
            .collect::<Vec<_>>();
        if let Some(class) = exported.get(1) {
            push_span(
                diagnostics,
                "FWR501",
                source,
                &class.span,
                &format!(
                    "module exports {} runtime classes; expected at most one",
                    exported.len()
                ),
            );
        }
        let stem = module_stem(basename);
        for class in exported {
            if kebab_case(&class.name) != stem {
                push_span(
                    diagnostics,
                    "FWR501",
                    source,
                    &class.span,
                    &format!(
                        "exported class '{}' does not match filename '{stem}'",
                        class.name
                    ),
                );
            }
        }
    }
}

fn import_diagnostics(
    source: &ScopedSource,
    request: &WebPolicyRequest<'_>,
    by_path: &HashMap<&str, &ScopedSource>,
    diagnostics: &mut Vec<WebDiagnostic>,
) {
    for fact in module_facts(source).iter().flat_map(|facts| &facts.imports) {
        let resolved = source
            .imports
            .iter()
            .find(|imported| imported.specifier == fact.specifier)
            .and_then(|imported| imported.resolved_path.as_deref());
        let target = resolved.and_then(|path| by_path.get(path).copied());
        if active(request, "FWL103")
            && fact.namespace
            && target.is_some_and(|target| {
                !target.purpose.is_generated() && !is_ui_kit(target, request.config)
            })
        {
            push_span(
                diagnostics,
                "FWL103",
                source,
                &fact.span,
                &format!("namespace import from '{}'", fact.specifier),
            );
        }
        let Some(target) = target else {
            continue;
        };
        if target.purpose.is_generated() {
            continue;
        }
        if active(request, "FWL102")
            && !is_ui_kit(target, request.config)
            && basename(target).starts_with("index.")
            && !explicit_index_specifier(&fact.specifier)
        {
            push_span(
                diagnostics,
                "FWL102",
                source,
                &fact.span,
                &format!("directory import resolves through '{}'", target.target_path),
            );
        }
        if active(request, "FWL105")
            && !source_is_test(source)
            && !source_is_tooling(source)
            && (source_is_test(target) || source_is_tooling(target))
        {
            push_span(
                diagnostics,
                "FWL105",
                source,
                &fact.span,
                "runtime module imports test or tooling code",
            );
        }
        let target_capability = capability_for(target, request.config);
        let source_identity = capability_identity(source, request.config);
        let target_identity = capability_identity(target, request.config);
        let target_role = role_for(target, request.config);
        if active(request, "FWL101")
            && target_role
                .as_deref()
                .is_some_and(|role| role.starts_with('_'))
            && source_identity != target_identity
        {
            push_span(
                diagnostics,
                "FWL101",
                source,
                &fact.span,
                &format!(
                    "import enters internal role '{}/{}'",
                    target_capability.as_deref().unwrap_or("unknown"),
                    target_role.as_deref().unwrap_or("unknown")
                ),
            );
        }
        if active(request, "FWL108")
            && target_role.as_deref() == Some("main")
            && basename(target).starts_with('_')
            && source_identity != target_identity
        {
            push_span(
                diagnostics,
                "FWL108",
                source,
                &fact.span,
                &format!(
                    "import crosses into private main entry '{}/{}'",
                    target_capability.as_deref().unwrap_or("unknown"),
                    basename(target)
                ),
            );
        }
    }
}

fn shape_diagnostics(
    source: &ScopedSource,
    request: &WebPolicyRequest<'_>,
    diagnostics: &mut Vec<WebDiagnostic>,
) {
    if source_is_test(source) {
        return;
    }
    let line_count = source.content.iter().filter(|byte| **byte == b'\n').count()
        + usize::from(!source.content.ends_with(b"\n") || source.content.is_empty());
    check_budget(
        source,
        request,
        diagnostics,
        "FWS601",
        "max_file_lines",
        line_count,
        "module has",
    );
    let imported = module_facts(source)
        .iter()
        .map(|facts| facts.imported_binding_count)
        .sum::<usize>();
    check_budget(
        source,
        request,
        diagnostics,
        "FWS105",
        "max_imported_bindings",
        imported,
        "module imports",
    );
    let exports = module_facts(source)
        .iter()
        .map(|facts| facts.public_export_count)
        .sum::<usize>();
    if !is_ui_kit_family_surface(source, request.config) {
        check_budget(
            source,
            request,
            diagnostics,
            "FWS106",
            "max_public_exports",
            exports,
            "module exports",
        );
    }
    let entry = role_for(source, request.config).as_deref() == Some("main");
    for function in functions(source) {
        function_budget(
            source,
            request,
            diagnostics,
            function,
            "FWS010",
            "max_arguments",
            function.parameter_count,
            "arguments",
        );
        function_budget(
            source,
            request,
            diagnostics,
            function,
            "FWS011",
            "max_statements_global",
            function.statement_count,
            "statements",
        );
        if entry && function.exported || is_server_route_entry(source, request.config, function) {
            function_budget(
                source,
                request,
                diagnostics,
                function,
                "FWS001",
                "max_statements",
                function.statement_count,
                "statements",
            );
            function_budget(
                source,
                request,
                diagnostics,
                function,
                "FWS002",
                "max_distinct_calls",
                function.distinct_call_count,
                "distinct operations",
            );
            function_budget(
                source,
                request,
                diagnostics,
                function,
                "FWS003",
                "max_locals",
                function.local_count,
                "locals",
            );
        }
    }
}

fn api_budget_diagnostics(
    source: &ScopedSource,
    request: &WebPolicyRequest<'_>,
    diagnostics: &mut Vec<WebDiagnostic>,
) {
    if source_is_test(source)
        || source_is_tooling(source)
        || role_for(source, request.config).as_deref() != Some("_api")
    {
        return;
    }
    check_named_budget(
        source,
        request,
        diagnostics,
        "FWS110",
        "max_api_lines",
        source_line_count(source),
        "API module has",
        "lines",
    );
    let exports = module_facts(source)
        .iter()
        .map(|value| value.public_export_count)
        .sum::<usize>();
    check_named_budget(
        source,
        request,
        diagnostics,
        "FWS111",
        "max_api_exports",
        exports,
        "API module exports",
        "declarations",
    );
}

#[allow(clippy::too_many_arguments)]
fn function_budget(
    source: &ScopedSource,
    request: &WebPolicyRequest<'_>,
    diagnostics: &mut Vec<WebDiagnostic>,
    function: &FunctionFact,
    code: &'static str,
    threshold_name: &str,
    actual: usize,
    noun: &str,
) {
    let limit = threshold(request, source, threshold_name);
    if active(request, code) && actual > limit as usize {
        let owner = if code.starts_with("FWS00") {
            "entry"
        } else {
            "function"
        };
        push_span(
            diagnostics,
            code,
            source,
            &function.span,
            &format!(
                "{owner} '{}' has {actual} {noun}; limit is {limit}",
                function.name
            ),
        );
    }
}

fn check_budget(
    source: &ScopedSource,
    request: &WebPolicyRequest<'_>,
    diagnostics: &mut Vec<WebDiagnostic>,
    code: &'static str,
    threshold_name: &str,
    actual: usize,
    prefix: &str,
) {
    let limit = threshold(request, source, threshold_name);
    if active(request, code) && actual > limit as usize {
        push_path(
            diagnostics,
            code,
            source,
            &format!("{prefix} {actual}; limit is {limit}"),
        );
    }
}

#[allow(clippy::too_many_arguments)]
fn check_named_budget(
    source: &ScopedSource,
    request: &WebPolicyRequest<'_>,
    diagnostics: &mut Vec<WebDiagnostic>,
    code: &'static str,
    threshold_name: &str,
    actual: usize,
    prefix: &str,
    noun: &str,
) {
    let limit = threshold(request, source, threshold_name);
    if active(request, code) && actual > limit as usize {
        push_path(
            diagnostics,
            code,
            source,
            &format!("{prefix} {actual} {noun}; limit is {limit}"),
        );
    }
}

#[allow(clippy::too_many_arguments)]
fn check_script_budget(
    source: &ScopedSource,
    request: &WebPolicyRequest<'_>,
    diagnostics: &mut Vec<WebDiagnostic>,
    code: &'static str,
    threshold_name: &str,
    actual: usize,
    prefix: &str,
) {
    let limit = threshold(request, source, threshold_name);
    if !active(request, code) || actual <= limit as usize {
        return;
    }
    let message = format!("{prefix} {actual} lines; limit is {limit}");
    if let Some(span) = instance_script_span(source) {
        push_span(diagnostics, code, source, span, &message);
    } else {
        push_path(diagnostics, code, source, &message);
    }
}

fn annotation_diagnostics(
    source: &ScopedSource,
    request: &WebPolicyRequest<'_>,
    diagnostics: &mut Vec<WebDiagnostic>,
) {
    let text = source_text(source);
    for function in functions(source).into_iter().filter(|fact| fact.exported) {
        if declared_variable_contract(text, &function.name) {
            continue;
        }
        if active(request, "FWA001") && !function.parameters_annotated {
            push_span(
                diagnostics,
                "FWA001",
                source,
                &function.span,
                &format!(
                    "public function '{}' has an unannotated parameter",
                    function.name
                ),
            );
        }
        if active(request, "FWA002") && function.return_type.is_none() {
            push_span(
                diagnostics,
                "FWA002",
                source,
                &function.span,
                &format!(
                    "public function '{}' has no declared return type",
                    function.name
                ),
            );
        }
    }
    if active(request, "FWA003") && !is_ui_kit(source, request.config) {
        for binding in module_facts(source)
            .iter()
            .flat_map(|facts| &facts.local_bindings)
            .filter(|binding| binding.requires_explicit_type())
        {
            push_span(
                diagnostics,
                "FWA003",
                source,
                &binding.span,
                &format!(
                    "local variable '{}' has no explicit type on first binding",
                    binding.name
                ),
            );
        }
    }
}

fn hygiene_and_contract_diagnostics(
    source: &ScopedSource,
    request: &WebPolicyRequest<'_>,
    diagnostics: &mut Vec<WebDiagnostic>,
) {
    if source_is_test(source) || source_is_tooling(source) {
        return;
    }
    let text = source_text(source);
    let syntax = syntax_only(text);
    if active(request, "FWH009") {
        if !matches!(source.program, Some(ParsedProgram::Svelte(_))) {
            for call in module_facts(source)
                .iter()
                .flat_map(|facts| &facts.top_level_calls)
                .filter(|call| !call.name.starts_with('$'))
            {
                push_span(
                    diagnostics,
                    "FWH009",
                    source,
                    call.initializer_call_span.as_ref().unwrap_or(&call.span),
                    &format!(
                        "module calls '{}' during import",
                        call.initializer_call.as_deref().unwrap_or(&call.name)
                    ),
                );
            }
        }
        if let Some((index, _)) = exported_singleton(&syntax) {
            push_offset(
                diagnostics,
                "FWH009",
                source,
                index,
                "module constructs an exported singleton during import",
            );
        }
    }
    for call in module_facts(source)
        .iter()
        .flat_map(|facts| &facts.json_calls)
    {
        if active(request, "FWC101") && !call.schema_decoded {
            push_span(
                diagnostics,
                "FWC101",
                source,
                &call.span,
                "JSON response is used without runtime schema decoding",
            );
        }
        if active(request, "FWC102") && call.asserted {
            push_span(
                diagnostics,
                "FWC102",
                source,
                &call.span,
                "JSON response type assertion bypasses runtime decoding",
            );
        }
    }
    if active(request, "FWC103") {
        if let Some(span) = module_facts(source)
            .iter()
            .flat_map(|facts| &facts.public_any)
            .filter(|span| legacy_public_any(source, span.start))
            .min_by_key(|span| span.start)
        {
            push_span(
                diagnostics,
                "FWC103",
                source,
                span,
                "public contract exposes explicit any",
            );
        }
    }
}

fn naming_diagnostics(
    source: &ScopedSource,
    request: &WebPolicyRequest<'_>,
    diagnostics: &mut Vec<WebDiagnostic>,
) {
    if source_is_test(source) || source_is_tooling(source) {
        return;
    }
    for function in functions(source) {
        let Some(return_type) = function.return_type.as_deref() else {
            continue;
        };
        let behaviors = request
            .config
            .contracts
            .iter()
            .filter(|(pattern, _)| wildcard_match(&function.name, pattern))
            .map(|(_, behavior)| behavior.as_str())
            .collect::<HashSet<_>>();
        if active(request, "FWN001")
            && behaviors.contains("returns-bool")
            && return_type != "boolean"
        {
            push_span(
                diagnostics,
                "FWN001",
                source,
                &function.span,
                &format!(
                    "predicate '{}' declares return type '{return_type}'",
                    function.name
                ),
            );
        }
        if active(request, "FWN002") && behaviors.contains("no-return") && return_type != "void" {
            push_span(
                diagnostics,
                "FWN002",
                source,
                &function.span,
                &format!(
                    "validator '{}' declares return type '{return_type}'",
                    function.name
                ),
            );
        }
        if active(request, "FWN003") && behaviors.contains("returns-value") && return_type == "void"
        {
            push_span(
                diagnostics,
                "FWN003",
                source,
                &function.span,
                &format!(
                    "value function '{}' does not declare a value return",
                    function.name
                ),
            );
        }
        if active(request, "FWN004")
            && behaviors.contains("returns-iterator")
            && !["Iterator", "Iterable", "Generator"]
                .iter()
                .any(|kind| return_type.contains(kind))
        {
            push_span(
                diagnostics,
                "FWN004",
                source,
                &function.span,
                &format!(
                    "iterator '{}' declares return type '{return_type}'",
                    function.name
                ),
            );
        }
    }
}

fn test_diagnostics(
    source: &ScopedSource,
    request: &WebPolicyRequest<'_>,
    by_path: &HashMap<&str, &ScopedSource>,
    diagnostics: &mut Vec<WebDiagnostic>,
) {
    if !source_is_test(source) {
        return;
    }
    if test_setup_file(source, request.config) {
        return;
    }
    let text = source_text(source);
    let syntax = syntax_only(text);
    if active(request, "FWT002") && !test_mirrors_source(source, request) {
        push_path(
            diagnostics,
            "FWT002",
            source,
            "test is outside its configured source owner",
        );
    }
    if active(request, "FWT001") {
        if let Some(index) = [
            "test.skip(",
            "test.todo(",
            "it.skip(",
            "it.todo(",
            "describe.skip(",
        ]
        .iter()
        .filter_map(|needle| syntax.find(needle))
        .min()
        {
            push_offset(
                diagnostics,
                "FWT001",
                source,
                index,
                "committed test is skipped or pending",
            );
        }
    }
    if active(request, "FWT302") {
        for fact in module_facts(source)
            .iter()
            .flat_map(|facts| &facts.test_calls)
        {
            if !fact.name.contains("given")
                || !fact.name.contains("when")
                || !fact.name.contains("then")
            {
                push_span(
                    diagnostics,
                    "FWT302",
                    source,
                    &fact.span,
                    &format!("test name '{}' does not express given/when/then", fact.name),
                );
            }
        }
    }
    for fact in module_facts(source)
        .into_iter()
        .flat_map(|facts| &facts.parameterized_tests)
    {
        let case_model = test_case_model(source, fact, request.config, by_path);
        if active(request, "FWT201")
            && case_model.is_some_and(|model| {
                !model
                    .property_names
                    .iter()
                    .any(|property| property == "description")
            })
        {
            push_span(
                diagnostics,
                "FWT201",
                source,
                &fact.span,
                "parameterized case type lacks a description field",
            );
        }
        if active(request, "FWT202")
            && case_model.is_some_and(|model| {
                !model
                    .property_names
                    .iter()
                    .any(|property| property.starts_with("expected"))
            })
        {
            push_span(
                diagnostics,
                "FWT202",
                source,
                &fact.span,
                "parameterized case type lacks an expected field",
            );
        }
        if active(request, "FWT401") && (!fact.typed || !fact.inline_cases) {
            push_span(
                diagnostics,
                "FWT401",
                source,
                &fact.span,
                "parameterized cases are not an inline typed array",
            );
        }
        if active(request, "FWT402") && fact.callback_name.as_deref() != Some("testCase") {
            push_span(
                diagnostics,
                "FWT402",
                source,
                &fact.span,
                "parameterized callback does not accept testCase",
            );
        }
        if active(request, "FWT403")
            && !readonly_test_case_type(source, fact, request.config, by_path)
        {
            push_span(
                diagnostics,
                "FWT403",
                source,
                &fact.span,
                "parameterized case type is not a local readonly interface",
            );
        }
        if active(request, "FWT404") && fact.has_expectation && !fact.uses_expected {
            push_span(
                diagnostics,
                "FWT404",
                source,
                &fact.span,
                "parameterized assertion does not use a testCase.expected field",
            );
        }
        if active(request, "FWT405") && fact.has_branch {
            push_span(
                diagnostics,
                "FWT405",
                source,
                &fact.span,
                "test body contains outcome-dependent control flow",
            );
        }
        if active(request, "FWT406") && !fact.title_uses_description {
            push_span(
                diagnostics,
                "FWT406",
                source,
                &fact.span,
                "parameterized title does not use $description",
            );
        }
        if active(request, "FWT410") && fact.mutates_case {
            push_span(
                diagnostics,
                "FWT410",
                source,
                &fact.span,
                "parameterized test mutates testCase data",
            );
        }
        if active(request, "FWT411") && fact.inline_cases && !fact.nonempty_cases {
            push_span(
                diagnostics,
                "FWT411",
                source,
                &fact.span,
                "parameterized case array is empty",
            );
        }
        if active(request, "FWT412") && fact.inline_cases && !fact.object_cases {
            push_span(
                diagnostics,
                "FWT412",
                source,
                &fact.span,
                "parameterized cases are not object values",
            );
        }
    }
}

fn sveltekit_diagnostics(
    source: &ScopedSource,
    request: &WebPolicyRequest<'_>,
    by_path: &HashMap<&str, &ScopedSource>,
    diagnostics: &mut Vec<WebDiagnostic>,
) {
    if request.config.framework.as_deref() != Some("sveltekit") {
        return;
    }
    if source_is_test(source) || source_is_tooling(source) {
        return;
    }
    let facts = module_facts(source);
    let state_module = is_state_module(source);
    let route = is_route_module(source, request.config);
    let component = matches!(source.program, Some(ParsedProgram::Svelte(_)));
    let line_count = source_line_count(source);
    if state_module {
        check_named_budget(
            source,
            request,
            diagnostics,
            "FWS101",
            "max_state_lines",
            line_count,
            "state module has",
            "lines",
        );
        let state_cells = facts
            .iter()
            .flat_map(|value| &value.calls)
            .filter(|call| call.name == "$state" || call.name.starts_with("$state."))
            .count();
        check_named_budget(
            source,
            request,
            diagnostics,
            "FWS107",
            "max_state_cells",
            state_cells,
            "state module has",
            "mutable cells",
        );
        let runes = legacy_rune_count(source);
        check_named_budget(
            source,
            request,
            diagnostics,
            "FWS108",
            "max_total_runes",
            runes,
            "state module has",
            "runes",
        );
        let functions = legacy_function_count(source);
        check_named_budget(
            source,
            request,
            diagnostics,
            "FWS109",
            "max_state_functions",
            functions,
            "state module has",
            "functions",
        );
    }
    for rune in module_scope_runes(source) {
        if active(request, "FWS102") {
            push_span(
                diagnostics,
                "FWS102",
                source,
                rune.1,
                &format!("module scope creates mutable rune '{}'", rune.0),
            );
        }
    }
    if component {
        let script_lines = instance_script_lines(source);
        if route {
            check_script_budget(
                source,
                request,
                diagnostics,
                "FWS103",
                "max_route_script_lines",
                script_lines,
                "route script has",
            );
        } else {
            check_script_budget(
                source,
                request,
                diagnostics,
                "FWS104",
                "max_component_script_lines",
                script_lines,
                "component script has",
            );
        }
    }
    state_policy_diagnostics(source, request, diagnostics, &facts, state_module);
    resource_policy_diagnostics(
        source,
        request,
        diagnostics,
        &facts,
        state_module,
        component,
    );
    api_policy_diagnostics(source, request, diagnostics, &facts, component, route);
    framework_layer_diagnostics(source, request, by_path, diagnostics, component, route);
    ui_kit_module_diagnostics(source, request, by_path, diagnostics);
    openapi_diagnostics(source, request, diagnostics, &facts);
}

fn state_policy_diagnostics(
    source: &ScopedSource,
    request: &WebPolicyRequest<'_>,
    diagnostics: &mut Vec<WebDiagnostic>,
    facts: &[&ModuleFacts],
    state_module: bool,
) {
    let runes = facts
        .iter()
        .flat_map(|value| &value.calls)
        .filter(|call| is_rune_name(&call.name))
        .collect::<Vec<_>>();
    if active(request, "FWV101") && !is_svelte_aware(source) {
        if let Some(rune) = runes.first() {
            push_span(
                diagnostics,
                "FWV101",
                source,
                &rune.span,
                "rune syntax appears outside a Svelte-aware file",
            );
        }
    }
    if role_for(source, request.config).as_deref() == Some("_state") && active(request, "FWV102") {
        let factories = facts
            .iter()
            .flat_map(|value| &value.functions)
            .filter(|function| {
                function.exported
                    && function.name.starts_with("create")
                    && function.name.ends_with("State")
            })
            .count();
        if factories != 1 {
            push_path(
                diagnostics,
                "FWV102",
                source,
                &format!("state module exposes {factories} create-state factories; expected 1"),
            );
        }
    }
    if state_module && active(request, "FWV103") {
        let factory = facts
            .iter()
            .flat_map(|value| &value.functions)
            .find(|function| {
                function.exported
                    && function.name.starts_with("create")
                    && function.name.ends_with("State")
            });
        if let Some(returned) = factory.and_then(|factory| {
            facts
                .iter()
                .flat_map(|value| &value.return_objects)
                .filter(|returned| returned.function_name.as_deref() == Some(&factory.name))
                .max_by_key(|returned| returned.span.start)
        }) {
            let limit = threshold(request, source, "max_state_public_members") as usize;
            if returned.member_count > limit {
                push_span(
                    diagnostics,
                    "FWV103",
                    source,
                    &returned.span,
                    &format!(
                        "state facade has {} members; limit is {limit}",
                        returned.member_count
                    ),
                );
            }
        }
    }
    if active(request, "FWV104") && !is_ui_kit(source, request.config) {
        for mutation in facts.iter().flat_map(|value| &value.imported_mutations) {
            push_span(
                diagnostics,
                "FWV104",
                source,
                &mutation.span,
                &format!(
                    "consumer mutates imported '{}' directly",
                    mutation.root_name
                ),
            );
        }
    }
    for call in facts.iter().flat_map(|value| &value.calls) {
        if active(request, "FWV105") && call.name == "$derived" && call.function_argument {
            push_span(
                diagnostics,
                "FWV105",
                source,
                &call.span,
                "function-valued derivation uses $derived instead of $derived.by",
            );
        }
        if active(request, "FWV106")
            && call.name == "fetch"
            && call.ancestor_calls.iter().any(|name| name == "$effect")
        {
            push_span(
                diagnostics,
                "FWV106",
                source,
                &call.span,
                "effect performs raw transport",
            );
        }
    }
    if active(request, "FWV107") {
        if let Some(offset) = legacy_nested_effect_offset(source) {
            push_offset(
                diagnostics,
                "FWV107",
                source,
                offset,
                "effect is nested inside onMount",
            );
        }
    }
}

fn resource_policy_diagnostics(
    source: &ScopedSource,
    request: &WebPolicyRequest<'_>,
    diagnostics: &mut Vec<WebDiagnostic>,
    facts: &[&ModuleFacts],
    state_module: bool,
    component: bool,
) {
    let resources = facts
        .iter()
        .flat_map(|value| &value.resources)
        .collect::<Vec<_>>();
    let resource_role = role_for(source, request.config).as_deref() == Some("_resources");
    let lifecycle_owner = component && legacy_lifecycle_call(source);
    if active(request, "FWV201") && !resource_role && !lifecycle_owner {
        if let Some(resource) = resources.first() {
            push_span(
                diagnostics,
                "FWV201",
                source,
                &resource.span,
                &format!(
                    "{} is constructed outside a resource owner",
                    resource.family
                ),
            );
        }
        if state_module {
            let families = resources
                .iter()
                .map(|resource| resource.family.as_str())
                .collect::<HashSet<_>>()
                .len();
            let limit = threshold(request, source, "max_resource_families") as usize;
            if families > limit {
                push_path(
                    diagnostics,
                    "FWV201",
                    source,
                    &format!("state module owns {families} resource families; limit is {limit}"),
                );
            }
        }
    }
    if active(request, "FWV202")
        && resource_role
        && !resources.is_empty()
        && !legacy_resource_cleanup(source)
    {
        push_path(
            diagnostics,
            "FWV202",
            source,
            "resource owner does not expose cleanup",
        );
    }
}

fn api_policy_diagnostics(
    source: &ScopedSource,
    request: &WebPolicyRequest<'_>,
    diagnostics: &mut Vec<WebDiagnostic>,
    facts: &[&ModuleFacts],
    component: bool,
    route: bool,
) {
    let allows_api = allows_api_access(source, request.config);
    if !allows_api {
        if active(request, "FWA101") {
            for call in facts
                .iter()
                .flat_map(|value| &value.calls)
                .filter(|call| call.name == "fetch")
            {
                push_span(
                    diagnostics,
                    "FWA101",
                    source,
                    &call.span,
                    "raw fetch call appears outside an API or loader module",
                );
            }
        }
        if active(request, "FWA102") {
            for literal in facts
                .iter()
                .flat_map(|value| &value.strings)
                .filter(|literal| literal.value.starts_with("/api/"))
            {
                push_span(
                    diagnostics,
                    "FWA102",
                    source,
                    &literal.span,
                    &format!(
                        "endpoint literal '{}' appears outside an API or loader module",
                        literal.value
                    ),
                );
            }
        }
    }
    if active(request, "FWA103") && component && !route && has_imported_navigation_call(facts) {
        push_path(
            diagnostics,
            "FWA103",
            source,
            "component owns application navigation",
        );
    }
}

fn has_imported_navigation_call(facts: &[&ModuleFacts]) -> bool {
    let mut direct: HashSet<&str> = HashSet::new();
    let mut namespaces: HashSet<&str> = HashSet::new();
    for imported in facts
        .iter()
        .flat_map(|facts| &facts.imports)
        .filter(|imported| imported.specifier == "$app/navigation")
    {
        for binding in &imported.bindings {
            if binding.imported_name == "goto" {
                direct.insert(&binding.local_name);
            } else if binding.imported_name == "*" {
                namespaces.insert(&binding.local_name);
            }
        }
    }
    facts.iter().flat_map(|facts| &facts.calls).any(|call| {
        direct.contains(call.name.as_str())
            || namespaces
                .iter()
                .any(|namespace| call.name == format!("{namespace}.goto"))
    })
}

fn framework_layer_diagnostics(
    source: &ScopedSource,
    request: &WebPolicyRequest<'_>,
    by_path: &HashMap<&str, &ScopedSource>,
    diagnostics: &mut Vec<WebDiagnostic>,
    _component: bool,
    _route: bool,
) {
    let server = is_server_module(source, request.config);
    for fact in module_facts(source).iter().flat_map(|value| &value.imports) {
        if active(request, "FWL106") && node_builtin(&fact.specifier) && !server {
            push_span(
                diagnostics,
                "FWL106",
                source,
                &fact.span,
                &format!("browser module imports '{}'", fact.specifier),
            );
        }
        let target = source
            .imports
            .iter()
            .find(|item| item.specifier == fact.specifier)
            .and_then(|item| item.resolved_path.as_deref())
            .and_then(|path| by_path.get(path).copied());
        let Some(target) = target.filter(|target| !target.purpose.is_generated()) else {
            continue;
        };
        if active(request, "FWL104") {
            let source_route = route_owner(source, request.config);
            let target_route = route_owner(target, request.config);
            if source_route.is_some() && target_route.is_some() && source_route != target_route {
                push_span(
                    diagnostics,
                    "FWL104",
                    source,
                    &fact.span,
                    &format!(
                        "route imports another route '{}'",
                        target_route.unwrap_or_default()
                    ),
                );
            }
        }
        if active(request, "FWL107")
            && server
            && (matches!(target.program, Some(ParsedProgram::Svelte(_))) || is_state_module(target))
        {
            push_span(
                diagnostics,
                "FWL107",
                source,
                &fact.span,
                &format!(
                    "server module imports client module '{}'",
                    target.target_path
                ),
            );
        }
    }
}

fn ui_kit_module_diagnostics(
    source: &ScopedSource,
    request: &WebPolicyRequest<'_>,
    by_path: &HashMap<&str, &ScopedSource>,
    diagnostics: &mut Vec<WebDiagnostic>,
) {
    if !is_ui_kit(source, request.config) {
        return;
    }
    let Some(root) = request.config.ui_kit.as_deref() else {
        return;
    };
    let relative = source
        .target_path
        .strip_prefix(root)
        .and_then(|value| value.strip_prefix('/'))
        .unwrap_or_default();
    let depth = relative.split('/').count();
    let component = matches!(source.program, Some(ParsedProgram::Svelte(_)));
    if active(request, "FWU003") && (depth > 2 || component && depth != 2) {
        push_path(
            diagnostics,
            "FWU003",
            source,
            &format!("UI-kit module '{relative}' is not directly inside one component family"),
        );
    }
    if active(request, "FWU002") {
        for imported in &source.imports {
            let target = imported
                .resolved_path
                .as_deref()
                .and_then(|path| by_path.get(path).copied());
            if target.is_some_and(|target| {
                !is_ui_kit(target, request.config)
                    && !source_is_test(target)
                    && !source_is_tooling(target)
            }) {
                push_path(
                    diagnostics,
                    "FWU002",
                    source,
                    &format!(
                        "UI-kit module imports application source '{}'",
                        target.map_or("unknown", |value| value.target_path.as_str())
                    ),
                );
            }
        }
    }
}

fn openapi_diagnostics(
    source: &ScopedSource,
    request: &WebPolicyRequest<'_>,
    diagnostics: &mut Vec<WebDiagnostic>,
    facts: &[&ModuleFacts],
) {
    if !active(request, "FWC201") || request.config.openapi.is_none() {
        return;
    }
    let paths = openapi_paths(request);
    for literal in facts
        .iter()
        .flat_map(|value| &value.strings)
        .filter(|literal| literal.value.starts_with("/api/"))
    {
        let endpoint = literal.value.split('?').next().unwrap_or(&literal.value);
        let documented = paths
            .iter()
            .any(|path| endpoint_matches_openapi(literal, endpoint, path));
        if !documented {
            push_span(
                diagnostics,
                "FWC201",
                source,
                &literal.span,
                &format!("endpoint '{endpoint}' is absent from OpenAPI"),
            );
        }
    }
}

fn endpoint_matches_openapi(literal: &StringFact, endpoint: &str, path: &str) -> bool {
    if literal.complete {
        return endpoint == path;
    }
    let Some(first) = literal.static_segments.first() else {
        return false;
    };
    let Some(mut remainder) = path.strip_prefix(first) else {
        return false;
    };
    for (index, segment) in literal.static_segments.iter().enumerate().skip(1) {
        let last = index + 1 == literal.static_segments.len();
        if last {
            return remainder.ends_with(segment);
        }
        let Some(position) = remainder.find(segment) else {
            return false;
        };
        remainder = &remainder[position + segment.len()..];
    }
    true
}

fn readonly_test_case_type(
    source: &ScopedSource,
    test: &fensu_typescript::ParameterizedTestFact,
    config: &Config,
    by_path: &HashMap<&str, &ScopedSource>,
) -> bool {
    test_case_model(source, test, config, by_path)
        .is_some_and(|model| model.readonly_properties && !model.property_names.is_empty())
}

fn test_case_model<'a>(
    source: &'a ScopedSource,
    test: &fensu_typescript::ParameterizedTestFact,
    config: &Config,
    by_path: &HashMap<&str, &'a ScopedSource>,
) -> Option<&'a ModelFact> {
    let case_type = test.case_type_name.as_deref()?;
    if let Some(model) = module_facts(source)
        .iter()
        .flat_map(|facts| &facts.models)
        .find(|model| model.name == case_type)
    {
        return Some(model);
    }
    for facts in module_facts(source) {
        for imported in &facts.imports {
            let Some(binding) = imported
                .bindings
                .iter()
                .find(|binding| binding.local_name == case_type)
            else {
                continue;
            };
            let target = source
                .imports
                .iter()
                .find(|graph| graph.specifier == imported.specifier)
                .and_then(|graph| graph.resolved_path.as_deref())
                .and_then(|path| by_path.get(path).copied());
            let Some(target) = target.filter(|target| {
                target.target_path.split('/').any(|part| part == "_test")
                    && capability_identity(target, config) == capability_identity(source, config)
            }) else {
                continue;
            };
            if let Some(model) = module_facts(target)
                .iter()
                .flat_map(|target_facts| &target_facts.models)
                .find(|model| model.name == binding.imported_name)
            {
                return Some(model);
            }
        }
    }
    None
}

fn project_diagnostics(request: &WebPolicyRequest<'_>) -> Vec<WebDiagnostic> {
    let mut diagnostics = Vec::new();
    ui_kit_project_diagnostics(request, &mut diagnostics);
    owner_project_diagnostics(request, &mut diagnostics);
    public_main_diagnostics(request, &mut diagnostics);
    cycle_diagnostics(request, &mut diagnostics);
    required_test_diagnostics(request, &mut diagnostics);
    diagnostics
}

fn ui_kit_project_diagnostics(
    request: &WebPolicyRequest<'_>,
    diagnostics: &mut Vec<WebDiagnostic>,
) {
    if !active(request, "FWU001") {
        return;
    }
    let (Some(ui_kit), Some(shadcn_path)) = (
        request.config.ui_kit.as_deref(),
        request.config.shadcn.as_deref(),
    ) else {
        return;
    };
    let Some(input) = request
        .project_inputs
        .iter()
        .find(|input| input.target_path == shadcn_path)
    else {
        return;
    };
    let parsed = serde_json::from_str::<serde_json::Value>(input.text()).unwrap_or_default();
    let ui_alias = parsed
        .pointer("/aliases/ui")
        .and_then(serde_json::Value::as_str);
    let utils_alias = parsed
        .pointer("/aliases/utils")
        .and_then(serde_json::Value::as_str);
    let resolved_ui = ui_alias.and_then(|alias| resolve_web_alias(alias, request.config));
    let resolved_utils = utils_alias.and_then(|alias| resolve_web_alias(alias, request.config));
    let remediation =
        format!("Set aliases.ui to '$ui-kit' and aliases.utils to '$ui-kit/utils' for '{ui_kit}'.");
    if resolved_ui.as_deref() != Some(ui_kit) {
        push_project_path(
            diagnostics,
            "FWU001",
            input.target_path.clone(),
            &format!(
                "shadcn UI alias '{}' does not resolve to '{ui_kit}'; {remediation}",
                ui_alias.unwrap_or("<missing>")
            ),
        );
    }
    if resolved_utils
        .as_deref()
        .is_none_or(|value| value == ui_kit || !value.starts_with(&format!("{ui_kit}/")))
    {
        push_project_path(
            diagnostics,
            "FWU001",
            input.target_path.clone(),
            &format!(
                "shadcn utility alias '{}' does not resolve beneath '{ui_kit}'; {remediation}",
                utils_alias.unwrap_or("<missing>")
            ),
        );
    }
}

fn resolve_web_alias(alias: &str, config: &Config) -> Option<String> {
    if alias == "$ui-kit" {
        return config.ui_kit.clone();
    }
    if let Some(relative) = alias.strip_prefix("$ui-kit/") {
        return config
            .ui_kit
            .as_ref()
            .map(|root| format!("{root}/{relative}"));
    }
    if alias == "$lib" {
        return config.roots.first().map(|root| format!("{root}/lib"));
    }
    if let Some(relative) = alias.strip_prefix("$lib/") {
        return config
            .roots
            .first()
            .map(|root| format!("{root}/lib/{relative}"));
    }
    Some(
        alias
            .trim_start_matches("./")
            .trim_end_matches('/')
            .to_owned(),
    )
}

fn openapi_paths(request: &WebPolicyRequest<'_>) -> HashSet<String> {
    let Some(path) = request.config.openapi.as_deref() else {
        return HashSet::new();
    };
    let Some(input) = request
        .project_inputs
        .iter()
        .find(|input| input.target_path == path)
    else {
        return HashSet::new();
    };
    serde_json::from_str::<serde_json::Value>(input.text())
        .ok()
        .and_then(|document| {
            document
                .get("paths")
                .and_then(serde_json::Value::as_object)
                .cloned()
        })
        .map(|paths| paths.into_iter().map(|(path, _)| path).collect())
        .unwrap_or_default()
}

fn owner_project_diagnostics(request: &WebPolicyRequest<'_>, diagnostics: &mut Vec<WebDiagnostic>) {
    let mut by_capability: HashMap<(String, String), Vec<&ScopedSource>> = HashMap::new();
    let mut by_owner: HashMap<(String, String), Vec<&ScopedSource>> = HashMap::new();
    for source in request.sources.iter().filter(|source| {
        participates_in_project(source, request.config)
            && source_is_analyzable(source)
            && !source_is_test(source)
            && !source_is_tooling(source)
    }) {
        if let (Some(root), Some(owner)) = (
            source_root_for(source, request.config),
            owner_for(source, request.config),
        ) {
            by_owner
                .entry((root.to_owned(), owner))
                .or_default()
                .push(source);
        }
        if let Some(capability) = capability_identity(source, request.config) {
            by_capability.entry(capability).or_default().push(source);
        }
    }
    for ((_, owner), modules) in &by_owner {
        let Some(first) = modules.first() else {
            continue;
        };
        if active(request, "FWR204") && GENERIC_OWNERS.contains(&owner.as_str()) {
            push_project_path(
                diagnostics,
                "FWR204",
                owner_path(first, request.config),
                &format!("generic owner '{owner}' does not identify a producer"),
            );
        }
        let mut leaf = false;
        let mut branch = false;
        for source in modules {
            let segments = owner_segments(source, request.config);
            let first = segments.first().map(String::as_str);
            if segments.len() == 1 || first.is_some_and(|part| LEAF_ROLES.contains(&part)) {
                leaf = true;
            } else if first.is_some_and(|part| !is_role_file(part)) {
                branch = true;
            }
        }
        if active(request, "FWR306") && leaf && branch {
            push_project_path(
                diagnostics,
                "FWR306",
                owner_path(first, request.config),
                &format!("owner '{owner}' mixes direct roles with subdomains"),
            );
        }
    }
    for ((_, capability), modules) in &by_capability {
        let Some(first) = modules.first() else {
            continue;
        };
        let roles = modules
            .iter()
            .filter_map(|source| role_for(source, request.config))
            .collect::<Vec<_>>();
        if active(request, "FWR309") && !roles.iter().any(|role| role == "main") {
            push_project_path(
                diagnostics,
                "FWR309",
                capability_path(first, request.config, capability),
                &format!("leaf '{capability}' has no main entry"),
            );
        }
        let meaningful_roles = modules
            .iter()
            .filter(|source| meaningful(source))
            .filter_map(|source| role_for(source, request.config))
            .collect::<HashSet<_>>();
        if active(request, "FWR311")
            && meaningful_roles.len() == 1
            && meaningful_roles.contains("main")
        {
            push_project_path(
                diagnostics,
                "FWR311",
                capability_path(first, request.config, capability),
                &format!("leaf '{capability}' contains only main entries"),
            );
        }
        if active(request, "FWR301") {
            for role in ["main", "_helpers"] {
                let role_modules = modules
                    .iter()
                    .copied()
                    .filter(|source| role_for(source, request.config).as_deref() == Some(role))
                    .collect::<Vec<_>>();
                if role_modules.is_empty() {
                    continue;
                }
                let paths = role_modules
                    .iter()
                    .map(|source| path_after_role(source, request.config))
                    .collect::<Vec<_>>();
                let direct = paths.iter().any(|parts| parts.len() == 1);
                let grouped = paths.iter().any(|parts| parts.len() > 1);
                let depth = threshold(request, role_modules[0], "max_role_depth") as usize;
                let limit_name = if role == "main" {
                    "max_main_container_modules"
                } else {
                    "max_helpers_container_modules"
                };
                let limit = threshold(request, role_modules[0], limit_name) as usize;
                if direct && grouped
                    || paths
                        .iter()
                        .any(|parts| parts.len().saturating_sub(1) > depth)
                    || role_modules.len() > limit
                {
                    push_project_path(
                        diagnostics,
                        "FWR301",
                        format!(
                            "{}/{role}",
                            capability_path(first, request.config, capability)
                        ),
                        &format!(
                            "{capability}/{role} must be flat or grouped with depth {depth} and at most {limit} entries"
                        ),
                    );
                }
            }
        }
    }
}

fn public_main_diagnostics(request: &WebPolicyRequest<'_>, diagnostics: &mut Vec<WebDiagnostic>) {
    if !active(request, "FWL109") {
        return;
    }
    for target in request.sources.iter().filter(|source| {
        participates_in_project(source, request.config)
            && source_is_analyzable(source)
            && !source_is_test(source)
            && !source_is_tooling(source)
            && role_for(source, request.config).as_deref() == Some("main")
            && !basename(source).starts_with('_')
    }) {
        let capability = capability_identity(target, request.config);
        let consumed = request.sources.iter().any(|source| {
            !source_is_test(source)
                && capability_identity(source, request.config) != capability
                && source
                    .imports
                    .iter()
                    .any(|imported| imported.resolved_path.as_deref() == Some(&target.target_path))
        });
        if !consumed {
            push_project_source(
                diagnostics,
                "FWL109",
                target,
                "public main entry has no external consumer",
            );
        }
    }
}

fn cycle_diagnostics(request: &WebPolicyRequest<'_>, diagnostics: &mut Vec<WebDiagnostic>) {
    if !active(request, "FWL201") {
        return;
    }
    let by_path = request
        .sources
        .iter()
        .map(|source| (source.target_path.as_str(), source))
        .collect::<HashMap<_, _>>();
    let mut visiting: HashSet<&str> = HashSet::new();
    let mut visited: HashSet<&str> = HashSet::new();
    let mut reported: HashSet<String> = HashSet::new();
    for source in request
        .sources
        .iter()
        .filter(|source| participates_in_project(source, request.config))
    {
        visit_cycle(
            source,
            &by_path,
            &mut visiting,
            &mut visited,
            &mut Vec::new(),
            &mut reported,
            diagnostics,
        );
    }
}

#[allow(clippy::too_many_arguments)]
fn visit_cycle<'a>(
    source: &'a ScopedSource,
    by_path: &HashMap<&'a str, &'a ScopedSource>,
    visiting: &mut HashSet<&'a str>,
    visited: &mut HashSet<&'a str>,
    stack: &mut Vec<&'a str>,
    reported: &mut HashSet<String>,
    diagnostics: &mut Vec<WebDiagnostic>,
) {
    if let Some(start) = stack.iter().position(|path| *path == source.target_path) {
        let mut cycle = stack[start..].to_vec();
        cycle.push(&source.target_path);
        let mut identity = cycle[..cycle.len().saturating_sub(1)].to_vec();
        identity.sort_unstable();
        identity.dedup();
        let report_source = identity
            .iter()
            .filter_map(|path| by_path.get(path).copied())
            .find(|candidate| candidate.purpose.is_direct())
            .or_else(|| identity.iter().find_map(|path| by_path.get(path).copied()));
        if let Some(report_source) = report_source.filter(|_| reported.insert(identity.join("|"))) {
            push_project_source(
                diagnostics,
                "FWL201",
                report_source,
                &format!("import cycle: {}", cycle.join(" -> ")),
            );
        }
        return;
    }
    if visited.contains(source.target_path.as_str()) || !visiting.insert(&source.target_path) {
        return;
    }
    stack.push(&source.target_path);
    for target in source
        .imports
        .iter()
        .filter_map(|imported| imported.resolved_path.as_deref())
        .filter_map(|path| by_path.get(path).copied())
    {
        visit_cycle(
            target,
            by_path,
            visiting,
            visited,
            stack,
            reported,
            diagnostics,
        );
    }
    let _ = stack.pop();
    visiting.remove(source.target_path.as_str());
    visited.insert(&source.target_path);
}

fn required_test_diagnostics(request: &WebPolicyRequest<'_>, diagnostics: &mut Vec<WebDiagnostic>) {
    if !active(request, "FWT003") && !active(request, "FWT004") {
        return;
    }
    let tests = request
        .sources
        .iter()
        .filter(|source| source_is_test(source))
        .filter(|source| source_is_analyzable(source))
        .collect::<Vec<_>>();
    for source in request.sources.iter().filter(|source| {
        participates_in_project(source, request.config)
            && source_is_analyzable(source)
            && !source_is_test(source)
    }) {
        let Some(role) = role_for(source, request.config) else {
            continue;
        };
        if !["_state", "_api", "_resources", "_adapters"].contains(&role.as_str()) {
            continue;
        }
        let stem = module_stem(basename(source));
        let matching_tests = tests
            .iter()
            .filter(|test| {
                basename(test).contains(&stem)
                    && capability_identity(test, request.config)
                        == capability_identity(source, request.config)
            })
            .copied()
            .collect::<Vec<_>>();
        if active(request, "FWT003") && matching_tests.is_empty() {
            push_project_source(
                diagnostics,
                "FWT003",
                source,
                &format!("{role} module has no focused test"),
            );
        }
        if active(request, "FWT004")
            && role == "_adapters"
            && !matching_tests.iter().any(|test| integration_test(test))
        {
            push_project_source(
                diagnostics,
                "FWT004",
                source,
                "imperative adapter has no integration or browser test",
            );
        }
    }
}

fn module_facts(source: &ScopedSource) -> Vec<&ModuleFacts> {
    match source.program.as_ref() {
        Some(ParsedProgram::TypeScript(facts)) => vec![facts.as_ref()],
        Some(ParsedProgram::Svelte(facts)) => {
            facts.scripts.iter().map(|script| &script.facts).collect()
        }
        Some(ParsedProgram::Python(_) | ParsedProgram::Malformed(_)) | None => Vec::new(),
    }
}

fn functions(source: &ScopedSource) -> Vec<&FunctionFact> {
    module_facts(source)
        .into_iter()
        .flat_map(|facts| &facts.functions)
        .collect()
}

fn active(request: &WebPolicyRequest<'_>, code: &str) -> bool {
    request.selected_codes.contains(code)
}

fn threshold(request: &WebPolicyRequest<'_>, source: &ScopedSource, name: &str) -> u32 {
    request
        .thresholds
        .get(&(source.target_path.clone(), name.to_owned()))
        .copied()
        .or_else(|| request.config.thresholds.get(name).copied())
        .unwrap_or(0)
}

fn source_text(source: &ScopedSource) -> &str {
    std::str::from_utf8(&source.content).unwrap_or_default()
}

fn basename(source: &ScopedSource) -> &str {
    source
        .target_path
        .rsplit('/')
        .next()
        .unwrap_or(&source.target_path)
}

fn source_is_test(source: &ScopedSource) -> bool {
    source.scope == "test"
}

fn source_is_tooling(source: &ScopedSource) -> bool {
    source.scope == "tooling"
}

fn source_is_analyzable(source: &ScopedSource) -> bool {
    matches!(
        source.program,
        Some(ParsedProgram::TypeScript(_) | ParsedProgram::Svelte(_))
    )
}

fn participates_in_project(source: &ScopedSource, config: &Config) -> bool {
    participates_in_file_policy(source, config)
}

fn is_ui_kit(source: &ScopedSource, config: &Config) -> bool {
    config.ui_kit.as_ref().is_some_and(|root| {
        source.target_path == *root || source.target_path.starts_with(&format!("{root}/"))
    })
}

fn is_ui_kit_family_surface(source: &ScopedSource, config: &Config) -> bool {
    let Some(root) = config.ui_kit.as_deref() else {
        return false;
    };
    source
        .target_path
        .strip_prefix(root)
        .and_then(|value| value.strip_prefix('/'))
        .is_some_and(|relative| {
            relative.split('/').count() == 2 && module_stem(basename(source)) == "index"
        })
}

fn owner_segments(source: &ScopedSource, config: &Config) -> Vec<String> {
    let Some(relative) = relative_to_source_root(source, config) else {
        return Vec::new();
    };
    let parts = relative.split('/').collect::<Vec<_>>();
    if parts.first() != Some(&"lib") || parts.len() < 3 {
        return Vec::new();
    }
    parts[2..].iter().map(|part| (*part).to_owned()).collect()
}

fn owner_for(source: &ScopedSource, config: &Config) -> Option<String> {
    let relative = relative_to_source_root(source, config)?;
    let parts = relative.split('/').collect::<Vec<_>>();
    (parts.first() == Some(&"lib") && parts.len() >= 3)
        .then(|| parts.get(1).map(|part| (*part).to_owned()))
        .flatten()
}

fn relative_to_source_root<'a>(source: &'a ScopedSource, config: &Config) -> Option<&'a str> {
    let root = source_root_for(source, config)?;
    ownership_path(source)
        .strip_prefix(root)
        .and_then(|value| value.strip_prefix('/'))
}

fn source_root_for<'a>(source: &ScopedSource, config: &'a Config) -> Option<&'a str> {
    config
        .roots
        .iter()
        .filter(|root| {
            ownership_path(source) == **root
                || ownership_path(source).starts_with(&format!("{root}/"))
        })
        .max_by_key(|root| root.len())
        .map(String::as_str)
}

fn role_index(segments: &[String]) -> Option<usize> {
    segments
        .iter()
        .position(|segment| LEAF_ROLES.contains(&segment.as_str()) || is_role_file(segment))
}

fn role_for(source: &ScopedSource, config: &Config) -> Option<String> {
    if let Some(role) = route_local_role(source, config) {
        return Some(role);
    }
    let segments = owner_segments(source, config);
    let index = role_index(&segments)?;
    let value = segments.get(index)?;
    if is_role_file(value) {
        Some(module_stem(value))
    } else {
        source
            .target_path
            .split('/')
            .find(|part| *part == value)
            .map(str::to_owned)
    }
}

fn capability_for(source: &ScopedSource, config: &Config) -> Option<String> {
    if source_is_test(source) && source.test_owner_path.is_none() {
        return test_capability(source, config);
    }
    runtime_capability(source, config).or_else(|| tooling_capability(source, config))
}

fn runtime_capability(source: &ScopedSource, config: &Config) -> Option<String> {
    let owner = owner_for(source, config)?;
    let segments = owner_segments(source, config);
    let end = role_index(&segments).unwrap_or(segments.len().saturating_sub(1));
    let mut parts = vec![owner];
    parts.extend(segments[..end].iter().cloned());
    Some(parts.join("/"))
}

fn capability_identity(source: &ScopedSource, config: &Config) -> Option<(String, String)> {
    let capability = capability_for(source, config)?;
    let root = if source_is_test(source) && source.test_owner_path.is_none() {
        test_source_root(source, config)?
    } else {
        source_root_for(source, config)
            .or_else(|| tooling_root_for(source, config))?
            .to_owned()
    };
    Some((root, capability))
}

fn tooling_capability(source: &ScopedSource, config: &Config) -> Option<String> {
    let root = tooling_root_for(source, config)?;
    let relative = ownership_path(source)
        .strip_prefix(root)
        .and_then(|value| value.strip_prefix('/'))?;
    Some(
        Path::new(relative)
            .parent()
            .filter(|parent| !parent.as_os_str().is_empty())
            .map_or_else(
                || "__root__".to_owned(),
                |parent| parent.to_string_lossy().into_owned(),
            ),
    )
}

fn tooling_root_for<'a>(source: &ScopedSource, config: &'a Config) -> Option<&'a str> {
    config
        .tooling
        .iter()
        .filter(|root| ownership_path(source).starts_with(&format!("{root}/")))
        .max_by_key(|root| root.len())
        .map(String::as_str)
}

fn ownership_path(source: &ScopedSource) -> &str {
    source
        .test_owner_path
        .as_deref()
        .unwrap_or(&source.target_path)
}

fn integration_test(source: &ScopedSource) -> bool {
    source
        .target_path
        .split('/')
        .any(|part| matches!(part, "integration" | "e2e"))
        || module_stem(basename(source))
            .split('.')
            .any(|part| matches!(part, "integration" | "e2e"))
}

fn test_source_root(source: &ScopedSource, config: &Config) -> Option<String> {
    if config.roots.len() == 1 {
        return config.roots.first().cloned();
    }
    config
        .roots
        .iter()
        .filter(|root| source.target_path.contains(&format!("/{root}/")))
        .max_by_key(|root| root.len())
        .cloned()
}

fn test_capability(source: &ScopedSource, config: &Config) -> Option<String> {
    let relative = config.tests.iter().find_map(|root| {
        source
            .target_path
            .strip_prefix(root)
            .and_then(|value| value.strip_prefix('/'))
    })?;
    let parts = relative.split('/').collect::<Vec<_>>();
    let lib = parts.iter().position(|part| *part == "lib")?;
    let owner = parts.get(lib + 1)?;
    let remaining = parts[lib + 2..]
        .iter()
        .map(|part| (*part).to_owned())
        .collect::<Vec<_>>();
    let end = role_index(&remaining).unwrap_or(remaining.len().saturating_sub(1));
    let mut capability = vec![(*owner).to_owned()];
    capability.extend(remaining[..end].iter().cloned());
    Some(capability.join("/"))
}

fn meaningful(source: &ScopedSource) -> bool {
    module_facts(source).iter().any(|facts| {
        facts.public_export_count > 0
            || !facts.functions.is_empty()
            || !facts.classes.is_empty()
            || !facts.models.is_empty()
            || !facts.top_level_calls.is_empty()
    }) || source
        .program
        .as_ref()
        .and_then(ParsedProgram::as_svelte)
        .is_some_and(|facts| facts.has_component_markup || !facts.module_runes.is_empty())
}

fn path_after_role(source: &ScopedSource, config: &Config) -> Vec<String> {
    let segments = owner_segments(source, config);
    let start = role_index(&segments).map_or(segments.len(), |index| index + 1);
    segments[start..].to_vec()
}

fn owner_path(source: &ScopedSource, config: &Config) -> String {
    let root = config
        .roots
        .iter()
        .find(|root| source.target_path.starts_with(&format!("{root}/")))
        .map(String::as_str)
        .unwrap_or("src");
    format!(
        "{root}/lib/{}",
        owner_for(source, config).unwrap_or_else(|| "unknown".to_owned())
    )
}

fn capability_path(source: &ScopedSource, config: &Config, capability: &str) -> String {
    let root = config
        .roots
        .iter()
        .find(|root| source.target_path.starts_with(&format!("{root}/")))
        .map(String::as_str)
        .unwrap_or("src");
    format!("{root}/lib/{capability}")
}

fn resource_suffix(name: &str) -> bool {
    [
        ".resource.ts",
        ".resource.js",
        ".resource.mjs",
        ".resource.cjs",
        ".resource.svelte.ts",
        ".resource.svelte.js",
    ]
    .iter()
    .any(|suffix| name.ends_with(suffix))
}

fn is_role_file(name: &str) -> bool {
    ROLE_FILE_STEMS.contains(&module_stem(name).as_str())
}

fn explicit_index_specifier(specifier: &str) -> bool {
    [
        "/index",
        "/index.ts",
        "/index.js",
        "/index.mjs",
        "/index.cjs",
        "/index.mts",
        "/index.cts",
    ]
    .iter()
    .any(|suffix| specifier.ends_with(suffix))
}

fn module_stem(name: &str) -> String {
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
    .to_owned()
}

fn kebab_case(value: &str) -> String {
    let mut output = String::new();
    let characters = value.chars().collect::<Vec<_>>();
    for (index, character) in characters.iter().enumerate() {
        if character.is_ascii_uppercase()
            && index > 0
            && (characters[index - 1].is_ascii_lowercase()
                || characters
                    .get(index + 1)
                    .is_some_and(char::is_ascii_lowercase))
        {
            output.push('-');
        }
        output.push(character.to_ascii_lowercase());
    }
    output
}

fn declared_variable_contract(source: &str, name: &str) -> bool {
    source
        .find(&format!("export const {name}"))
        .and_then(|start| {
            source[start..]
                .find('=')
                .map(|end| &source[start..start + end])
        })
        .is_some_and(|declaration| declaration.contains(':'))
}

fn exported_singleton(source: &str) -> Option<(usize, &str)> {
    let start = source.find("export const ")?;
    let tail = &source[start..source.len().min(start + 300)];
    let new = tail.find("= new ")?;
    ["Store(", "State(", "Service(", "Client(", "Manager("]
        .iter()
        .any(|suffix| tail[new..].contains(suffix))
        .then_some((start + new, tail))
}

fn syntax_only(source: &str) -> String {
    let bytes = source.as_bytes();
    let mut output = bytes.to_vec();
    let mut index = 0;
    while index < bytes.len() {
        if bytes[index..].starts_with(b"//") {
            while index < bytes.len() && bytes[index] != b'\n' {
                output[index] = b' ';
                index += 1;
            }
        } else if bytes[index..].starts_with(b"/*") {
            output[index] = b' ';
            output[index + 1] = b' ';
            index += 2;
            while index < bytes.len() && !bytes[index..].starts_with(b"*/") {
                if bytes[index] != b'\n' {
                    output[index] = b' ';
                }
                index += 1;
            }
            if index + 1 < bytes.len() {
                output[index] = b' ';
                output[index + 1] = b' ';
                index += 2;
            }
        } else if matches!(bytes[index], b'\'' | b'"' | b'`') {
            let quote = bytes[index];
            output[index] = b' ';
            index += 1;
            while index < bytes.len() {
                let escaped = index > 0 && bytes[index - 1] == b'\\';
                let done = bytes[index] == quote && !escaped;
                if bytes[index] != b'\n' {
                    output[index] = b' ';
                }
                index += 1;
                if done {
                    break;
                }
            }
        } else {
            index += 1;
        }
    }
    String::from_utf8(output).unwrap_or_default()
}

fn wildcard_match(value: &str, pattern: &str) -> bool {
    if let Some(prefix) = pattern.strip_suffix("_*") {
        if value.strip_prefix(prefix).is_some_and(|rest| {
            rest.starts_with('_') || rest.chars().next().is_some_and(char::is_uppercase)
        }) {
            return true;
        }
    }
    let value = value.as_bytes();
    let mut matches = vec![false; value.len() + 1];
    matches[0] = true;
    for token in pattern.as_bytes() {
        if *token == b'*' {
            for index in 1..=value.len() {
                matches[index] = matches[index] || matches[index - 1];
            }
        } else {
            for index in (1..=value.len()).rev() {
                matches[index] = matches[index - 1] && value[index - 1] == *token;
            }
            matches[0] = false;
        }
    }
    matches[value.len()]
}

fn test_mirrors_source(source: &ScopedSource, request: &WebPolicyRequest<'_>) -> bool {
    if request.config.test_layout == TestLayout::Colocated {
        return test_is_colocated(source);
    }
    let Some(relative) = request.config.tests.iter().find_map(|root| {
        source
            .target_path
            .strip_prefix(root)
            .and_then(|value| value.strip_prefix('/'))
    }) else {
        return false;
    };
    let area = Path::new(relative)
        .parent()
        .unwrap_or_else(|| Path::new(""))
        .to_string_lossy()
        .trim_end_matches("/_test")
        .to_owned();
    request.sources.iter().any(|candidate| {
        !source_is_test(candidate)
            && (request.config.roots.iter().any(|root| {
                candidate
                    .target_path
                    .starts_with(&format!("{root}/{area}/"))
            }) || request.config.tooling.iter().any(|root| {
                let tooling_area = area
                    .strip_prefix(root)
                    .and_then(|value| {
                        value
                            .strip_prefix('/')
                            .or_else(|| value.is_empty().then_some(value))
                    })
                    .unwrap_or(&area);
                let tooling_owner = format!("{root}/{tooling_area}")
                    .trim_end_matches('/')
                    .to_owned();
                candidate
                    .target_path
                    .starts_with(&format!("{tooling_owner}/"))
            }))
    })
}

fn test_is_colocated(source: &ScopedSource) -> bool {
    source.test_owner_path.is_some()
}

fn test_setup_file(source: &ScopedSource, config: &Config) -> bool {
    let configured_setup = module_stem(basename(source)) == "setup"
        && config.tests.iter().any(|root| {
            source
                .target_path
                .strip_prefix(&format!("{root}/"))
                .is_some_and(|relative| !relative.contains('/'))
        });
    let colocated_setup = config.test_layout == TestLayout::Colocated
        && crate::check::_helpers::project::web_test_identity(&source.path).as_deref()
            == Some("setup");
    configured_setup || colocated_setup
}

fn participates_in_file_policy(source: &ScopedSource, config: &Config) -> bool {
    if source.purpose.is_direct() {
        return true;
    }
    config.analyzer == AnalyzerId::Svelte
        && source.purpose == SourcePurpose::Support
        && crate::check::_helpers::project::is_direct_source(&source.path, AnalyzerId::TypeScript)
}

fn is_svelte_aware(source: &ScopedSource) -> bool {
    let name = basename(source);
    name.ends_with(".svelte") || name.contains(".svelte.")
}

fn is_state_module(source: &ScopedSource) -> bool {
    let name = basename(source);
    name.ends_with(".svelte.ts") || name.ends_with(".svelte.js")
}

fn is_rune_name(name: &str) -> bool {
    [
        "$state",
        "$derived",
        "$effect",
        "$props",
        "$bindable",
        "$inspect",
    ]
    .iter()
    .any(|rune| name == *rune || name.starts_with(&format!("{rune}.")))
}

fn module_scope_runes(source: &ScopedSource) -> Vec<(&str, &SourceSpan)> {
    if let Some(facts) = source.program.as_ref().and_then(ParsedProgram::as_svelte) {
        return facts
            .scripts
            .iter()
            .filter(|script| script.context == fensu_svelte::ScriptContext::Module)
            .flat_map(|script| &script.facts.top_level_bindings)
            .filter_map(|binding| {
                let name = binding.initializer_call.as_deref()?;
                is_rune_name(name).then(|| {
                    (
                        name,
                        binding
                            .initializer_call_span
                            .as_ref()
                            .unwrap_or(&binding.span),
                    )
                })
            })
            .collect();
    }
    if !is_svelte_aware(source) {
        return Vec::new();
    }
    module_facts(source)
        .into_iter()
        .flat_map(|facts| &facts.top_level_bindings)
        .filter_map(|binding| {
            let name = binding.initializer_call.as_deref()?;
            is_rune_name(name).then(|| {
                (
                    name,
                    binding
                        .initializer_call_span
                        .as_ref()
                        .unwrap_or(&binding.span),
                )
            })
        })
        .collect()
}

fn source_line_count(source: &ScopedSource) -> usize {
    if source.content.is_empty() {
        0
    } else {
        source.content.iter().filter(|byte| **byte == b'\n').count()
            + usize::from(!source.content.ends_with(b"\n"))
    }
}

fn instance_script_lines(source: &ScopedSource) -> usize {
    let Some(facts) = source.program.as_ref().and_then(ParsedProgram::as_svelte) else {
        return 0;
    };
    let Some(script) = facts
        .scripts
        .iter()
        .find(|script| script.context == fensu_svelte::ScriptContext::Instance)
    else {
        return 0;
    };
    let content = source
        .content
        .get(script.content_span.start..script.content_span.end)
        .unwrap_or_default();
    let trimmed = String::from_utf8_lossy(content);
    let trimmed = trimmed.trim();
    if trimmed.is_empty() {
        0
    } else {
        trimmed.lines().count()
    }
}

fn instance_script_span(source: &ScopedSource) -> Option<&SourceSpan> {
    source
        .program
        .as_ref()
        .and_then(ParsedProgram::as_svelte)?
        .scripts
        .iter()
        .find(|script| script.context == fensu_svelte::ScriptContext::Instance)
        .map(|script| &script.content_span)
}

fn is_route_module(source: &ScopedSource, config: &Config) -> bool {
    basename(source).starts_with('+')
        && config.roots.iter().any(|root| {
            source.target_path == format!("{root}/routes/{}", basename(source))
                || source.target_path.starts_with(&format!("{root}/routes/"))
        })
}

fn route_local_role(source: &ScopedSource, config: &Config) -> Option<String> {
    let relative = config
        .roots
        .iter()
        .find_map(|root| source.target_path.strip_prefix(&format!("{root}/routes/")))?;
    relative
        .split('/')
        .take_while(|part| *part != basename(source))
        .find(|part| LEAF_ROLES.contains(part))
        .map(str::to_owned)
}

fn is_server_route_entry(source: &ScopedSource, config: &Config, function: &FunctionFact) -> bool {
    if config.framework.as_deref() != Some("sveltekit")
        || !is_route_module(source, config)
        || !is_server_module(source, config)
    {
        return false;
    }
    function.export_owner.as_deref().is_some_and(|owner| {
        owner == "load"
            || owner == "actions"
            || ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"].contains(&owner)
    })
}

fn route_owner(source: &ScopedSource, config: &Config) -> Option<String> {
    let relative = config
        .roots
        .iter()
        .find_map(|root| source.target_path.strip_prefix(&format!("{root}/routes/")))?;
    let directory = relative
        .rsplit_once('/')
        .map_or("", |(directory, _)| directory);
    Some(
        directory
            .split('/')
            .take_while(|segment| !segment.starts_with('_'))
            .collect::<Vec<_>>()
            .join("/"),
    )
}

fn is_server_module(source: &ScopedSource, config: &Config) -> bool {
    let name = basename(source);
    name.contains(".server.")
        || name.starts_with("+server.")
        || config.roots.iter().any(|root| {
            source.target_path == format!("{root}/lib/server/{name}")
                || source
                    .target_path
                    .starts_with(&format!("{root}/lib/server/"))
        })
}

fn allows_api_access(source: &ScopedSource, config: &Config) -> bool {
    let name = basename(source);
    role_for(source, config).as_deref() == Some("_api")
        || source.target_path.split('/').any(|part| part == "http")
        || ["+page.", "+layout.", "+server."]
            .iter()
            .any(|prefix| name.starts_with(prefix) && !name.ends_with(".svelte"))
}

fn node_builtin(specifier: &str) -> bool {
    specifier.starts_with("node:")
        || [
            "fs",
            "path",
            "os",
            "child_process",
            "worker_threads",
            "net",
            "tls",
            "http",
            "https",
            "stream",
            "crypto",
        ]
        .iter()
        .any(|name| specifier == *name || specifier.starts_with(&format!("{name}/")))
}

fn legacy_rune_count(source: &ScopedSource) -> usize {
    let bytes = source_text(source).as_bytes();
    let mut count = 0;
    for index in 0..bytes.len() {
        if bytes[index] != b'$' {
            continue;
        }
        for rune in ["state", "derived", "effect", "props", "bindable", "inspect"] {
            let mut end = index + 1 + rune.len();
            if bytes.get(index + 1..end) != Some(rune.as_bytes()) {
                continue;
            }
            if bytes.get(end) == Some(&b'.') {
                end += 1;
                let member_start = end;
                while bytes.get(end).is_some_and(|byte| word_byte(*byte)) {
                    end += 1;
                }
                if end == member_start {
                    continue;
                }
            }
            if call_parenthesis(bytes, end).is_some() {
                count += 1;
                break;
            }
        }
    }
    count
}

fn legacy_function_count(source: &ScopedSource) -> usize {
    let bytes = source_text(source).as_bytes();
    let mut count = 0;
    for index in 0..bytes.len() {
        if !word_at(bytes, index, b"function") {
            continue;
        }
        let mut cursor = index + "function".len();
        if !bytes.get(cursor).is_some_and(u8::is_ascii_whitespace) {
            continue;
        }
        while bytes.get(cursor).is_some_and(u8::is_ascii_whitespace) {
            cursor += 1;
        }
        let name_start = cursor;
        while bytes.get(cursor).is_some_and(|byte| word_byte(*byte)) {
            cursor += 1;
        }
        if cursor > name_start && call_parenthesis(bytes, cursor).is_some() {
            count += 1;
        }
    }
    count
}

fn legacy_nested_effect_offset(source: &ScopedSource) -> Option<usize> {
    let bytes = source_text(source).as_bytes();
    for index in 0..bytes.len() {
        if !word_at(bytes, index, b"onMount") {
            continue;
        }
        let Some(open) = call_parenthesis(bytes, index + "onMount".len()) else {
            continue;
        };
        let end = (open + 1_002).min(bytes.len());
        for effect in open + 1..end {
            if bytes.get(effect..effect + "$effect".len()) == Some(b"$effect")
                && call_parenthesis(bytes, effect + "$effect".len()).is_some()
            {
                return Some(index);
            }
        }
    }
    None
}

fn legacy_lifecycle_call(source: &ScopedSource) -> bool {
    let bytes = source_text(source).as_bytes();
    (0..bytes.len()).any(|index| {
        word_at(bytes, index, b"onMount")
            && call_parenthesis(bytes, index + "onMount".len()).is_some()
            || bytes.get(index..index + "$effect".len()) == Some(b"$effect")
                && call_parenthesis(bytes, index + "$effect".len()).is_some()
    })
}

fn legacy_resource_cleanup(source: &ScopedSource) -> bool {
    let bytes = source_text(source).as_bytes();
    (0..bytes.len()).any(|index| {
        ["stop", "destroy", "cleanup"]
            .iter()
            .any(|name| word_at(bytes, index, name.as_bytes()))
            || ["clearTimeout", "clearInterval"].iter().any(|name| {
                word_at(bytes, index, name.as_bytes())
                    && call_parenthesis(bytes, index + name.len()).is_some()
            })
            || bytes.get(index..index + ".removeEventListener".len())
                == Some(b".removeEventListener")
                && call_parenthesis(bytes, index + ".removeEventListener".len()).is_some()
            || word_at(bytes, index, b"return") && returned_arrow(bytes, index + "return".len())
    })
}

fn legacy_public_any(source: &ScopedSource, offset: usize) -> bool {
    let bytes = source_text(source).as_bytes();
    let bounded = offset.min(bytes.len());
    for index in 0..bounded {
        if index + "export".len() <= bounded
            && word_at(bytes, index, b"export")
            && !bytes[index + "export".len()..bounded]
                .iter()
                .any(|byte| matches!(byte, b'{' | b';' | b'\n'))
        {
            return true;
        }
        if !word_at(bytes, index, b"interface") {
            continue;
        }
        let mut cursor = index + "interface".len();
        if !bytes.get(cursor).is_some_and(u8::is_ascii_whitespace) {
            continue;
        }
        while bytes.get(cursor).is_some_and(u8::is_ascii_whitespace) {
            cursor += 1;
        }
        if !word_at(bytes, cursor, b"Props") {
            continue;
        }
        cursor += "Props".len();
        while bytes.get(cursor).is_some_and(u8::is_ascii_whitespace) {
            cursor += 1;
        }
        if bytes.get(cursor) == Some(&b'{')
            && cursor < bounded
            && !bytes[cursor + 1..bounded].contains(&b'}')
        {
            return true;
        }
    }
    false
}

fn call_parenthesis(bytes: &[u8], mut index: usize) -> Option<usize> {
    while bytes.get(index).is_some_and(u8::is_ascii_whitespace) {
        index += 1;
    }
    (bytes.get(index) == Some(&b'(')).then_some(index)
}

fn returned_arrow(bytes: &[u8], mut index: usize) -> bool {
    while bytes.get(index).is_some_and(u8::is_ascii_whitespace) {
        index += 1;
    }
    if bytes.get(index) != Some(&b'(') {
        return false;
    }
    index += 1;
    while bytes.get(index).is_some_and(u8::is_ascii_whitespace) {
        index += 1;
    }
    if bytes.get(index) != Some(&b')') {
        return false;
    }
    index += 1;
    while bytes.get(index).is_some_and(u8::is_ascii_whitespace) {
        index += 1;
    }
    bytes.get(index..index + 2) == Some(b"=>")
}

fn word_at(bytes: &[u8], index: usize, word: &[u8]) -> bool {
    bytes.get(index..index + word.len()) == Some(word)
        && index
            .checked_sub(1)
            .and_then(|before| bytes.get(before))
            .is_none_or(|byte| !word_byte(*byte))
        && bytes
            .get(index + word.len())
            .is_none_or(|byte| !word_byte(*byte))
}

fn word_byte(byte: u8) -> bool {
    byte.is_ascii_alphanumeric() || byte == b'_'
}

fn push_path(
    diagnostics: &mut Vec<WebDiagnostic>,
    code: &'static str,
    source: &ScopedSource,
    message: &str,
) {
    diagnostics.push(WebDiagnostic {
        code,
        path: source.target_path.clone(),
        line: Some(1),
        column: Some(0),
        message: message.to_owned(),
    });
}

fn push_project_path(
    diagnostics: &mut Vec<WebDiagnostic>,
    code: &'static str,
    path: String,
    message: &str,
) {
    diagnostics.push(WebDiagnostic {
        code,
        path,
        line: None,
        column: None,
        message: message.to_owned(),
    });
}

fn push_project_source(
    diagnostics: &mut Vec<WebDiagnostic>,
    code: &'static str,
    source: &ScopedSource,
    message: &str,
) {
    push_project_path(diagnostics, code, source.target_path.clone(), message);
}

fn push_span(
    diagnostics: &mut Vec<WebDiagnostic>,
    code: &'static str,
    source: &ScopedSource,
    span: &SourceSpan,
    message: &str,
) {
    diagnostics.push(WebDiagnostic {
        code,
        path: source.target_path.clone(),
        line: Some(span.line as u32),
        column: Some(span.column as u32),
        message: message.to_owned(),
    });
}

fn push_offset(
    diagnostics: &mut Vec<WebDiagnostic>,
    code: &'static str,
    source: &ScopedSource,
    offset: usize,
    message: &str,
) {
    let prefix = &source.content[..offset.min(source.content.len())];
    let line = prefix.iter().filter(|byte| **byte == b'\n').count() + 1;
    let column = prefix
        .iter()
        .rposition(|byte| *byte == b'\n')
        .map_or(prefix.len(), |index| prefix.len() - index - 1);
    diagnostics.push(WebDiagnostic {
        code,
        path: source.target_path.clone(),
        line: Some(line as u32),
        column: Some(column as u32),
        message: message.to_owned(),
    });
}

#[allow(dead_code)]
fn _absolute_path(root: &Path, path: &str) -> PathBuf {
    root.join(path)
}
