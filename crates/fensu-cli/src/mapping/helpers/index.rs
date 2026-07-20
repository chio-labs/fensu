use std::collections::{BTreeMap, BTreeSet};

use fensu_facts::facts::mapping::main::extract_mapping_facts::extract_mapping_facts;
use fensu_facts::facts::mapping::models::{
    MappingAttributeRow, MappingExpressionRow, MappingImportRow, MappingRows,
};
use fensu_facts::parsing::main::parse_strict::parse_strict;
use fensu_facts::positions::main::index_lines::index_lines;

use crate::helpers::check_policy::python_version;
use crate::mapping::constants::{
    EXPRESSION_ATTRIBUTE, EXPRESSION_NAME, EXPRESSION_SUBSCRIPT, INIT_MODULE_FILE,
};
use crate::mapping::helpers::decoding::decode_source;
use crate::mapping::helpers::identity::build_class_key;
use crate::mapping::models::{
    ClassDefinition, ClassReference, FunctionDefinition, FunctionSyntax, ImportView, MappingCall,
    MappingExpression, MappingParameter, MappingStatement, ModuleImports, ProjectIndex,
    SourceSnapshot,
};

pub(crate) fn build(snapshots: &[SourceSnapshot]) -> Result<ProjectIndex, String> {
    let mut index = ProjectIndex::default();
    for snapshot in snapshots {
        let text = decode_source(snapshot)?;
        let parsed = parse_strict(&text, python_version()).map_err(|failure| {
            format!(
                "Could not parse {}: {}",
                snapshot.path.display(),
                failure.message
            )
        })?;
        let lines = index_lines(&text);
        let rows = extract_mapping_facts(parsed.syntax(), &lines, &text);
        merge_rows(&mut index, snapshot, rows);
    }
    index.protocol_implementations = protocol_implementations(&index.classes);
    Ok(index)
}

pub(crate) fn merge(indexes: impl IntoIterator<Item = ProjectIndex>) -> ProjectIndex {
    let mut merged = ProjectIndex::default();
    for index in indexes {
        merged.functions.extend(index.functions);
        merged.classes.extend(index.classes);
    }
    merged.protocol_implementations = protocol_implementations(&merged.classes);
    merged
}

pub(crate) fn select(
    definitions: &BTreeMap<String, FunctionDefinition>,
    symbol: &str,
) -> Result<FunctionDefinition, String> {
    let matches = if let Some((path_fragment, function_name)) = symbol.rsplit_once("::") {
        let normalized = path_fragment.replace('\\', "/");
        let normalized = normalized.strip_suffix(".py").unwrap_or(&normalized);
        definitions
            .values()
            .filter(|definition| {
                definition.qualified_name() == function_name
                    && definition
                        .path
                        .to_string_lossy()
                        .replace('\\', "/")
                        .strip_suffix(".py")
                        .unwrap_or(&definition.path.to_string_lossy().replace('\\', "/"))
                        .ends_with(normalized)
            })
            .cloned()
            .collect::<Vec<_>>()
    } else if let Some(definition) = definitions.get(symbol) {
        return Ok(definition.clone());
    } else if symbol.contains('.') {
        definitions
            .values()
            .filter(|definition| definition.qualified_name() == symbol)
            .cloned()
            .collect::<Vec<_>>()
    } else {
        definitions
            .values()
            .filter(|definition| definition.name == symbol)
            .cloned()
            .collect::<Vec<_>>()
    };
    if matches.len() == 1 {
        return Ok(matches[0].clone());
    }
    if matches.is_empty() {
        let hint = if symbol.contains('.') {
            format!(" Use a full dotted key or path::{symbol}.")
        } else {
            String::new()
        };
        return Err(format!("Unknown project function: {symbol}.{hint}"));
    }
    let choices = matches
        .iter()
        .map(FunctionDefinition::key)
        .collect::<Vec<_>>()
        .join(", ");
    let path_form = if symbol.contains('.') {
        symbol
    } else {
        "Class.method"
    };
    Err(format!(
        "Ambiguous function {symbol}; choose a full dotted key: {choices}; or use path::{path_form}"
    ))
}

fn merge_rows(index: &mut ProjectIndex, snapshot: &SourceSnapshot, rows: MappingRows) {
    let package_module = snapshot
        .path
        .file_name()
        .is_some_and(|name| name == INIT_MODULE_FILE);
    let imports = ModuleImports {
        runtime: import_view(&rows.runtime_imports, &snapshot.module_name, package_module),
        annotation: import_view(
            &rows.annotation_imports,
            &snapshot.module_name,
            package_module,
        ),
    };
    for row in rows.functions {
        let definition = FunctionDefinition {
            module_name: snapshot.module_name.clone(),
            name: row.name,
            path: snapshot.path.clone(),
            syntax: FunctionSyntax {
                line: row.line,
                parameters: row
                    .parameters
                    .into_iter()
                    .map(|parameter| MappingParameter {
                        name: parameter.name,
                        annotation: parameter.annotation.map(expression),
                    })
                    .collect(),
                returns: row.returns.map(expression),
                statements: row
                    .statements
                    .into_iter()
                    .map(|statement| MappingStatement {
                        control_flow: statement.control_flow,
                        assigned_names: statement.assigned_names.into_iter().collect(),
                        binding_name: statement.binding_name,
                        binding_annotation: statement.binding_annotation.map(expression),
                        binding_value: statement.binding_value.map(expression),
                        calls: statement
                            .calls
                            .into_iter()
                            .map(|call| MappingCall {
                                callee: expression(call.callee),
                                line: call.line,
                            })
                            .collect(),
                    })
                    .collect(),
            },
            imports: imports.clone(),
            owning_class: row.owning_class,
        };
        index.functions.insert(definition.key(), definition);
    }
    for row in rows.classes {
        let bases = row.bases.into_iter().map(expression).collect::<Vec<_>>();
        let definition = ClassDefinition {
            module_name: snapshot.module_name.clone(),
            name: row.name,
            path: snapshot.path.clone(),
            imports: imports.clone(),
            base_keys: bases
                .iter()
                .filter_map(|base| base_key(base, &snapshot.module_name, &imports))
                .collect(),
            protocol: is_protocol(&bases, &imports),
            bases,
            class_attributes: attributes(row.class_attributes),
            instance_attributes: attributes(row.instance_attributes),
        };
        index.classes.insert(definition.key(), definition);
    }
}

fn expression(row: MappingExpressionRow) -> MappingExpression {
    MappingExpression {
        kind: row.kind,
        spelling: row.spelling,
        parts: row.parts,
        child: row.child.map(|child| Box::new(expression(*child))),
        string_value: row.string_value,
    }
}

fn attributes(rows: Vec<MappingAttributeRow>) -> BTreeMap<String, ClassReference> {
    rows.into_iter()
        .map(|row| {
            (
                row.name,
                ClassReference {
                    expression: expression(row.expression),
                    annotation: row.annotation,
                },
            )
        })
        .collect()
}

fn import_view(rows: &[MappingImportRow], module: &str, package: bool) -> ImportView {
    let mut view = ImportView::default();
    for row in rows {
        if row.from_import {
            let Some(imported_from) =
                import_from_module(row.module.as_deref(), row.level, module, package)
            else {
                continue;
            };
            for alias in &row.aliases {
                let local = alias.asname.as_ref().unwrap_or(&alias.name).clone();
                view.symbols
                    .insert(local.clone(), (imported_from.clone(), alias.name.clone()));
                view.modules
                    .insert(local, format!("{imported_from}.{}", alias.name));
            }
        } else {
            for alias in &row.aliases {
                let local = alias.asname.clone().unwrap_or_else(|| {
                    alias
                        .name
                        .split('.')
                        .next()
                        .unwrap_or(&alias.name)
                        .to_owned()
                });
                view.modules.insert(local, alias.name.clone());
            }
        }
    }
    view
}

fn import_from_module(
    imported: Option<&str>,
    level: u32,
    module: &str,
    package: bool,
) -> Option<String> {
    if level == 0 {
        return imported.map(str::to_owned);
    }
    let mut parts = module.split('.').map(str::to_owned).collect::<Vec<_>>();
    if !package {
        parts.pop();
    }
    let parent_count = usize::try_from(level - 1).ok()?;
    if parent_count > parts.len() {
        return None;
    }
    parts.truncate(parts.len() - parent_count);
    if let Some(imported) = imported {
        parts.extend(imported.split('.').map(str::to_owned));
    }
    (!parts.is_empty()).then(|| parts.join("."))
}

fn base_key(base: &MappingExpression, module: &str, imports: &ModuleImports) -> Option<String> {
    if base.kind == EXPRESSION_SUBSCRIPT {
        return base
            .child
            .as_deref()
            .and_then(|child| base_key(child, module, imports));
    }
    if base.kind == EXPRESSION_NAME {
        return imports.runtime.symbols.get(base.name()).map_or_else(
            || Some(build_class_key(module, base.name())),
            |(owner, name)| Some(build_class_key(owner, name)),
        );
    }
    if base.kind == EXPRESSION_ATTRIBUTE {
        let spelling = base.parts.join(".");
        let (first, remainder) = spelling.split_once('.')?;
        return imports
            .runtime
            .modules
            .get(first)
            .map(|owner| format!("{owner}.{remainder}"))
            .or(Some(spelling));
    }
    None
}

fn is_protocol(bases: &[MappingExpression], imports: &ModuleImports) -> bool {
    bases.iter().any(|base| {
        let expression = if base.kind == EXPRESSION_SUBSCRIPT {
            base.child.as_deref().unwrap_or(base)
        } else {
            base
        };
        let mut spelling = expression.parts.join(".");
        if expression.kind == EXPRESSION_NAME {
            if let Some((owner, name)) = imports.runtime.symbols.get(expression.name()) {
                spelling = format!("{owner}.{name}");
            }
        } else if expression.kind == EXPRESSION_ATTRIBUTE {
            if let Some(child) = expression.child.as_deref() {
                if let Some(owner) = imports.runtime.modules.get(child.name()) {
                    spelling = format!("{owner}.{}", expression.name());
                }
            }
        }
        matches!(
            spelling.as_str(),
            "Protocol" | "typing.Protocol" | "typing_extensions.Protocol"
        )
    })
}

fn protocol_implementations(
    classes: &BTreeMap<String, ClassDefinition>,
) -> BTreeMap<String, Vec<String>> {
    let protocols = classes
        .iter()
        .filter(|(_, definition)| definition.protocol)
        .map(|(key, _)| key.clone())
        .collect::<BTreeSet<_>>();
    let mut result = protocols
        .iter()
        .map(|key| (key.clone(), Vec::new()))
        .collect::<BTreeMap<_, _>>();
    for key in classes.keys().filter(|key| !protocols.contains(*key)) {
        let mut ancestors = BTreeSet::new();
        collect_protocols(
            key,
            classes,
            &protocols,
            &mut BTreeSet::new(),
            &mut ancestors,
        );
        for protocol in ancestors {
            result.entry(protocol).or_default().push(key.clone());
        }
    }
    result
}

fn collect_protocols(
    key: &str,
    classes: &BTreeMap<String, ClassDefinition>,
    protocols: &BTreeSet<String>,
    active: &mut BTreeSet<String>,
    result: &mut BTreeSet<String>,
) {
    if !active.insert(key.to_owned()) {
        return;
    }
    if let Some(class) = classes.get(key) {
        for base in &class.base_keys {
            if protocols.contains(base) {
                result.insert(base.clone());
            }
            collect_protocols(base, classes, protocols, active, result);
        }
    }
    active.remove(key);
}
