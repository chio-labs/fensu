//! Error-discarding existence probes in runtime source.

use syn::visit::Visit;

use crate::models;

const ERROR_DISCARDING_METHODS: &[&str] = &["is_ok", "ok"];
const FALLIBLE_METHODS: &[&str] = &[
    "canonicalize",
    "execute",
    "metadata",
    "open",
    "parse",
    "prepare",
    "query_map",
    "query_row",
    "read_dir",
    "strip_prefix",
    "symlink_metadata",
];
const FALLIBLE_FUNCTIONS: &[&str] = &[
    "canonicalize",
    "from_slice",
    "from_str",
    "read",
    "read_to_string",
];
const DEFAULT_METHOD: &str = "unwrap_or_default";

#[derive(Default)]
struct DiscardedErrorVisitor {
    lines: Vec<usize>,
}

impl<'ast> Visit<'ast> for DiscardedErrorVisitor {
    fn visit_expr_method_call(&mut self, node: &'ast syn::ExprMethodCall) {
        let method = node.method.to_string();
        let discards_error = ERROR_DISCARDING_METHODS.contains(&method.as_str())
            || method == DEFAULT_METHOD && receiver_is_fallible(&node.receiver);
        if discards_error {
            self.lines.push(node.method.span().start().line);
        }
        syn::visit::visit_expr_method_call(self, node);
    }
}

pub(super) fn check(file: &models::SourceFile, syntax: &syn::File) -> Vec<models::Violation> {
    let mut visitor = DiscardedErrorVisitor::default();
    visitor.visit_file(syntax);
    visitor
        .lines
        .into_iter()
        .map(|line| {
            models::Violation::new(models::ViolationRequest {
                code: "RSH005",
                path: file.relative_path(),
                line: Some(line),
                message: "fallible result is converted into an existence probe",
                remediation: "match the expected error explicitly and preserve unexpected failures",
            })
        })
        .collect()
}

fn receiver_is_fallible(receiver: &syn::Expr) -> bool {
    match receiver {
        syn::Expr::MethodCall(call) => FALLIBLE_METHODS.contains(&call.method.to_string().as_str()),
        syn::Expr::Call(call) => {
            let syn::Expr::Path(function) = call.func.as_ref() else {
                return false;
            };
            function.path.segments.last().is_some_and(|segment| {
                FALLIBLE_FUNCTIONS.contains(&segment.ident.to_string().as_str())
            })
        }
        _ => false,
    }
}
