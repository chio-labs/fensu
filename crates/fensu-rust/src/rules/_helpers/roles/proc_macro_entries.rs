//! Thin proc-macro entries that Rust requires in a proc-macro crate root.

use syn::parse::Parser;
use syn::visit::Visit;

use crate::constants;
use crate::models;

/// Return the function when the item is a thin, directly attributed proc-macro entry.
pub(crate) fn thin_entry(item: &syn::Item) -> Option<&syn::ItemFn> {
    let syn::Item::Fn(function) = item else {
        return None;
    };
    (has_one_entry_attribute(&function.attrs)
        && has_plain_signature(&function.sig)
        && forwards_thinly(function))
    .then_some(function)
}

/// Count the source lines an entry occupies, including its attributes and doc comments.
pub(crate) fn entry_line_count(function: &syn::ItemFn) -> usize {
    let start = function
        .attrs
        .iter()
        .map(|attribute| attribute.pound_token.span.start().line)
        .chain([function.sig.fn_token.span.start().line])
        .min()
        .unwrap_or_default();
    let end = function.block.brace_token.span.close().end().line;
    end.saturating_sub(start) + 1
}

/// Cap the number of thin entries one proc-macro root may define.
pub(crate) fn check_entry_cap(
    file: &models::SourceFile,
    entries: &[&syn::ItemFn],
    thresholds: &models::ThresholdConfig,
) -> Vec<models::Violation> {
    let limit = thresholds.max_main_container_modules;
    let Some(first_extra) = entries.get(limit) else {
        return Vec::new();
    };
    vec![models::Violation::new(models::ViolationRequest {
        code: "RSR406",
        path: file.relative_path(),
        line: Some(first_extra.sig.ident.span().start().line),
        message: format!(
            "proc-macro crate root defines {} macro entries; the limit is {limit}",
            entries.len()
        ),
        remediation: "split the macros into separate proc-macro crates by family",
    })]
}

fn has_one_entry_attribute(attributes: &[syn::Attribute]) -> bool {
    let entry_attributes = attributes
        .iter()
        .filter(|attribute| is_entry_attribute(attribute))
        .count();
    entry_attributes == 1 && attributes.iter().all(is_permitted_attribute)
}

fn is_entry_attribute(attribute: &syn::Attribute) -> bool {
    constants::PROC_MACRO_ATTRIBUTES
        .iter()
        .any(|name| attribute.path().is_ident(name))
}

fn is_permitted_attribute(attribute: &syn::Attribute) -> bool {
    matches!(attribute.style, syn::AttrStyle::Outer)
        && (is_entry_attribute(attribute) || is_companion_attribute(attribute))
}

fn is_companion_attribute(attribute: &syn::Attribute) -> bool {
    constants::PROC_MACRO_COMPANION_ATTRIBUTES
        .iter()
        .any(|name| attribute.path().is_ident(name))
}

fn has_plain_signature(signature: &syn::Signature) -> bool {
    let plain_output = match &signature.output {
        syn::ReturnType::Default => true,
        syn::ReturnType::Type(_, value) => is_plain_type(value),
    };
    signature.constness.is_none()
        && signature.asyncness.is_none()
        && signature.unsafety.is_none()
        && signature.abi.is_none()
        && signature.variadic.is_none()
        && signature.generics.params.is_empty()
        && signature.generics.where_clause.is_none()
        && signature.inputs.iter().all(is_plain_parameter)
        && plain_output
}

fn is_plain_parameter(input: &syn::FnArg) -> bool {
    match input {
        syn::FnArg::Typed(typed) => {
            typed.attrs.is_empty()
                && pattern_ident(&typed.pat).is_some()
                && is_plain_type(&typed.ty)
        }
        syn::FnArg::Receiver(_) => false,
    }
}

fn forwards_thinly(function: &syn::ItemFn) -> bool {
    let mut locals: Vec<&syn::Ident> = function
        .sig
        .inputs
        .iter()
        .filter_map(|input| match input {
            syn::FnArg::Typed(typed) => pattern_ident(&typed.pat),
            syn::FnArg::Receiver(_) => None,
        })
        .collect();
    match function.block.stmts.as_slice() {
        [syn::Stmt::Expr(tail, None)] => forwarding_call(tail, &locals),
        [syn::Stmt::Local(local), syn::Stmt::Expr(tail, None)] => {
            let Some(bound) = parse_binding(local, &locals) else {
                return false;
            };
            locals.push(bound);
            forwarding_call(tail, &locals)
        }
        _ => false,
    }
}

fn pattern_ident(pattern: &syn::Pat) -> Option<&syn::Ident> {
    match pattern {
        syn::Pat::Ident(binding)
            if binding.attrs.is_empty() && binding.by_ref.is_none() && binding.subpat.is_none() =>
        {
            Some(&binding.ident)
        }
        _ => None,
    }
}

fn parse_binding<'a>(local: &'a syn::Local, parameters: &[&syn::Ident]) -> Option<&'a syn::Ident> {
    if !local.attrs.is_empty() {
        return None;
    }
    let bound = match &local.pat {
        syn::Pat::Type(typed) if typed.attrs.is_empty() && is_plain_type(&typed.ty) => {
            pattern_ident(&typed.pat)
        }
        pattern => pattern_ident(pattern),
    }?;
    let init = local.init.as_ref()?;
    (init.diverge.is_none() && is_parse_step(&init.expr, parameters)).then_some(bound)
}

fn is_parse_step(expr: &syn::Expr, parameters: &[&syn::Ident]) -> bool {
    match expr {
        syn::Expr::Macro(invocation) => {
            invocation.attrs.is_empty() && is_parse_macro(&invocation.mac, parameters)
        }
        syn::Expr::Try(attempt) => {
            attempt.attrs.is_empty() && is_parse_call(&attempt.expr, parameters)
        }
        syn::Expr::MethodCall(call) => {
            (is_bare_method(call, constants::PROC_MACRO_UNWRAP_METHOD)
                || is_compile_error_fallback(call))
                && is_parse_call(&call.receiver, parameters)
        }
        _ => false,
    }
}

fn is_parse_macro(mac: &syn::Macro, parameters: &[&syn::Ident]) -> bool {
    let segments = path_idents(&mac.path);
    let expected = constants::PROC_MACRO_PARSE_MACRO_PATH;
    let named = !segments.is_empty()
        && segments.len() <= expected.len()
        && expected
            .iter()
            .rev()
            .zip(segments.iter().rev())
            .all(|(name, segment)| segment == name);
    if !named || !plain_path_arguments(&mac.path) {
        return false;
    }
    let parser = |input: syn::parse::ParseStream<'_>| {
        let source: syn::Ident = input.parse()?;
        input.parse::<syn::Token![as]>()?;
        let target: syn::Type = input.parse()?;
        Ok((source, target))
    };
    parser
        .parse2(mac.tokens.clone())
        .is_ok_and(|(source, target)| parameters.contains(&&source) && is_plain_type(&target))
}

fn is_parse_call(expr: &syn::Expr, parameters: &[&syn::Ident]) -> bool {
    let syn::Expr::Call(call) = expr else {
        return false;
    };
    let syn::Expr::Path(function) = call.func.as_ref() else {
        return false;
    };
    call.attrs.is_empty()
        && function.attrs.is_empty()
        && function.qself.is_none()
        && path_idents(&function.path) == constants::PROC_MACRO_PARSE_PATH
        && plain_path_arguments(&function.path)
        && call.args.len() == 1
        && call.args.first().is_some_and(|argument| {
            local_name(argument).is_some_and(|name| parameters.contains(&name))
        })
}

fn forwarding_call(expr: &syn::Expr, locals: &[&syn::Ident]) -> bool {
    let mut current = expr;
    let mut converted = false;
    let mut recovered = false;
    loop {
        match current {
            syn::Expr::MethodCall(call)
                if !converted && is_bare_method(call, constants::PROC_MACRO_INTO_METHOD) =>
            {
                converted = true;
                current = &call.receiver;
            }
            syn::Expr::MethodCall(call) if !recovered && is_compile_error_fallback(call) => {
                recovered = true;
                current = &call.receiver;
            }
            syn::Expr::Call(call) => return is_direct_call(call, locals),
            _ => return false,
        }
    }
}

fn is_direct_call(call: &syn::ExprCall, locals: &[&syn::Ident]) -> bool {
    let syn::Expr::Path(function) = call.func.as_ref() else {
        return false;
    };
    call.attrs.is_empty()
        && function.attrs.is_empty()
        && function.qself.is_none()
        && plain_path_arguments(&function.path)
        && call
            .args
            .iter()
            .all(|argument| is_local_argument(argument, locals))
}

fn is_local_argument(argument: &syn::Expr, locals: &[&syn::Ident]) -> bool {
    let value = match argument {
        syn::Expr::Reference(borrow) if borrow.attrs.is_empty() => borrow.expr.as_ref(),
        other => other,
    };
    local_name(value).is_some_and(|name| locals.contains(&name))
}

fn local_name(expr: &syn::Expr) -> Option<&syn::Ident> {
    match expr {
        syn::Expr::Path(path) if path.attrs.is_empty() && path.qself.is_none() => {
            path.path.get_ident()
        }
        _ => None,
    }
}

fn is_bare_method(call: &syn::ExprMethodCall, name: &str) -> bool {
    call.attrs.is_empty() && call.turbofish.is_none() && call.args.is_empty() && call.method == name
}

fn is_compile_error_fallback(call: &syn::ExprMethodCall) -> bool {
    let [syn::Expr::Path(handler)] = call.args.iter().collect::<Vec<_>>().as_slice() else {
        return false;
    };
    let segments = path_idents(&handler.path);
    call.attrs.is_empty()
        && call.turbofish.is_none()
        && call.method == constants::PROC_MACRO_FALLBACK_METHOD
        && handler.attrs.is_empty()
        && handler.qself.is_none()
        && handler
            .path
            .segments
            .iter()
            .all(|segment| segment.arguments.is_none())
        && segments.split_last().is_some_and(|(function, owner)| {
            owner == constants::PROC_MACRO_ERROR_PATH
                && constants::PROC_MACRO_COMPILE_ERROR_FUNCTIONS.contains(&function.as_str())
        })
}

fn path_idents(path: &syn::Path) -> Vec<String> {
    path.segments
        .iter()
        .map(|segment| segment.ident.to_string())
        .collect()
}

fn plain_path_arguments(path: &syn::Path) -> bool {
    path.segments
        .iter()
        .all(|segment| match &segment.arguments {
            syn::PathArguments::None => true,
            syn::PathArguments::AngleBracketed(arguments) => {
                arguments.args.iter().all(is_plain_generic_argument)
            }
            syn::PathArguments::Parenthesized(_) => false,
        })
}

fn is_plain_generic_argument(argument: &syn::GenericArgument) -> bool {
    match argument {
        syn::GenericArgument::Type(value) => is_plain_type(value),
        syn::GenericArgument::Lifetime(_) => true,
        _ => false,
    }
}

fn is_plain_type(value: &syn::Type) -> bool {
    let mut visitor = PlainTypeVisitor { plain: true };
    visitor.visit_type(value);
    visitor.plain
}

struct PlainTypeVisitor {
    plain: bool,
}

impl<'ast> Visit<'ast> for PlainTypeVisitor {
    fn visit_type(&mut self, node: &'ast syn::Type) {
        if matches!(node, syn::Type::Verbatim(_)) {
            self.plain = false;
        } else {
            syn::visit::visit_type(self, node);
        }
    }

    fn visit_expr(&mut self, node: &'ast syn::Expr) {
        if matches!(node, syn::Expr::Lit(_) | syn::Expr::Path(_)) {
            syn::visit::visit_expr(self, node);
        } else {
            self.plain = false;
        }
    }

    fn visit_macro(&mut self, _node: &'ast syn::Macro) {
        self.plain = false;
    }
}
