//! Rust-specific parameter, outer-state, and closure-complexity policy.

use std::collections::BTreeSet;

use quote::ToTokens;
use syn::spanned::Spanned;
use syn::visit::Visit;

use crate::constants;
use crate::models;

const MUTATING_INTERIOR_METHODS: &[&str] = &[
    "append",
    "borrow_mut",
    "clear",
    "drain",
    "entry",
    "extend",
    "fetch_add",
    "fetch_and",
    "fetch_max",
    "fetch_min",
    "fetch_nand",
    "fetch_or",
    "fetch_sub",
    "fetch_update",
    "fetch_xor",
    "get_mut",
    "insert",
    "lock",
    "pop",
    "push",
    "push_str",
    "remove",
    "reserve",
    "replace",
    "retain",
    "set",
    "sort",
    "sort_by",
    "sort_by_key",
    "sort_unstable",
    "store",
    "swap",
    "take",
    "write",
];

const ITERATOR_CLOSURE_METHODS: &[&str] = &[
    "all",
    "any",
    "filter",
    "filter_map",
    "find",
    "find_map",
    "flat_map",
    "fold",
    "for_each",
    "inspect",
    "map",
    "map_while",
    "partition",
    "position",
    "rfind",
    "scan",
    "skip_while",
    "take_while",
    "try_fold",
    "try_for_each",
];
const TOOLING_CRATE_SOURCE_PREFIX: &str = "crates/fensu-structure-checker/src/";

pub(crate) fn check(file: &models::SourceFile, syntax: &syn::File) -> Vec<models::Violation> {
    let statics = syntax
        .items
        .iter()
        .filter_map(|item| match item {
            syn::Item::Static(item_static) => Some(item_static.ident.to_string()),
            _ => None,
        })
        .collect::<BTreeSet<_>>();
    let mut visitor = PolicyVisitor {
        file,
        statics: &statics,
        violations: Vec::new(),
    };
    visitor.visit_file(syntax);
    visitor
        .violations
        .sort_by(|left, right| left.sort_key().cmp(&right.sort_key()));
    visitor
        .violations
        .dedup_by(|left, right| left.sort_key() == right.sort_key());
    visitor.violations
}

struct PolicyVisitor<'a> {
    file: &'a models::SourceFile,
    statics: &'a BTreeSet<String>,
    violations: Vec<models::Violation>,
}

struct PolicyViolationRequest<'a> {
    file: &'a models::SourceFile,
    line: usize,
    code: &'static str,
    message: &'static str,
    remediation: &'static str,
}

impl PolicyVisitor<'_> {
    fn check_function(&mut self, signature: &syn::Signature, block: &syn::Block) {
        let mutable_parameters = signature
            .inputs
            .iter()
            .filter_map(mutable_reference_parameter)
            .collect::<BTreeSet<_>>();
        let mutated_parameters = mutated_parameters(block, &mutable_parameters);
        let mutable_references = mutated_parameters.len();
        if mutable_references > 0 && self.file.has_directory(constants::HELPERS_DIRECTORY) {
            self.violations
                .push(policy_violation(PolicyViolationRequest {
                    file: self.file,
                    line: signature.ident.span().start().line,
                    code: "RSS102",
                    message: "helper function accepts mutable-reference parameters",
                    remediation: "return a new or updated value so helper dataflow remains visible",
                }));
        }
        if mutable_references > mutable_reference_return_count(signature) {
            self.violations
                .push(policy_violation(PolicyViolationRequest {
                    file: self.file,
                    line: signature.ident.span().start().line,
                    code: "RSS110",
                    message: "mutable-reference parameters are not all returned",
                    remediation:
                        "return every mutable reference or avoid mutating through parameters",
                }));
        }
        let parameters = signature
            .inputs
            .iter()
            .filter(|input| matches!(input, syn::FnArg::Typed(_)))
            .count();
        if parameters > constants::MAX_POSITIONAL_PARAMETERS {
            self.violations
                .push(models::Violation::new(models::ViolationRequest {
                    code: "RSS120",
                    path: self.file.relative_path(),
                    line: Some(signature.ident.span().start().line),
                    message: format!("function uses {parameters} positional parameters"),
                    remediation: "group cohesive inputs into one named parameter struct",
                }));
        }
        let mut body = BodyPolicyVisitor {
            file: self.file,
            statics: self.statics,
            iterator_closure_depth: 0,
            violations: &mut self.violations,
        };
        body.visit_block(block);
    }
}

impl<'ast> Visit<'ast> for PolicyVisitor<'_> {
    fn visit_item_fn(&mut self, node: &'ast syn::ItemFn) {
        self.check_function(&node.sig, &node.block);
    }

    fn visit_impl_item_fn(&mut self, node: &'ast syn::ImplItemFn) {
        self.check_function(&node.sig, &node.block);
    }
}

struct BodyPolicyVisitor<'a, 'b> {
    file: &'a models::SourceFile,
    statics: &'a BTreeSet<String>,
    iterator_closure_depth: usize,
    violations: &'b mut Vec<models::Violation>,
}

impl<'ast> Visit<'ast> for BodyPolicyVisitor<'_, '_> {
    fn visit_item_fn(&mut self, _node: &'ast syn::ItemFn) {}

    fn visit_expr_assign(&mut self, node: &'ast syn::ExprAssign) {
        if expression_root(&node.left).is_some_and(|root| self.statics.contains(&root)) {
            self.violations
                .push(policy_violation(PolicyViolationRequest {
                    file: self.file,
                    line: node.span().start().line,
                    code: "RSS130",
                    message: "function assigns to static state",
                    remediation: "pass state explicitly and return the updated value",
                }));
        }
        syn::visit::visit_expr_assign(self, node);
    }

    fn visit_expr_method_call(&mut self, node: &'ast syn::ExprMethodCall) {
        let method = node.method.to_string();
        if MUTATING_INTERIOR_METHODS.contains(&method.as_str())
            && expression_root(&node.receiver).is_some_and(|root| self.statics.contains(&root))
        {
            self.violations
                .push(policy_violation(PolicyViolationRequest {
                    file: self.file,
                    line: node.span().start().line,
                    code: "RSS130",
                    message: "function mutates static interior state",
                    remediation: "pass state explicitly and return the updated value",
                }));
        }
        if ITERATOR_CLOSURE_METHODS.contains(&method.as_str()) {
            self.visit_expr(&node.receiver);
            for argument in &node.args {
                if let syn::Expr::Closure(closure) = argument {
                    self.visit_iterator_closure(closure);
                } else {
                    self.visit_expr(argument);
                }
            }
        } else {
            syn::visit::visit_expr_method_call(self, node);
        }
    }

    fn visit_expr_closure(&mut self, node: &'ast syn::ExprClosure) {
        self.visit_expr(&node.body);
    }
}

impl BodyPolicyVisitor<'_, '_> {
    fn visit_iterator_closure(&mut self, closure: &syn::ExprClosure) {
        if self.iterator_closure_depth > 0 {
            let code = if self.file.relative.starts_with(TOOLING_CRATE_SOURCE_PREFIX) {
                "RSH006"
            } else {
                "RSS131"
            };
            self.violations
                .push(policy_violation(PolicyViolationRequest {
                    file: self.file,
                    line: closure.span().start().line,
                    code,
                    message: "nested iterator closure hides control flow",
                    remediation: "extract the nested iterator transformation into a named function",
                }));
        }
        self.iterator_closure_depth += 1;
        self.visit_expr(&closure.body);
        self.iterator_closure_depth -= 1;
    }
}

fn mutable_reference_parameter(input: &syn::FnArg) -> Option<String> {
    let syn::FnArg::Typed(parameter) = input else {
        return None;
    };
    let mutable = matches!(parameter.ty.as_ref(), syn::Type::Reference(reference) if reference.mutability.is_some());
    let syn::Pat::Ident(identifier) = parameter.pat.as_ref() else {
        return None;
    };
    mutable.then(|| identifier.ident.to_string())
}

fn mutated_parameters(block: &syn::Block, parameters: &BTreeSet<String>) -> BTreeSet<String> {
    let mut visitor = ParameterMutationVisitor {
        parameters,
        mutated: BTreeSet::new(),
    };
    visitor.visit_block(block);
    visitor.mutated
}

struct ParameterMutationVisitor<'a> {
    parameters: &'a BTreeSet<String>,
    mutated: BTreeSet<String>,
}

impl Visit<'_> for ParameterMutationVisitor<'_> {
    fn visit_item_fn(&mut self, _node: &syn::ItemFn) {}

    fn visit_expr_assign(&mut self, node: &syn::ExprAssign) {
        self.record_root(&node.left);
        syn::visit::visit_expr_assign(self, node);
    }

    fn visit_expr_binary(&mut self, node: &syn::ExprBinary) {
        if matches!(
            node.op,
            syn::BinOp::AddAssign(_)
                | syn::BinOp::SubAssign(_)
                | syn::BinOp::MulAssign(_)
                | syn::BinOp::DivAssign(_)
                | syn::BinOp::RemAssign(_)
                | syn::BinOp::BitXorAssign(_)
                | syn::BinOp::BitAndAssign(_)
                | syn::BinOp::BitOrAssign(_)
                | syn::BinOp::ShlAssign(_)
                | syn::BinOp::ShrAssign(_)
        ) {
            self.record_root(&node.left);
        }
        syn::visit::visit_expr_binary(self, node);
    }

    fn visit_expr_call(&mut self, node: &syn::ExprCall) {
        for argument in &node.args {
            self.record_root(argument);
        }
        syn::visit::visit_expr_call(self, node);
    }

    fn visit_expr_method_call(&mut self, node: &syn::ExprMethodCall) {
        if MUTATING_INTERIOR_METHODS.contains(&node.method.to_string().as_str()) {
            self.record_root(&node.receiver);
        }
        syn::visit::visit_expr_method_call(self, node);
    }
}

impl ParameterMutationVisitor<'_> {
    fn record_root(&mut self, expression: &syn::Expr) {
        let Some(root) = expression_root(expression) else {
            return;
        };
        if self.parameters.contains(&root) {
            self.mutated.insert(root);
        }
    }
}

fn mutable_reference_return_count(signature: &syn::Signature) -> usize {
    let syn::ReturnType::Type(_, output) = &signature.output else {
        return 0;
    };
    output
        .to_token_stream()
        .to_string()
        .match_indices("& mut")
        .count()
}

fn expression_root(expression: &syn::Expr) -> Option<String> {
    match expression {
        syn::Expr::Path(path) => path
            .path
            .segments
            .first()
            .map(|segment| segment.ident.to_string()),
        syn::Expr::Field(field) => expression_root(&field.base),
        syn::Expr::Index(index) => expression_root(&index.expr),
        syn::Expr::Paren(paren) => expression_root(&paren.expr),
        syn::Expr::Reference(reference) => expression_root(&reference.expr),
        syn::Expr::Unary(unary) => expression_root(&unary.expr),
        _ => None,
    }
}

fn policy_violation(request: PolicyViolationRequest<'_>) -> models::Violation {
    models::Violation::new(models::ViolationRequest {
        code: request.code,
        path: request.file.relative_path(),
        line: Some(request.line),
        message: request.message,
        remediation: request.remediation,
    })
}
