//! Explicit type requirements for unresolved generic local bindings.

use syn::visit::Visit;

use crate::models;

const GENERIC_METHODS: &[&str] = &["collect", "parse"];
const GENERIC_FUNCTIONS: &[&str] = &[
    "channel",
    "default",
    "from_reader",
    "from_slice",
    "from_str",
    "from_value",
];
const GENERIC_COLLECTIONS: &[&str] = &[
    "BTreeMap",
    "BTreeSet",
    "BinaryHeap",
    "HashMap",
    "HashSet",
    "LinkedList",
    "Vec",
    "VecDeque",
];
const GENERIC_DESERIALIZERS: &[&str] = &["serde_json", "serde_yaml", "toml"];
const GENERIC_CHANNEL_OWNERS: &[&str] = &["mpsc", "oneshot"];
const CHANNEL_FUNCTION: &str = "channel";
const DEFAULT_FUNCTION: &str = "default";
const DEFAULT_TRAIT: &str = "Default";
const NEW_FUNCTION: &str = "new";

struct BindingVisitor<'a> {
    file: &'a models::SourceFile,
    violations: Vec<models::Violation>,
}

impl<'ast> Visit<'ast> for BindingVisitor<'_> {
    fn visit_local(&mut self, node: &'ast syn::Local) {
        let syn::Pat::Ident(binding) = &node.pat else {
            syn::visit::visit_local(self, node);
            return;
        };
        let Some(initializer) = &node.init else {
            syn::visit::visit_local(self, node);
            return;
        };
        if requires_type(&initializer.expr) {
            self.violations
                .push(models::Violation::new(models::ViolationRequest {
                    code: "RSA103",
                    path: self.file.relative_path(),
                    line: Some(binding.ident.span().start().line),
                    message: format!(
                        "generic local binding `{}` has no explicit type",
                        binding.ident
                    ),
                    remediation: "add an explicit type to the let binding",
                }));
        }
        syn::visit::visit_local(self, node);
    }
}

pub(super) fn check(file: &models::SourceFile, syntax: &syn::File) -> Vec<models::Violation> {
    let mut visitor = BindingVisitor {
        file,
        violations: Vec::new(),
    };
    visitor.visit_file(syntax);
    visitor.violations
}

fn requires_type(expression: &syn::Expr) -> bool {
    match expression {
        syn::Expr::Await(value) => requires_type(&value.base),
        syn::Expr::Group(value) => requires_type(&value.expr),
        syn::Expr::Paren(value) => requires_type(&value.expr),
        syn::Expr::Try(value) => requires_type(&value.expr),
        syn::Expr::MethodCall(call) => {
            GENERIC_METHODS.contains(&call.method.to_string().as_str()) && call.turbofish.is_none()
        }
        syn::Expr::Call(call) => call_requires_type(call),
        _ => false,
    }
}

fn call_requires_type(call: &syn::ExprCall) -> bool {
    let syn::Expr::Path(function) = call.func.as_ref() else {
        return false;
    };
    let Some(last) = function.path.segments.last() else {
        return false;
    };
    if !matches!(last.arguments, syn::PathArguments::None) {
        return false;
    }
    let function_name = last.ident.to_string();
    let owners = function
        .path
        .segments
        .iter()
        .take(function.path.segments.len().saturating_sub(1))
        .map(|segment| segment.ident.to_string())
        .collect::<Vec<_>>();
    if function_name == DEFAULT_FUNCTION {
        return owners.last().is_some_and(|owner| owner == DEFAULT_TRAIT);
    }
    if function_name == CHANNEL_FUNCTION {
        return owners
            .iter()
            .any(|owner| GENERIC_CHANNEL_OWNERS.contains(&owner.as_str()));
    }
    if GENERIC_FUNCTIONS.contains(&function_name.as_str())
        && owners
            .iter()
            .any(|owner| GENERIC_DESERIALIZERS.contains(&owner.as_str()))
    {
        return true;
    }
    if function_name != NEW_FUNCTION {
        return false;
    }
    function.path.segments.iter().any(|segment| {
        GENERIC_COLLECTIONS.contains(&segment.ident.to_string().as_str())
            && matches!(segment.arguments, syn::PathArguments::None)
    })
}
