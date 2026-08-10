//! Strict Oxc parsing and owned fact extraction.

use std::collections::{HashMap, HashSet};

use oxc_allocator::Allocator;
use oxc_ast::ast::{
    ArrowFunctionBody, ArrowFunctionExpression, BindingPattern, CallExpression, Class, Declaration,
    ExportDefaultDeclarationKind, Expression, Function, ImportDeclarationSpecifier,
    ImportOrExportKind, MethodDefinition, ObjectProperty, PropertyKey, Statement,
    TSInterfaceDeclaration, TSSignature, TSType, TSTypeAliasDeclaration, VariableDeclarator,
};
use oxc_ast_visit::{walk, Visit};
use oxc_diagnostics::{Diagnostics, OxcDiagnostic};
use oxc_parser::Parser;
use oxc_semantic::SemanticBuilder;
use oxc_span::{FileExtension, GetSpan, SourceType, Span};
use oxc_syntax::scope::ScopeFlags;

use crate::models::{
    ClassFact, FunctionFact, ImportFact, LocalBindingFact, ModelFact, ModelKind, ModuleFacts,
    ParseDiagnostic, SourceKind, SourceSpan, TopLevelBindingFact,
};

pub fn parse(source: &[u8], source_kind: SourceKind) -> Result<ModuleFacts, ParseDiagnostic> {
    let text =
        std::str::from_utf8(source).map_err(|error| invalid_utf8_diagnostic(source, error))?;
    let allocator = Allocator::default();
    let parsed: oxc_parser::ParserReturn<'_> =
        Parser::new(&allocator, text, oxc_source_type(source_kind)).parse();
    if !parsed.diagnostics.is_empty() {
        return Err(earliest_diagnostic(text, &parsed.diagnostics));
    }
    let semantic = SemanticBuilder::new()
        .with_check_syntax_error(true)
        .build(&parsed.program);
    if !semantic.diagnostics.is_empty() {
        return Err(earliest_diagnostic(text, &semantic.diagnostics));
    }
    Ok(collect_facts(text, &parsed.program.body))
}

pub fn parse_typescript(source: &[u8]) -> Result<ModuleFacts, ParseDiagnostic> {
    parse(source, SourceKind::TypeScript)
}

pub fn parse_javascript(source: &[u8]) -> Result<ModuleFacts, ParseDiagnostic> {
    parse(source, SourceKind::JavaScript)
}

pub fn parse_expression(source: &[u8], source_kind: SourceKind) -> Result<(), ParseDiagnostic> {
    const EXPRESSION_PREFIX: &str = "const __fensu_expression = (";
    const EXPRESSION_SUFFIX: &str = ");";

    parse_wrapped_syntax(source, source_kind, EXPRESSION_PREFIX, EXPRESSION_SUFFIX)
}

pub fn parse_binding_pattern(
    source: &[u8],
    source_kind: SourceKind,
) -> Result<(), ParseDiagnostic> {
    const BINDING_PREFIX: &str = "const ";
    const BINDING_SUFFIX: &str = " = __fensu_value;";

    parse_wrapped_syntax(source, source_kind, BINDING_PREFIX, BINDING_SUFFIX)
}

pub fn parse_formal_parameters(
    source: &[u8],
    source_kind: SourceKind,
) -> Result<(), ParseDiagnostic> {
    const PARAMETERS_PREFIX: &str = "function __fensu(";
    const PARAMETERS_SUFFIX: &str = ") {}";

    parse_wrapped_syntax(source, source_kind, PARAMETERS_PREFIX, PARAMETERS_SUFFIX)
}

pub fn parse_type_parameters(
    source: &[u8],
    source_kind: SourceKind,
) -> Result<(), ParseDiagnostic> {
    const TYPE_PARAMETERS_PREFIX: &str = "function __fensu";
    const TYPE_PARAMETERS_SUFFIX: &str = "() {}";

    parse_wrapped_syntax(
        source,
        source_kind,
        TYPE_PARAMETERS_PREFIX,
        TYPE_PARAMETERS_SUFFIX,
    )
}

fn parse_wrapped_syntax(
    source: &[u8],
    source_kind: SourceKind,
    prefix: &str,
    suffix: &str,
) -> Result<(), ParseDiagnostic> {
    let text =
        std::str::from_utf8(source).map_err(|error| invalid_utf8_diagnostic(source, error))?;
    let wrapped = format!("{prefix}{text}{suffix}");
    parse(wrapped.as_bytes(), source_kind).map_or_else(
        |diagnostic| {
            let start = diagnostic
                .span
                .start
                .saturating_sub(prefix.len())
                .min(source.len());
            let end = diagnostic
                .span
                .end
                .saturating_sub(prefix.len())
                .min(source.len());
            Err(ParseDiagnostic {
                message: diagnostic.message,
                span: locate_span(source, start, end),
            })
        },
        |_| Ok(()),
    )
}

fn oxc_source_type(source_kind: SourceKind) -> SourceType {
    match source_kind {
        SourceKind::JavaScript => SourceType::unambiguous(),
        SourceKind::JavaScriptModule => SourceType::from(FileExtension::Mjs),
        SourceKind::JavaScriptCommonJs => SourceType::from(FileExtension::Cjs),
        SourceKind::JavaScriptJsx => SourceType::jsx(),
        SourceKind::TypeScript => SourceType::ts(),
        SourceKind::TypeScriptModule => SourceType::from(FileExtension::Mts),
        SourceKind::TypeScriptCommonJs => SourceType::from(FileExtension::Cts),
        SourceKind::TypeScriptDefinition => {
            SourceType::from(FileExtension::Ts).with_typescript_definition(true)
        }
        SourceKind::TypeScriptModuleDefinition => {
            SourceType::from(FileExtension::Mts).with_typescript_definition(true)
        }
        SourceKind::TypeScriptCommonJsDefinition => {
            SourceType::from(FileExtension::Cts).with_typescript_definition(true)
        }
        SourceKind::TypeScriptJsx => SourceType::tsx(),
    }
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

fn earliest_diagnostic(source: &str, diagnostics: &Diagnostics) -> ParseDiagnostic {
    let mut candidates: Vec<(usize, usize, String)> =
        diagnostics.iter().map(diagnostic_parts).collect();
    candidates.sort();
    let (start, length, message) = candidates
        .into_iter()
        .next()
        .unwrap_or_else(|| (0, 0, "source contains invalid syntax".to_owned()));
    ParseDiagnostic {
        message,
        span: locate_span(source.as_bytes(), start, start.saturating_add(length)),
    }
}

fn diagnostic_parts(diagnostic: &OxcDiagnostic) -> (usize, usize, String) {
    let label = diagnostic.labels.first();
    let start = label.map_or(0, |value| value.inner().offset() as usize);
    let length = label.map_or(0, |value| value.inner().len() as usize);
    (start, length, diagnostic.to_string())
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

fn owned_span(source: &str, span: Span) -> SourceSpan {
    locate_span(source.as_bytes(), span.start as usize, span.end as usize)
}

fn collect_facts(source: &str, statements: &[Statement<'_>]) -> ModuleFacts {
    let mut collector = TopLevelCollector {
        source,
        facts: ModuleFacts::default(),
        exported_functions: HashSet::new(),
        function_names: HashMap::new(),
    };
    for statement in statements {
        collector.collect(statement);
    }
    let mut name_visitor = FunctionNameVisitor {
        source,
        names: collector.function_names,
    };
    for statement in statements {
        name_visitor.visit_statement(statement);
    }
    let mut visitor = FactVisitor {
        source,
        exported_functions: collector.exported_functions,
        function_names: name_visitor.names,
        function_stack: Vec::new(),
        local_names: Vec::new(),
        variable_statement_depth: 0,
        functions: Vec::new(),
        local_bindings: Vec::new(),
    };
    for statement in statements {
        visitor.visit_statement(statement);
    }
    collector.facts.functions = visitor.functions;
    collector.facts.local_bindings = visitor.local_bindings;
    collector.facts
}

struct TopLevelCollector<'s> {
    source: &'s str,
    facts: ModuleFacts,
    exported_functions: HashSet<u32>,
    function_names: HashMap<u32, String>,
}

impl TopLevelCollector<'_> {
    fn collect(&mut self, statement: &Statement<'_>) {
        match statement {
            Statement::ImportDeclaration(imported) => self.collect_import(imported),
            Statement::ClassDeclaration(class) => self.collect_class(class, false),
            Statement::TSInterfaceDeclaration(interface) => {
                self.collect_interface(interface, false);
            }
            Statement::TSTypeAliasDeclaration(alias) => self.collect_alias(alias, false),
            Statement::VariableDeclaration(declaration) => {
                self.collect_top_level_bindings(declaration);
            }
            Statement::ExportDeclaration(exported) => {
                self.collect_exported_declaration(&exported.declaration);
            }
            Statement::ExportDefaultDeclaration(exported) => match &exported.declaration {
                ExportDefaultDeclarationKind::ClassDeclaration(class) => {
                    self.collect_class(class, true);
                }
                ExportDefaultDeclarationKind::FunctionDeclaration(function) => {
                    self.exported_functions.insert(function.span.start);
                }
                ExportDefaultDeclarationKind::TSInterfaceDeclaration(interface) => {
                    self.collect_interface(interface, true);
                }
                _ => {}
            },
            _ => {}
        }
    }

    fn collect_import(&mut self, imported: &oxc_ast::ast::ImportDeclaration<'_>) {
        let namespace = imported.specifiers.as_ref().is_some_and(|specifiers| {
            specifiers.iter().any(|specifier| {
                matches!(
                    specifier,
                    ImportDeclarationSpecifier::ImportNamespaceSpecifier(_)
                )
            })
        });
        let binding_count = imported.specifiers.as_ref().map_or(0, |value| value.len());
        self.facts.imported_binding_count += binding_count;
        self.facts.imports.push(ImportFact {
            specifier: imported.source.value.to_string(),
            binding_count,
            type_only: imported.import_kind == ImportOrExportKind::Type,
            namespace,
            span: owned_span(self.source, imported.span),
        });
    }

    fn collect_exported_declaration(&mut self, declaration: &Declaration<'_>) {
        match declaration {
            Declaration::ClassDeclaration(class) => self.collect_class(class, true),
            Declaration::TSInterfaceDeclaration(interface) => {
                self.collect_interface(interface, true);
            }
            Declaration::TSTypeAliasDeclaration(alias) => self.collect_alias(alias, true),
            Declaration::FunctionDeclaration(function) => {
                self.exported_functions.insert(function.span.start);
            }
            Declaration::VariableDeclaration(declaration) => {
                self.collect_top_level_bindings(declaration);
                for declarator in &declaration.declarations {
                    let Some(name) = binding_name(&declarator.id) else {
                        continue;
                    };
                    let Some(initializer) = declarator.init.as_ref() else {
                        continue;
                    };
                    if matches!(
                        initializer,
                        Expression::ArrowFunctionExpression(_) | Expression::FunctionExpression(_)
                    ) {
                        self.exported_functions.insert(initializer.span().start);
                        self.function_names
                            .insert(initializer.span().start, name.to_owned());
                    }
                }
            }
            _ => {}
        }
    }

    fn collect_top_level_bindings(&mut self, declaration: &oxc_ast::ast::VariableDeclaration<'_>) {
        for declarator in &declaration.declarations {
            let initializer_call = declarator
                .init
                .as_ref()
                .and_then(|initializer| initializer_call(self.source, initializer));
            self.facts.top_level_bindings.push(TopLevelBindingFact {
                name: binding_name(&declarator.id).map_or_else(
                    || span_text(self.source, declarator.id.span()).to_owned(),
                    str::to_owned,
                ),
                initializer_call: initializer_call
                    .as_ref()
                    .map(|(call_name, _)| call_name.clone()),
                initializer_call_span: initializer_call.map(|(_, call_span)| call_span),
                span: owned_span(self.source, declarator.id.span()),
            });
        }
    }

    fn collect_class(&mut self, class: &Class<'_>, exported: bool) {
        if class.declare {
            return;
        }
        let Some(identifier) = class.id.as_ref() else {
            return;
        };
        self.facts.classes.push(ClassFact {
            name: identifier.name.to_string(),
            exported,
            span: owned_span(self.source, identifier.span),
        });
    }

    fn collect_interface(&mut self, interface: &TSInterfaceDeclaration<'_>, exported: bool) {
        self.facts.models.push(ModelFact {
            name: interface.id.name.to_string(),
            kind: ModelKind::Interface,
            exported,
            readonly_shape: readonly_members(self.source, &interface.body.body),
            span: owned_span(self.source, interface.id.span),
        });
    }

    fn collect_alias(&mut self, alias: &TSTypeAliasDeclaration<'_>, exported: bool) {
        let TSType::TSTypeLiteral(literal) = &alias.type_annotation else {
            return;
        };
        self.facts.models.push(ModelFact {
            name: alias.id.name.to_string(),
            kind: ModelKind::TypeLiteralAlias,
            exported,
            readonly_shape: readonly_members(self.source, &literal.members),
            span: owned_span(self.source, alias.id.span),
        });
    }
}

fn initializer_call(source: &str, expression: &Expression<'_>) -> Option<(String, SourceSpan)> {
    let Expression::CallExpression(call) = expression else {
        return None;
    };
    Some((
        span_text(source, call.callee.span()).to_owned(),
        owned_span(source, call.callee.span()),
    ))
}

fn readonly_members(source: &str, members: &[TSSignature<'_>]) -> bool {
    members.iter().all(|member| match member {
        TSSignature::TSPropertySignature(property) => {
            property.readonly
                && property.type_annotation.as_ref().is_none_or(|annotation| {
                    readonly_collection(source, &annotation.type_annotation)
                })
        }
        _ => true,
    })
}

fn readonly_collection(source: &str, value: &TSType<'_>) -> bool {
    match value {
        TSType::TSArrayType(_) | TSType::TSTupleType(_) => false,
        TSType::TSTypeOperatorType(_) => true,
        TSType::TSTypeReference(reference) => {
            let name = span_text(source, reference.type_name.span());
            !matches!(name, "Array" | "Map" | "Set" | "WeakMap" | "WeakSet")
        }
        TSType::TSUnionType(union) => union
            .types
            .iter()
            .all(|item| readonly_collection(source, item)),
        TSType::TSIntersectionType(intersection) => intersection
            .types
            .iter()
            .all(|item| readonly_collection(source, item)),
        _ => true,
    }
}

fn span_text(source: &str, span: Span) -> &str {
    source
        .get(span.start as usize..span.end as usize)
        .unwrap_or_default()
}

fn binding_name<'a>(pattern: &'a BindingPattern<'a>) -> Option<&'a str> {
    match pattern {
        BindingPattern::BindingIdentifier(identifier) => Some(identifier.name.as_str()),
        _ => None,
    }
}

struct FunctionNameVisitor<'s> {
    source: &'s str,
    names: HashMap<u32, String>,
}

impl<'a> Visit<'a> for FunctionNameVisitor<'_> {
    fn visit_variable_declarator(&mut self, declarator: &VariableDeclarator<'a>) {
        let name = binding_name(&declarator.id);
        let initializer = declarator.init.as_ref();
        if let (Some(name), Some(initializer)) = (name, initializer) {
            if matches!(
                initializer,
                Expression::ArrowFunctionExpression(_) | Expression::FunctionExpression(_)
            ) {
                self.names.insert(initializer.span().start, name.to_owned());
            }
        }
        walk::walk_variable_declarator(self, declarator);
    }

    fn visit_method_definition(&mut self, method: &MethodDefinition<'a>) {
        self.names.insert(
            method.value.span.start,
            property_key_name(self.source, &method.key),
        );
        walk::walk_method_definition(self, method);
    }

    fn visit_object_property(&mut self, property: &ObjectProperty<'a>) {
        if property.method {
            if let Expression::FunctionExpression(function) = &property.value {
                self.names.insert(
                    function.span.start,
                    property_key_name(self.source, &property.key),
                );
            }
        }
        walk::walk_object_property(self, property);
    }
}

fn property_key_name(source: &str, key: &PropertyKey<'_>) -> String {
    match key {
        PropertyKey::StaticIdentifier(identifier) => identifier.name.to_string(),
        PropertyKey::PrivateIdentifier(identifier) => format!("#{}", identifier.name),
        _ => span_text(source, key.span()).to_owned(),
    }
}

struct FactVisitor<'s> {
    source: &'s str,
    exported_functions: HashSet<u32>,
    function_names: HashMap<u32, String>,
    function_stack: Vec<String>,
    local_names: Vec<HashSet<String>>,
    variable_statement_depth: usize,
    functions: Vec<FunctionFact>,
    local_bindings: Vec<LocalBindingFact>,
}

impl<'a> Visit<'a> for FactVisitor<'_> {
    fn visit_statement(&mut self, statement: &Statement<'a>) {
        let variable_statement = matches!(statement, Statement::VariableDeclaration(_));
        if variable_statement {
            self.variable_statement_depth += 1;
        }
        walk::walk_statement(self, statement);
        if variable_statement {
            self.variable_statement_depth -= 1;
        }
    }

    fn visit_function(&mut self, function: &Function<'a>, flags: ScopeFlags) {
        if function.body.is_none() {
            return;
        }
        let name = function
            .id
            .as_ref()
            .map(|identifier| identifier.name.to_string())
            .or_else(|| self.function_names.get(&function.span.start).cloned())
            .unwrap_or_else(|| "<anonymous>".to_owned());
        let metrics = function_metrics(self.source, function.body.as_deref());
        let parameter_count = function.params.items.len()
            + usize::from(function.params.rest.is_some())
            + usize::from(function.this_param.is_some());
        let parameters_annotated = function
            .params
            .items
            .iter()
            .all(|parameter| parameter.type_annotation.is_some())
            && function
                .params
                .rest
                .as_ref()
                .is_none_or(|parameter| parameter.type_annotation.is_some())
            && function
                .this_param
                .as_ref()
                .is_none_or(|parameter| parameter.type_annotation.is_some());
        self.functions.push(function_fact(FunctionFactRequest {
            source: self.source,
            name: &name,
            span: function.span,
            parameter_count,
            parameters_annotated,
            return_span: function.return_type.as_ref().map(|value| value.span),
            exported: self.exported_functions.contains(&function.span.start),
            metrics,
        }));
        self.function_stack.push(name);
        self.local_names.push(HashSet::new());
        walk::walk_function(self, function, flags);
        self.local_names.pop();
        self.function_stack.pop();
    }

    fn visit_arrow_function_expression(&mut self, arrow: &ArrowFunctionExpression<'a>) {
        let name = self
            .function_names
            .get(&arrow.span.start)
            .cloned()
            .unwrap_or_else(|| "<anonymous>".to_owned());
        let metrics = arrow_function_metrics(self.source, &arrow.body);
        let parameter_count = arrow.params.items.len() + usize::from(arrow.params.rest.is_some());
        let parameters_annotated = arrow
            .params
            .items
            .iter()
            .all(|parameter| parameter.type_annotation.is_some())
            && arrow
                .params
                .rest
                .as_ref()
                .is_none_or(|parameter| parameter.type_annotation.is_some());
        self.functions.push(function_fact(FunctionFactRequest {
            source: self.source,
            name: &name,
            span: arrow.span,
            parameter_count,
            parameters_annotated,
            return_span: arrow.return_type.as_ref().map(|value| value.span),
            exported: self.exported_functions.contains(&arrow.span.start),
            metrics,
        }));
        self.function_stack.push(name);
        self.local_names.push(HashSet::new());
        walk::walk_arrow_function_expression(self, arrow);
        self.local_names.pop();
        self.function_stack.pop();
    }

    fn visit_variable_declarator(&mut self, declarator: &VariableDeclarator<'a>) {
        let Some(function_name) = self.function_stack.last().cloned() else {
            self.walk_declarator(declarator);
            return;
        };
        if self.variable_statement_depth == 0 {
            self.walk_declarator(declarator);
            return;
        }
        let Some(name) = binding_name(&declarator.id) else {
            self.walk_declarator(declarator);
            return;
        };
        let is_first = self
            .local_names
            .last_mut()
            .is_some_and(|names| names.insert(name.to_owned()));
        if is_first {
            let initializer = declarator.init.as_ref();
            self.local_bindings.push(LocalBindingFact {
                name: name.to_owned(),
                function_name,
                scalar_literal: initializer
                    .is_some_and(|expression| is_scalar_literal(self.source, expression)),
                explicitly_typed: declarator.type_annotation.is_some(),
                satisfies_type: initializer.is_some_and(|expression| {
                    matches!(expression, Expression::TSSatisfiesExpression(_))
                }),
                generic_call_or_new: initializer.is_some_and(has_generic_call_or_new),
                span: owned_span(self.source, declarator.id.span()),
            });
        }
        self.walk_declarator(declarator);
    }
}

impl<'a> FactVisitor<'_> {
    fn walk_declarator(&mut self, declarator: &VariableDeclarator<'a>) {
        let statement_depth = std::mem::take(&mut self.variable_statement_depth);
        walk::walk_variable_declarator(self, declarator);
        self.variable_statement_depth = statement_depth;
    }
}

struct FunctionFactRequest<'a> {
    source: &'a str,
    name: &'a str,
    span: Span,
    parameter_count: usize,
    parameters_annotated: bool,
    return_span: Option<Span>,
    exported: bool,
    metrics: FunctionMetrics,
}

fn function_fact(request: FunctionFactRequest<'_>) -> FunctionFact {
    FunctionFact {
        name: request.name.to_owned(),
        exported: request.exported,
        parameter_count: request.parameter_count,
        parameters_annotated: request.parameters_annotated,
        return_type: request.return_span.map(|value| {
            span_text(request.source, value)
                .trim_start_matches(':')
                .trim()
                .to_owned()
        }),
        statement_count: request.metrics.statement_count,
        distinct_call_count: request.metrics.calls.len(),
        local_count: request.metrics.local_count,
        span: owned_span(request.source, request.span),
    }
}

#[derive(Default)]
struct FunctionMetrics {
    statement_count: usize,
    local_count: usize,
    calls: HashSet<String>,
}

fn function_metrics(
    source: &str,
    body: Option<&oxc_ast::ast::FunctionBody<'_>>,
) -> FunctionMetrics {
    let mut visitor = FunctionMetricsVisitor {
        source,
        metrics: FunctionMetrics::default(),
    };
    if let Some(body) = body {
        visitor.visit_function_body(body);
    }
    visitor.metrics
}

fn arrow_function_metrics(source: &str, body: &ArrowFunctionBody<'_>) -> FunctionMetrics {
    let mut visitor = FunctionMetricsVisitor {
        source,
        metrics: FunctionMetrics::default(),
    };
    visitor.visit_arrow_function_body(body);
    visitor.metrics
}

struct FunctionMetricsVisitor<'s> {
    source: &'s str,
    metrics: FunctionMetrics,
}

impl<'a> Visit<'a> for FunctionMetricsVisitor<'_> {
    fn visit_statement(&mut self, statement: &Statement<'a>) {
        if matches!(statement, Statement::FunctionDeclaration(_)) {
            return;
        }
        self.metrics.statement_count += 1;
        walk::walk_statement(self, statement);
    }

    fn visit_variable_declarator(&mut self, declarator: &VariableDeclarator<'a>) {
        self.metrics.local_count += 1;
        walk::walk_variable_declarator(self, declarator);
    }

    fn visit_call_expression(&mut self, call: &CallExpression<'a>) {
        self.metrics.calls.insert(call_name(self.source, call));
        walk::walk_call_expression(self, call);
    }

    fn visit_function(&mut self, _function: &Function<'a>, _flags: ScopeFlags) {}

    fn visit_arrow_function_expression(&mut self, _arrow: &ArrowFunctionExpression<'a>) {}
}

fn call_name(source: &str, call: &CallExpression<'_>) -> String {
    expression_name(source, &call.callee)
}

fn expression_name(source: &str, expression: &Expression<'_>) -> String {
    match expression {
        Expression::Identifier(identifier) => identifier.name.to_string(),
        Expression::StaticMemberExpression(member) => {
            format!(
                "{}.{}",
                expression_name(source, &member.object),
                member.property.name
            )
        }
        _ => span_text(source, expression.span()).to_owned(),
    }
}

fn is_scalar_literal(source: &str, expression: &Expression<'_>) -> bool {
    match expression {
        Expression::BooleanLiteral(_)
        | Expression::NumericLiteral(_)
        | Expression::BigIntLiteral(_)
        | Expression::StringLiteral(_)
        | Expression::TemplateLiteral(_) => true,
        Expression::UnaryExpression(unary) => {
            let operator = source.as_bytes().get(unary.span.start as usize).copied();
            matches!(operator, Some(b'+') | Some(b'-'))
                && is_scalar_literal(source, &unary.argument)
        }
        _ => false,
    }
}

fn has_generic_call_or_new(expression: &Expression<'_>) -> bool {
    match expression {
        Expression::CallExpression(call) => call.type_arguments.is_some(),
        Expression::NewExpression(call) => call.type_arguments.is_some(),
        _ => false,
    }
}
