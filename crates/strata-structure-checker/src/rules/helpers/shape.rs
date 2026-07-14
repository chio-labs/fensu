//! Shape rules: argument, statement, callee, local, and global-state budgets.

use std::collections::BTreeSet;

use quote::ToTokens;
use syn::visit::Visit;

use crate::constants;
use crate::models;
use crate::types::FileKind;

pub(crate) fn check(
    file: &models::SourceFile,
    syntax: &syn::File,
    kind: FileKind,
) -> Vec<models::Violation> {
    let mut visitor = ShapeVisitor {
        functions: Vec::new(),
        statics: Vec::new(),
    };
    visitor.visit_file(syntax);
    let mut violations: Vec<models::Violation> = Vec::new();
    for line in &visitor.statics {
        violations.push(models::Violation::new(
            "RSS130",
            file.relative_path(),
            Some(*line),
            "static item holds outer state",
            "pass state explicitly through parameters and return values",
        ));
    }
    let entry = kind == FileKind::ModuleFile && file.has_directory(constants::MAIN_DIRECTORY);
    for function in &visitor.functions {
        violations.extend(budget_violations(file, function, entry));
    }
    violations
}

struct FunctionShape {
    arguments: usize,
    statements: usize,
    locals: usize,
    distinct_calls: usize,
    line: usize,
}

struct ShapeVisitor {
    functions: Vec<FunctionShape>,
    statics: Vec<usize>,
}

impl<'ast> Visit<'ast> for ShapeVisitor {
    fn visit_item_fn(&mut self, node: &'ast syn::ItemFn) {
        self.functions.push(function_shape(&node.sig, &node.block));
        syn::visit::visit_item_fn(self, node);
    }

    fn visit_impl_item_fn(&mut self, node: &'ast syn::ImplItemFn) {
        self.functions.push(function_shape(&node.sig, &node.block));
        syn::visit::visit_impl_item_fn(self, node);
    }

    fn visit_item_static(&mut self, node: &'ast syn::ItemStatic) {
        self.statics.push(node.ident.span().start().line);
        syn::visit::visit_item_static(self, node);
    }
}

struct BodyCounter {
    statements: usize,
    locals: usize,
    calls: BTreeSet<String>,
}

impl<'ast> Visit<'ast> for BodyCounter {
    fn visit_stmt(&mut self, node: &'ast syn::Stmt) {
        self.statements += 1;
        syn::visit::visit_stmt(self, node);
    }

    fn visit_local(&mut self, node: &'ast syn::Local) {
        self.locals += 1;
        syn::visit::visit_local(self, node);
    }

    fn visit_expr_call(&mut self, node: &'ast syn::ExprCall) {
        self.calls.insert(node.func.to_token_stream().to_string());
        syn::visit::visit_expr_call(self, node);
    }

    fn visit_expr_method_call(&mut self, node: &'ast syn::ExprMethodCall) {
        self.calls.insert(node.method.to_string());
        syn::visit::visit_expr_method_call(self, node);
    }
}

fn function_shape(signature: &syn::Signature, block: &syn::Block) -> FunctionShape {
    let mut counter = BodyCounter {
        statements: 0,
        locals: 0,
        calls: BTreeSet::new(),
    };
    counter.visit_block(block);
    let arguments = signature
        .inputs
        .iter()
        .filter(|input| matches!(input, syn::FnArg::Typed(_)))
        .count();
    FunctionShape {
        arguments,
        statements: counter.statements,
        locals: counter.locals,
        distinct_calls: counter.calls.len(),
        line: signature.ident.span().start().line,
    }
}

fn budget_violations(
    file: &models::SourceFile,
    function: &FunctionShape,
    entry: bool,
) -> Vec<models::Violation> {
    let mut violations: Vec<models::Violation> = Vec::new();
    if function.arguments > constants::MAX_ARGUMENTS {
        violations.push(budget_violation(
            file,
            function,
            "RSS010",
            "declares too many parameters",
            "group cohesive inputs into a typed model",
        ));
    }
    if function.statements > constants::MAX_STATEMENTS_GLOBAL {
        violations.push(budget_violation(
            file,
            function,
            "RSS011",
            "exceeds the global statement budget",
            "split the function at a meaningful phase boundary",
        ));
    }
    if !entry {
        return violations;
    }
    if function.statements > constants::MAX_STATEMENTS_ENTRY {
        violations.push(budget_violation(
            file,
            function,
            "RSS001",
            "exceeds the entry statement budget",
            "extract cohesive phases into helpers returning explicit results",
        ));
    }
    if function.distinct_calls > constants::MAX_DISTINCT_CALLS_ENTRY {
        violations.push(budget_violation(
            file,
            function,
            "RSS002",
            "coordinates too many distinct callees",
            "group related work into named phase helpers",
        ));
    }
    if function.locals > constants::MAX_LOCALS_ENTRY {
        violations.push(budget_violation(
            file,
            function,
            "RSS003",
            "juggles too many local variables",
            "let each extracted phase own its intermediates",
        ));
    }
    violations
}

fn budget_violation(
    file: &models::SourceFile,
    function: &FunctionShape,
    code: &'static str,
    detail: &str,
    remediation: &'static str,
) -> models::Violation {
    models::Violation::new(
        code,
        file.relative_path(),
        Some(function.line),
        format!("function {detail}"),
        remediation,
    )
}
