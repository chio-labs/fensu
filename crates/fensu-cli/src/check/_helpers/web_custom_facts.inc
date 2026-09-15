//! Serialize parser-independent web facts already owned by the native check.

use std::collections::HashMap;
use std::path::Path;

use fensu_typescript::{ModuleFacts, SourceKind, SourceSpan};
use serde_json::{json, Value};

use crate::analyzer::AnalyzerId;
use crate::constants::{WEB_MODULE_PATH_SEPARATOR, WEB_ROUTES_DIRECTORY, WEB_SVELTE_EXTENSION};
use crate::models::{ParsedProgram, ScopedSource, SourcePurpose};

pub(crate) const WEB_FACT_SCHEMA_VERSION: &str = "web-facts-v1";

pub(crate) fn web_fact_payload(analyzer: AnalyzerId, sources: &[ScopedSource]) -> Value {
    json!({
        "schema_version": WEB_FACT_SCHEMA_VERSION,
        "parser_contract": analyzer.parser_contract(),
        "analyzer": analyzer.to_string(),
        "files": sources.iter().map(web_file).collect::<Vec<_>>(),
    })
}

fn web_file(source: &ScopedSource) -> Value {
    let modules = module_facts(source);
    let targets = source
        .imports
        .iter()
        .map(|item| (item.specifier.as_str(), item.resolved_path.as_deref()))
        .collect::<HashMap<_, _>>();
    let path = source.target_path.as_str();
    let svelte = match source.program.as_ref() {
        Some(ParsedProgram::Svelte(facts)) => Some(json!({
            "scripts": facts.scripts.iter().map(|script| json!({
                "context": match script.context {
                    fensu_svelte::ScriptContext::Module => "module",
                    fensu_svelte::ScriptContext::Instance => "instance",
                },
                "location": location(path, &script.content_span),
            })).collect::<Vec<_>>(),
            "module_runes": facts.module_runes.iter().map(|rune| json!({
                "name": rune.name,
                "location": location(path, &rune.span),
            })).collect::<Vec<_>>(),
            "has_component_markup": facts.has_component_markup,
            "route": is_route(path),
            "state_module": is_state_module(path),
        })),
        Some(ParsedProgram::TypeScript(facts))
            if source.analyzer == AnalyzerId::Svelte && is_state_module(path) =>
        {
            Some(json!({
                "scripts": [],
                "module_runes": state_runes(facts).into_iter().map(|(name, span)| json!({
                    "name": name,
                    "location": location(path, span),
                })).collect::<Vec<_>>(),
                "has_component_markup": false,
                "route": false,
                "state_module": true,
            }))
        }
        Some(ParsedProgram::Malformed(_))
            if source.analyzer == AnalyzerId::Svelte
                && (source.path.extension().and_then(|value| value.to_str())
                    == Some(WEB_SVELTE_EXTENSION)
                    || is_state_module(path)) =>
        {
            Some(json!({
                "scripts": [],
                "module_runes": [],
                "has_component_markup": false,
                "route": is_route(path),
                "state_module": is_state_module(path),
            }))
        }
        _ => None,
    };
    let parse_error = match source.program.as_ref() {
        Some(ParsedProgram::Malformed(failure)) => Some(failure.message.as_str()),
        _ => None,
    };
    let syntax_handles = syntax_handles(source, &modules);
    json!({
        "path": path,
        "source_kind": source_kind(source),
        "purpose": purpose(source.purpose),
        "module": module_identity(&source.relative_parts.join(WEB_MODULE_PATH_SEPARATOR)),
        "source_root": source.root_text,
        "scope": source.scope,
        "source": String::from_utf8_lossy(&source.content),
        "parse_error": parse_error,
        "imports": modules.iter().flat_map(|facts| facts.imports.iter()).map(|item| json!({
            "specifier": item.specifier,
            "bindings": item.bindings.iter().map(|binding| json!({
                "local_name": binding.local_name,
                "imported_name": binding.imported_name,
            })).collect::<Vec<_>>(),
            "type_only": item.type_only,
            "namespace": item.namespace,
            "target_path": targets.get(item.specifier.as_str()).copied().flatten(),
            "location": location(path, &item.span),
        })).collect::<Vec<_>>(),
        "functions": modules.iter().flat_map(|facts| facts.functions.iter()).map(|item| json!({
            "name": item.name,
            "qualified_name": item.qualified_name,
            "exported": item.exported,
            "export_owner": item.export_owner,
            "parameter_count": item.parameter_count,
            "parameters_annotated": item.parameters_annotated,
            "return_type": item.return_type,
            "statement_count": item.statement_count,
            "distinct_call_count": item.distinct_call_count,
            "local_count": item.local_count,
            "location": location(path, &item.span),
        })).collect::<Vec<_>>(),
        "classes": modules.iter().flat_map(|facts| facts.classes.iter()).map(|item| json!({
            "name": item.name,
            "exported": item.exported,
            "error_class": item.error_class,
            "location": location(path, &item.span),
        })).collect::<Vec<_>>(),
        "models": modules.iter().flat_map(|facts| facts.models.iter()).map(|item| json!({
            "name": item.name,
            "kind": match item.kind {
                fensu_typescript::ModelKind::Interface => "interface",
                fensu_typescript::ModelKind::TypeLiteralAlias => "type_literal_alias",
            },
            "exported": item.exported,
            "readonly_properties": item.readonly_properties,
            "readonly_shape": item.readonly_shape,
            "property_names": item.property_names,
            "location": location(path, &item.span),
        })).collect::<Vec<_>>(),
        "bindings": modules.iter().flat_map(|facts| facts.top_level_bindings.iter()).map(|item| json!({
            "name": item.name,
            "initializer_call": item.initializer_call,
            "location": location(path, &item.span),
        })).collect::<Vec<_>>(),
        "calls": modules.iter().flat_map(|facts| facts.calls.iter()).map(|item| json!({
            "name": item.name,
            "function_name": item.function_name,
            "ancestor_calls": item.ancestor_calls,
            "function_argument": item.function_argument,
            "returned_cleanup": item.returned_cleanup,
            "location": location(path, &item.span),
        })).collect::<Vec<_>>(),
        "resources": modules.iter().flat_map(|facts| facts.resources.iter()).map(|item| json!({
            "family": item.family,
            "binding_name": item.binding_name,
            "ancestor_calls": item.ancestor_calls,
            "location": location(path, &item.span),
        })).collect::<Vec<_>>(),
        "re_exports": modules.iter().flat_map(|facts| facts.re_exports.iter()).map(|span| location(path, span)).collect::<Vec<_>>(),
        "public_export_count": modules.iter().map(|facts| facts.public_export_count).sum::<usize>(),
        "runtime_declaration_count": modules.iter().map(|facts| facts.runtime_declaration_count).sum::<usize>(),
        "syntax_handles": syntax_handles,
        "svelte": svelte,
    })
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

fn source_kind(source: &ScopedSource) -> &'static str {
    if source.path.extension().and_then(|value| value.to_str()) == Some(WEB_SVELTE_EXTENSION) {
        return "svelte";
    }
    match crate::check::_helpers::project::source_kind(&source.path) {
        Some(SourceKind::JavaScript) => "javascript",
        Some(SourceKind::JavaScriptModule) => "javascript_module",
        Some(SourceKind::JavaScriptCommonJs) => "javascript_commonjs",
        Some(SourceKind::JavaScriptJsx) => "javascript_jsx",
        Some(SourceKind::TypeScript) => "typescript",
        Some(SourceKind::TypeScriptModule) => "typescript_module",
        Some(SourceKind::TypeScriptCommonJs) => "typescript_commonjs",
        Some(SourceKind::TypeScriptDefinition) => "typescript_definition",
        Some(SourceKind::TypeScriptModuleDefinition) => "typescript_module_definition",
        Some(SourceKind::TypeScriptCommonJsDefinition) => "typescript_commonjs_definition",
        Some(SourceKind::TypeScriptJsx) => "typescript_jsx",
        None => "typescript",
    }
}

fn purpose(value: SourcePurpose) -> &'static str {
    match value {
        SourcePurpose::Direct => "direct",
        SourcePurpose::Support => "support",
        SourcePurpose::Excluded => "excluded",
        SourcePurpose::Generated => "generated",
    }
}

fn module_identity(path: &str) -> String {
    let mut value = path.replace(['/', '\\'], ".");
    for suffix in [
        ".d.mts", ".d.cts", ".d.ts", ".svelte", ".mts", ".cts", ".tsx", ".ts", ".mjs", ".cjs",
        ".jsx", ".js",
    ] {
        if value.ends_with(suffix) {
            value.truncate(value.len() - suffix.len());
            break;
        }
    }
    value
}

fn is_route(path: &str) -> bool {
    path.split('/').any(|part| part == WEB_ROUTES_DIRECTORY)
        && Path::new(path)
            .file_name()
            .and_then(|name| name.to_str())
            .is_some_and(|name| name.starts_with('+'))
}

fn is_state_module(path: &str) -> bool {
    path.ends_with(".svelte.ts")
        || path
            .split('/')
            .any(|part| matches!(part, "state" | "_state"))
}

fn location(path: &str, span: &SourceSpan) -> Value {
    json!({"path": path, "line": span.line, "column": span.column})
}

fn syntax_handles(source: &ScopedSource, modules: &[&ModuleFacts]) -> Vec<Value> {
    let path = source.target_path.as_str();
    let mut values: Vec<Value> = Vec::new();
    for facts in modules {
        for item in &facts.imports {
            values.push(syntax_handle(
                path,
                "import",
                Some(&item.specifier),
                &item.span,
            ));
        }
        for item in &facts.functions {
            values.push(syntax_handle(
                path,
                "function",
                Some(&item.name),
                &item.span,
            ));
        }
        for item in &facts.classes {
            values.push(syntax_handle(path, "class", Some(&item.name), &item.span));
        }
        for item in &facts.models {
            values.push(syntax_handle(path, "model", Some(&item.name), &item.span));
        }
        for item in &facts.top_level_bindings {
            values.push(syntax_handle(path, "binding", Some(&item.name), &item.span));
        }
        for item in &facts.calls {
            values.push(syntax_handle(path, "call", Some(&item.name), &item.span));
        }
        for item in &facts.resources {
            values.push(syntax_handle(
                path,
                "resource",
                Some(&item.family),
                &item.span,
            ));
        }
        for span in &facts.re_exports {
            values.push(syntax_handle(path, "re_export", None, span));
        }
    }
    if let Some(ParsedProgram::Svelte(facts)) = source.program.as_ref() {
        for script in &facts.scripts {
            values.push(syntax_handle(
                path,
                "svelte_script",
                None,
                &script.content_span,
            ));
        }
        for rune in &facts.module_runes {
            values.push(syntax_handle(
                path,
                "svelte_rune",
                Some(&rune.name),
                &rune.span,
            ));
        }
    } else if source.analyzer == AnalyzerId::Svelte && is_state_module(path) {
        for facts in modules {
            for (name, span) in state_runes(facts) {
                values.push(syntax_handle(path, "svelte_rune", Some(name), span));
            }
        }
    }
    values.sort_by(|left, right| {
        left["start"]
            .as_u64()
            .cmp(&right["start"].as_u64())
            .then_with(|| left["kind"].as_str().cmp(&right["kind"].as_str()))
            .then_with(|| left["name"].as_str().cmp(&right["name"].as_str()))
    });
    values
}

fn state_runes(facts: &ModuleFacts) -> Vec<(&str, &SourceSpan)> {
    facts
        .top_level_bindings
        .iter()
        .filter_map(|binding| {
            let name = binding.initializer_call.as_deref()?;
            let span = binding.initializer_call_span.as_ref()?;
            fensu_svelte::constants::KNOWN_RUNES
                .contains(&name)
                .then_some((name, span))
        })
        .collect()
}

fn syntax_handle(path: &str, kind: &str, name: Option<&str>, span: &SourceSpan) -> Value {
    json!({
        "kind": kind,
        "name": name,
        "start": span.start,
        "end": span.end,
        "location": location(path, span),
    })
}
