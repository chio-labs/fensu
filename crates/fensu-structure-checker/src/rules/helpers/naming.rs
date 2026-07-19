//! Naming contract rules mapping function prefixes to declared return types.

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
    return_type: Option<syn::Type>,
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

    fn visit_trait_item_fn(&mut self, node: &'ast syn::TraitItemFn) {
        self.functions.push(declared_function(&node.sig));
        syn::visit::visit_trait_item_fn(self, node);
    }
}

fn declared_function(signature: &syn::Signature) -> DeclaredFunction {
    let return_type = match &signature.output {
        syn::ReturnType::Default => None,
        syn::ReturnType::Type(_, inner) => Some(inner.as_ref().clone()),
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
    if bool_contract && !returns_bool(function.return_type.as_ref()) {
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
    if value_contract && !returns_value(function.return_type.as_ref()) {
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
    if no_return_contract && !unit_or_unit_result(function.return_type.as_ref()) {
        return contract_case(
            file,
            function,
            "RSN001",
            "return () or Result<(), E>, or rename a value-producing query",
        );
    }
    let iterator_contract = function.name.starts_with(constants::ITERATOR_RETURN_PREFIX);
    let returns_iterator = function.return_type.as_ref().is_some_and(iterator_type);
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

fn returns_bool(return_type: Option<&syn::Type>) -> bool {
    return_type.is_some_and(|inner| type_path_ends_with(inner, "bool"))
}

fn returns_value(return_type: Option<&syn::Type>) -> bool {
    return_type.is_some_and(|inner| !unit_type(inner))
}

fn unit_or_unit_result(return_type: Option<&syn::Type>) -> bool {
    let Some(inner) = return_type else {
        return true;
    };
    unit_type(inner) || result_success_type(inner).is_some_and(unit_type)
}

fn unit_type(value: &syn::Type) -> bool {
    matches!(value, syn::Type::Tuple(tuple) if tuple.elems.is_empty())
}

fn result_success_type(value: &syn::Type) -> Option<&syn::Type> {
    let syn::Type::Path(type_path) = value else {
        return None;
    };
    let segment = type_path.path.segments.last()?;
    if segment.ident != constants::RESULT_TYPE {
        return None;
    }
    let syn::PathArguments::AngleBracketed(arguments) = &segment.arguments else {
        return None;
    };
    arguments.args.iter().find_map(|argument| match argument {
        syn::GenericArgument::Type(inner) => Some(inner),
        _ => None,
    })
}

fn iterator_type(value: &syn::Type) -> bool {
    match value {
        syn::Type::ImplTrait(inner) => inner.bounds.iter().any(iterator_bound),
        syn::Type::TraitObject(inner) => inner.bounds.iter().any(iterator_bound),
        syn::Type::Path(inner) => inner.path.segments.last().is_some_and(|segment| {
            constants::ITERATOR_TYPE_NAMES.contains(&segment.ident.to_string().as_str())
        }),
        _ => false,
    }
}

fn iterator_bound(bound: &syn::TypeParamBound) -> bool {
    let syn::TypeParamBound::Trait(inner) = bound else {
        return false;
    };
    inner
        .path
        .segments
        .last()
        .is_some_and(|segment| segment.ident == constants::ITERATOR_TYPE)
}

fn type_path_ends_with(value: &syn::Type, expected: &str) -> bool {
    let syn::Type::Path(inner) = value else {
        return false;
    };
    inner
        .path
        .segments
        .last()
        .is_some_and(|segment| segment.ident == expected)
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
