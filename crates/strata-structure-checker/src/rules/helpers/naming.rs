//! Naming contract rules mapping function prefixes to declared return types.

use quote::ToTokens;
use syn::visit::Visit;

use crate::constants;
use crate::models;

pub(crate) fn check(file: &models::SourceFile, syntax: &syn::File) -> Vec<models::Violation> {
    let mut visitor = FunctionVisitor {
        functions: Vec::new(),
    };
    visitor.visit_file(syntax);
    let mut violations: Vec<models::Violation> = Vec::new();
    for function in &visitor.functions {
        violations.extend(contract_violation(file, function));
    }
    violations
}

struct DeclaredFunction {
    name: String,
    return_type: Option<String>,
    line: usize,
}

struct FunctionVisitor {
    functions: Vec<DeclaredFunction>,
}

impl<'ast> Visit<'ast> for FunctionVisitor {
    fn visit_item_fn(&mut self, node: &'ast syn::ItemFn) {
        self.functions.push(declared_function(&node.sig));
        syn::visit::visit_item_fn(self, node);
    }

    fn visit_impl_item_fn(&mut self, node: &'ast syn::ImplItemFn) {
        self.functions.push(declared_function(&node.sig));
        syn::visit::visit_impl_item_fn(self, node);
    }
}

fn declared_function(signature: &syn::Signature) -> DeclaredFunction {
    let return_type = match &signature.output {
        syn::ReturnType::Default => None,
        syn::ReturnType::Type(_, inner) => Some(inner.to_token_stream().to_string()),
    };
    DeclaredFunction {
        name: signature.ident.to_string(),
        return_type,
        line: signature.ident.span().start().line,
    }
}

fn contract_violation(
    file: &models::SourceFile,
    function: &DeclaredFunction,
) -> Vec<models::Violation> {
    if function
        .name
        .starts_with(constants::DISCOURAGED_GETTER_PREFIX)
    {
        return contract_case(
            file,
            function,
            "RSN003",
            "drop the get_ prefix and name the returned value, per Rust API guidelines",
        );
    }
    let bool_contract = constants::BOOL_RETURN_PREFIXES
        .iter()
        .any(|prefix| function.name.starts_with(prefix));
    if bool_contract && function.return_type.as_deref() != Some("bool") {
        return contract_case(
            file,
            function,
            "RSN002",
            "return bool, or rename the function after the value it produces",
        );
    }
    let value_contract = constants::VALUE_RETURN_PREFIXES
        .iter()
        .any(|prefix| function.name.starts_with(prefix));
    if value_contract && function.return_type.is_none() {
        return contract_case(
            file,
            function,
            "RSN003",
            "return the converted value, or rename the function after its effect",
        );
    }
    let no_return_contract = constants::NO_RETURN_PREFIXES
        .iter()
        .any(|prefix| function.name.starts_with(prefix));
    if no_return_contract && !unit_or_unit_result(function.return_type.as_deref()) {
        return contract_case(
            file,
            function,
            "RSN001",
            "return () or Result<(), E>, or rename a value-producing query",
        );
    }
    let iterator_contract = function.name.starts_with(constants::ITERATOR_RETURN_PREFIX);
    let returns_iterator = function
        .return_type
        .as_deref()
        .is_some_and(|inner| inner.contains("Iter"));
    if iterator_contract && !returns_iterator {
        return contract_case(
            file,
            function,
            "RSN004",
            "return an iterator, or rename an eager collection function",
        );
    }
    Vec::new()
}

fn unit_or_unit_result(return_type: Option<&str>) -> bool {
    let Some(inner) = return_type else {
        return true;
    };
    inner.starts_with("Result") && inner.contains("()")
}

fn contract_case(
    file: &models::SourceFile,
    function: &DeclaredFunction,
    code: &'static str,
    remediation: &'static str,
) -> Vec<models::Violation> {
    vec![models::Violation::new(
        code,
        file.relative_path(),
        Some(function.line),
        format!("{} violates its naming contract", function.name),
        remediation,
    )]
}
