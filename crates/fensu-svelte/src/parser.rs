//! Strict Svelte structure validation and embedded script parsing.

use fensu_typescript::{ModuleFacts, SourceSpan};
use tree_sitter::{Node, Parser};

use crate::constants::{
    ATTRIBUTE_KIND, ATTRIBUTE_NAME_FIELD, ATTRIBUTE_VALUE_FIELD, CONTEXT_ATTRIBUTE, ELEMENT_KIND,
    END_TAG_KIND, EXPRESSION_KIND, EXPRESSION_VALUE_KIND, KNOWN_RUNES, LANGUAGE_ATTRIBUTE,
    MODULE_ATTRIBUTE, MODULE_CONTEXT_VALUE, NAME_FIELD, PARSER_NO_TREE_MESSAGE, PATTERN_KIND,
    RAW_TEXT_KIND, RECOVERY_NODE_KINDS, SCRIPT_TAG, SNIPPET_BLOCK_KIND, SNIPPET_PARAMETERS_KIND,
    SNIPPET_TYPE_PARAMETERS_KIND, START_TAG_KIND, STYLE_TAG, TAG_NAME_KIND,
    TYPESCRIPT_LANGUAGE_VALUE,
};
use crate::models::{ParseDiagnostic, RuneFact, ScriptContext, ScriptFact, SvelteFacts};

pub fn parse(source: &[u8]) -> Result<SvelteFacts, ParseDiagnostic> {
    let text =
        std::str::from_utf8(source).map_err(|error| invalid_utf8_diagnostic(source, error))?;
    let mut parser = Parser::new();
    parser
        .set_language(&tree_sitter_htmlx_svelte::LANGUAGE.into())
        .map_err(|error| parser_setup_diagnostic(source, &error.to_string()))?;
    let tree = parser
        .parse(text, None)
        .ok_or_else(|| parser_setup_diagnostic(source, PARSER_NO_TREE_MESSAGE))?;
    validate_snippet_names(source, tree.root_node())?;
    if let Some(node) = earliest_invalid_node(tree.root_node()) {
        return Err(ParseDiagnostic {
            message: format!("invalid Svelte structure: {}", node.kind()),
            span: node_span(source, node),
        });
    }
    let scripts: Vec<ScriptNode> = script_nodes(source, text, tree.root_node())?;
    validate_script_contexts(source, &scripts)?;
    let component_source_kind = component_source_kind(&scripts);
    validate_template_syntax(source, tree.root_node(), component_source_kind)?;
    let mut facts = SvelteFacts::default();
    for script in scripts {
        let content = &source[script.content_start..script.content_end];
        let parsed =
            fensu_typescript::parse(content, script.source_kind).map_err(|diagnostic| {
                ParseDiagnostic {
                    message: diagnostic.message,
                    span: shifted_span(source, diagnostic.span, script.content_start),
                }
            })?;
        let shifted = shift_module_facts(source, parsed, script.content_start);
        facts.module_runes.extend(module_runes(&shifted));
        facts.scripts.push(ScriptFact {
            context: script.context,
            content_span: locate_span(source, script.content_start, script.content_end),
            facts: shifted,
        });
    }
    Ok(facts)
}

#[derive(Clone, Copy)]
struct ScriptNode {
    context: ScriptContext,
    source_kind: fensu_typescript::SourceKind,
    element_start: usize,
    content_start: usize,
    content_end: usize,
}

fn invalid_utf8_diagnostic(source: &[u8], error: std::str::Utf8Error) -> ParseDiagnostic {
    let start = error.valid_up_to();
    let end = error
        .error_len()
        .map_or(source.len(), |length| start.saturating_add(length));
    ParseDiagnostic {
        message: "source is not valid UTF-8".to_owned(),
        span: locate_span(source, start, end),
    }
}

fn parser_setup_diagnostic(source: &[u8], message: &str) -> ParseDiagnostic {
    ParseDiagnostic {
        message: message.to_owned(),
        span: locate_span(source, 0, 0),
    }
}

fn earliest_invalid_node(root: Node<'_>) -> Option<Node<'_>> {
    let mut stack = vec![root];
    let mut invalid: Vec<Node<'_>> = Vec::new();
    while let Some(node) = stack.pop() {
        if node.is_error() || node.is_missing() || is_recovery_kind(node.kind()) {
            invalid.push(node);
        }
        let mut cursor = node.walk();
        let children: Vec<Node<'_>> = node.children(&mut cursor).collect();
        stack.extend(children.into_iter().rev());
    }
    invalid.sort_by_key(|node| (node.start_byte(), node.end_byte(), node.kind().to_owned()));
    invalid.into_iter().next()
}

fn is_recovery_kind(kind: &str) -> bool {
    RECOVERY_NODE_KINDS.contains(&kind)
}

fn script_nodes(
    source: &[u8],
    text: &str,
    root: Node<'_>,
) -> Result<Vec<ScriptNode>, ParseDiagnostic> {
    let mut scripts: Vec<ScriptNode> = Vec::new();
    let mut style_start: Option<usize> = None;
    let mut cursor = root.walk();
    for node in root.children(&mut cursor) {
        if node.kind() != ELEMENT_KIND {
            continue;
        }
        let Some((start_tag, tag_name)) = element_tag(text, node) else {
            continue;
        };
        if tag_name == SCRIPT_TAG {
            scripts.push(as_script_node(source, text, node, start_tag)?);
        }
        if tag_name == STYLE_TAG && style_start.replace(node.start_byte()).is_some() {
            return Err(ParseDiagnostic {
                message: "duplicate top-level style".to_owned(),
                span: locate_span(source, node.start_byte(), node.start_byte()),
            });
        }
    }
    scripts.sort_by_key(|script| script.element_start);
    Ok(scripts)
}

fn element_tag<'source, 'tree>(
    source: &'source str,
    element: Node<'tree>,
) -> Option<(Node<'tree>, &'source str)> {
    let mut cursor = element.walk();
    let children: Vec<Node<'_>> = element.children(&mut cursor).collect();
    let start_tag = children.iter().find(|node| node.kind() == START_TAG_KIND)?;
    let tag_name = child_with_kind(*start_tag, TAG_NAME_KIND)?;
    Some((*start_tag, source.get(tag_name.byte_range())?))
}

fn as_script_node(
    source: &[u8],
    text: &str,
    element: Node<'_>,
    start_tag: Node<'_>,
) -> Result<ScriptNode, ParseDiagnostic> {
    let mut cursor = element.walk();
    let children: Vec<Node<'_>> = element.children(&mut cursor).collect();
    let Some(end_tag) = children.iter().find(|node| node.kind() == END_TAG_KIND) else {
        return Err(ParseDiagnostic {
            message: "script element is missing an end tag".to_owned(),
            span: node_span(source, element),
        });
    };
    let raw_text = children.iter().find(|node| node.kind() == RAW_TEXT_KIND);
    let content_start = raw_text.map_or(start_tag.end_byte(), |node| node.start_byte());
    let content_end = raw_text.map_or(end_tag.start_byte(), |node| node.end_byte());
    let context = script_context(source, text, start_tag)?;
    let source_kind = if has_typescript_language(text, start_tag) {
        fensu_typescript::SourceKind::TypeScript
    } else {
        fensu_typescript::SourceKind::JavaScript
    };
    Ok(ScriptNode {
        context,
        source_kind,
        element_start: element.start_byte(),
        content_start,
        content_end,
    })
}

fn child_with_kind<'tree>(node: Node<'tree>, kind: &str) -> Option<Node<'tree>> {
    let mut cursor = node.walk();
    let child = node
        .children(&mut cursor)
        .find(|candidate| candidate.kind() == kind);
    child
}

fn script_context(
    source: &[u8],
    text: &str,
    start_tag: Node<'_>,
) -> Result<ScriptContext, ParseDiagnostic> {
    let mut context = ScriptContext::Instance;
    let mut context_declared = false;
    let mut cursor = start_tag.walk();
    for attribute in start_tag
        .children(&mut cursor)
        .filter(|node| node.kind() == ATTRIBUTE_KIND)
    {
        let Some(name_node) = attribute.child_by_field_name(ATTRIBUTE_NAME_FIELD) else {
            continue;
        };
        let Some(name) = text.get(name_node.byte_range()) else {
            continue;
        };
        if name != MODULE_ATTRIBUTE && name != CONTEXT_ATTRIBUTE {
            continue;
        }
        if context_declared {
            return Err(script_attribute_diagnostic(
                source,
                attribute,
                "duplicate script context attribute",
            ));
        }
        context_declared = true;
        let value = attribute
            .child_by_field_name(ATTRIBUTE_VALUE_FIELD)
            .and_then(|node| text.get(node.byte_range()))
            .map(normalized_attribute_value);
        let valid = (name == MODULE_ATTRIBUTE && value.is_none())
            || (name == CONTEXT_ATTRIBUTE && value == Some(MODULE_CONTEXT_VALUE));
        if !valid {
            return Err(script_attribute_diagnostic(
                source,
                attribute,
                "invalid script context attribute",
            ));
        }
        context = ScriptContext::Module;
    }
    Ok(context)
}

fn has_typescript_language(source: &str, start_tag: Node<'_>) -> bool {
    let mut cursor = start_tag.walk();
    let is_typescript = start_tag
        .children(&mut cursor)
        .filter(|node| node.kind() == ATTRIBUTE_KIND)
        .any(|attribute| {
            let name = attribute
                .child_by_field_name(ATTRIBUTE_NAME_FIELD)
                .and_then(|node| source.get(node.byte_range()));
            let value = attribute
                .child_by_field_name(ATTRIBUTE_VALUE_FIELD)
                .and_then(|node| source.get(node.byte_range()))
                .map(normalized_attribute_value);
            name == Some(LANGUAGE_ATTRIBUTE) && value == Some(TYPESCRIPT_LANGUAGE_VALUE)
        });
    is_typescript
}

fn normalized_attribute_value(value: &str) -> &str {
    value
        .trim()
        .trim_matches(|character| character == '\'' || character == '"')
}

fn script_attribute_diagnostic(
    source: &[u8],
    attribute: Node<'_>,
    message: &str,
) -> ParseDiagnostic {
    ParseDiagnostic {
        message: message.to_owned(),
        span: node_span(source, attribute),
    }
}

fn validate_script_contexts(source: &[u8], scripts: &[ScriptNode]) -> Result<(), ParseDiagnostic> {
    let mut module_seen = false;
    let mut instance_seen = false;
    for script in scripts {
        let duplicate = match script.context {
            ScriptContext::Module => std::mem::replace(&mut module_seen, true),
            ScriptContext::Instance => std::mem::replace(&mut instance_seen, true),
        };
        if duplicate {
            return Err(ParseDiagnostic {
                message: format!("duplicate {:?} script", script.context),
                span: locate_span(source, script.element_start, script.element_start),
            });
        }
    }
    Ok(())
}

fn component_source_kind(scripts: &[ScriptNode]) -> fensu_typescript::SourceKind {
    if scripts
        .iter()
        .any(|script| script.source_kind == fensu_typescript::SourceKind::TypeScript)
    {
        fensu_typescript::SourceKind::TypeScript
    } else {
        fensu_typescript::SourceKind::JavaScript
    }
}

fn node_span(source: &[u8], node: Node<'_>) -> SourceSpan {
    locate_span(source, node.start_byte(), node.end_byte())
}

fn locate_span(source: &[u8], start: usize, end: usize) -> SourceSpan {
    let bounded_start = start.min(source.len());
    let bounded_end = end.max(bounded_start).min(source.len());
    let prefix = &source[..bounded_start];
    let line = prefix.iter().filter(|byte| **byte == b'\n').count() + 1;
    let column = prefix
        .iter()
        .rposition(|byte| *byte == b'\n')
        .map_or(prefix.len(), |index| prefix.len() - index - 1);
    SourceSpan {
        start: bounded_start,
        end: bounded_end,
        line,
        column,
    }
}

fn shifted_span(source: &[u8], span: SourceSpan, offset: usize) -> SourceSpan {
    locate_span(
        source,
        span.start.saturating_add(offset),
        span.end.saturating_add(offset),
    )
}

fn shift_module_facts(source: &[u8], mut facts: ModuleFacts, offset: usize) -> ModuleFacts {
    for imported in &mut facts.imports {
        imported.span = shifted_span(source, imported.span.clone(), offset);
    }
    for class in &mut facts.classes {
        class.span = shifted_span(source, class.span.clone(), offset);
    }
    for model in &mut facts.models {
        model.span = shifted_span(source, model.span.clone(), offset);
    }
    for function in &mut facts.functions {
        function.span = shifted_span(source, function.span.clone(), offset);
    }
    for binding in &mut facts.local_bindings {
        binding.span = shifted_span(source, binding.span.clone(), offset);
    }
    for binding in &mut facts.top_level_bindings {
        binding.span = shifted_span(source, binding.span.clone(), offset);
        binding.initializer_call_span = binding
            .initializer_call_span
            .take()
            .map(|span| shifted_span(source, span, offset));
    }
    facts
}

fn module_runes(facts: &ModuleFacts) -> Vec<RuneFact> {
    let mut runes: Vec<RuneFact> = Vec::new();
    for binding in &facts.top_level_bindings {
        let Some(name) = binding.initializer_call.as_ref() else {
            continue;
        };
        if !KNOWN_RUNES.contains(&name.as_str()) {
            continue;
        }
        let Some(span) = binding.initializer_call_span.as_ref() else {
            continue;
        };
        runes.push(RuneFact {
            name: name.clone(),
            span: span.clone(),
        });
    }
    runes
}

fn validate_template_syntax(
    source: &[u8],
    root: Node<'_>,
    source_kind: fensu_typescript::SourceKind,
) -> Result<(), ParseDiagnostic> {
    let mut stack: Vec<Node<'_>> = vec![root];
    while let Some(node) = stack.pop() {
        match node.kind() {
            EXPRESSION_KIND | EXPRESSION_VALUE_KIND => {
                validate_expression_node(source, node, source_kind)?;
            }
            PATTERN_KIND if !is_snippet_parameter(node) => {
                validate_binding_pattern_node(source, node, source_kind)?;
            }
            SNIPPET_PARAMETERS_KIND => {
                validate_snippet_parameters(source, node, source_kind)?;
            }
            SNIPPET_TYPE_PARAMETERS_KIND => {
                validate_snippet_type_parameters(source, node, source_kind)?;
            }
            _ => {}
        }
        let mut cursor = node.walk();
        let children: Vec<Node<'_>> = node.children(&mut cursor).collect();
        stack.extend(children.into_iter().rev());
    }
    Ok(())
}

fn validate_snippet_names(source: &[u8], root: Node<'_>) -> Result<(), ParseDiagnostic> {
    let mut stack: Vec<Node<'_>> = vec![root];
    while let Some(node) = stack.pop() {
        if node.kind() == SNIPPET_BLOCK_KIND {
            validate_snippet_name(source, node)?;
        }
        let mut cursor = node.walk();
        let children: Vec<Node<'_>> = node.children(&mut cursor).collect();
        stack.extend(children.into_iter().rev());
    }
    Ok(())
}

fn validate_expression_node(
    source: &[u8],
    node: Node<'_>,
    source_kind: fensu_typescript::SourceKind,
) -> Result<(), ParseDiagnostic> {
    let Some(content) = node.child_by_field_name(crate::constants::CONTENT_FIELD) else {
        if node.kind() == EXPRESSION_KIND {
            return Err(ParseDiagnostic {
                message: "empty template expression".to_owned(),
                span: node_span(source, node),
            });
        }
        return Ok(());
    };
    let expression = &source[content.byte_range()];
    fensu_typescript::parse_expression(expression, source_kind).map_err(|diagnostic| {
        ParseDiagnostic {
            message: diagnostic.message,
            span: shifted_span(source, diagnostic.span, content.start_byte()),
        }
    })
}

fn is_snippet_parameter(node: Node<'_>) -> bool {
    node.parent()
        .is_some_and(|parent| parent.kind() == SNIPPET_PARAMETERS_KIND)
}

fn validate_binding_pattern_node(
    source: &[u8],
    node: Node<'_>,
    source_kind: fensu_typescript::SourceKind,
) -> Result<(), ParseDiagnostic> {
    let Some(content) = node.child_by_field_name(crate::constants::CONTENT_FIELD) else {
        return Err(ParseDiagnostic {
            message: "empty binding pattern".to_owned(),
            span: node_span(source, node),
        });
    };
    fensu_typescript::parse_binding_pattern(&source[content.byte_range()], source_kind).map_err(
        |diagnostic| ParseDiagnostic {
            message: diagnostic.message,
            span: shifted_span(source, diagnostic.span, content.start_byte()),
        },
    )
}

fn validate_snippet_name(source: &[u8], snippet: Node<'_>) -> Result<(), ParseDiagnostic> {
    let name = snippet.child_by_field_name(NAME_FIELD);
    let missing = name.is_none_or(|node| {
        node.start_byte() == node.end_byte()
            || source
                .get(node.byte_range())
                .is_none_or(|value| value.iter().all(u8::is_ascii_whitespace))
    });
    if missing {
        return Err(ParseDiagnostic {
            message: "snippet name is required".to_owned(),
            span: locate_span(source, snippet.start_byte(), snippet.start_byte()),
        });
    }
    Ok(())
}

fn validate_snippet_parameters(
    source: &[u8],
    parameters: Node<'_>,
    source_kind: fensu_typescript::SourceKind,
) -> Result<(), ParseDiagnostic> {
    fensu_typescript::parse_formal_parameters(&source[parameters.byte_range()], source_kind)
        .map_err(|diagnostic| ParseDiagnostic {
            message: diagnostic.message,
            span: shifted_span(source, diagnostic.span, parameters.start_byte()),
        })
}

fn validate_snippet_type_parameters(
    source: &[u8],
    parameters: Node<'_>,
    source_kind: fensu_typescript::SourceKind,
) -> Result<(), ParseDiagnostic> {
    fensu_typescript::parse_type_parameters(&source[parameters.byte_range()], source_kind).map_err(
        |diagnostic| ParseDiagnostic {
            message: diagnostic.message,
            span: shifted_span(source, diagnostic.span, parameters.start_byte()),
        },
    )
}
