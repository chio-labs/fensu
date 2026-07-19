//! Hygiene rules: comments, doc length, panics, asserts, unwraps, stdio, unsafe.

use syn::spanned::Spanned;
use syn::visit::Visit;

use crate::constants;
use crate::models;
use crate::types::FileKind;

/// Check one library source file for hygiene violations.
pub(crate) fn check_source(
    file: &models::SourceFile,
    syntax: Option<&syn::File>,
    kind: FileKind,
) -> Vec<models::Violation> {
    let mut violations = check_doc_comment_length(file);
    violations.extend(check_comment_lines(file));
    let Some(syntax) = syntax else {
        return violations;
    };
    if kind == FileKind::LibraryRoot && !forbids_unsafe_code(syntax) {
        violations.push(models::Violation::new(
            "RSH012",
            file.relative_path(),
            Some(1),
            "crate root does not forbid unsafe code",
            "add #![forbid(unsafe_code)] to lib.rs",
        ));
    }
    let invocations = collect_invocations(syntax);
    for line in &invocations.suppressions {
        violations.push(models::Violation::new(
            "RSH013",
            file.relative_path(),
            Some(*line),
            "inline lint suppression weakens workspace policy",
            "remove the attribute and fix the underlying fault",
        ));
    }
    for (name, line) in &invocations.macros {
        violations.extend(macro_violation(file, name, *line, kind));
    }
    for (name, line) in &invocations.method_calls {
        if constants::PANIC_EXTRACTION_METHODS.contains(&name.as_str()) {
            violations.push(models::Violation::new(
                "RSH010",
                file.relative_path(),
                Some(*line),
                format!("library code calls {name}()"),
                "propagate with ? or handle the failure and return a crate error",
            ));
        }
    }
    violations.extend(check_comparisons(file, syntax));
    violations
}

/// Check one test file for the hygiene rules that apply to tests.
pub(crate) fn check_test_file(
    file: &models::SourceFile,
    syntax: Option<&syn::File>,
) -> Vec<models::Violation> {
    let mut violations = check_doc_comment_length(file);
    let Some(syntax) = syntax else {
        return violations;
    };
    let invocations = collect_invocations(syntax);
    for (name, line) in &invocations.method_calls {
        if constants::TEST_PANIC_EXTRACTION_METHODS.contains(&name.as_str()) {
            violations.push(models::Violation::new(
                "RSH010",
                file.relative_path(),
                Some(*line),
                "test code calls unwrap()",
                "use expect with a message naming the assumption",
            ));
        }
    }
    violations
}

struct Invocations {
    macros: Vec<(String, usize)>,
    method_calls: Vec<(String, usize)>,
    suppressions: Vec<usize>,
}

struct InvocationVisitor {
    macros: Vec<(String, usize)>,
    method_calls: Vec<(String, usize)>,
    suppressions: Vec<usize>,
}

impl<'ast> Visit<'ast> for InvocationVisitor {
    fn visit_attribute(&mut self, node: &'ast syn::Attribute) {
        let path = node.path();
        if path.is_ident(constants::ALLOW_ATTRIBUTE) || path.is_ident(constants::EXPECT_ATTRIBUTE) {
            self.suppressions.push(path.span().start().line);
        }
        syn::visit::visit_attribute(self, node);
    }

    fn visit_macro(&mut self, node: &'ast syn::Macro) {
        if let Some(segment) = node.path.segments.last() {
            let line = segment.ident.span().start().line;
            self.macros.push((segment.ident.to_string(), line));
        }
        syn::visit::visit_macro(self, node);
    }

    fn visit_expr_method_call(&mut self, node: &'ast syn::ExprMethodCall) {
        let line = node.method.span().start().line;
        self.method_calls.push((node.method.to_string(), line));
        syn::visit::visit_expr_method_call(self, node);
    }

    fn visit_expr_call(&mut self, node: &'ast syn::ExprCall) {
        if let syn::Expr::Path(path) = node.func.as_ref() {
            if let Some(segment) = path.path.segments.last() {
                self.method_calls
                    .push((segment.ident.to_string(), segment.ident.span().start().line));
            }
        }
        syn::visit::visit_expr_call(self, node);
    }
}

fn forbids_unsafe_code(syntax: &syn::File) -> bool {
    syntax.attrs.iter().any(|attribute| {
        if !attribute.path().is_ident(constants::FORBID_ATTRIBUTE) {
            return false;
        }
        let syn::Meta::List(arguments) = &attribute.meta else {
            return false;
        };
        arguments
            .parse_args_with(
                syn::punctuated::Punctuated::<syn::Path, syn::Token![,]>::parse_terminated,
            )
            .is_ok_and(|paths| {
                paths
                    .iter()
                    .any(|path| path.is_ident(constants::UNSAFE_CODE_LINT))
            })
    })
}

fn collect_invocations(syntax: &syn::File) -> Invocations {
    let mut visitor = InvocationVisitor {
        macros: Vec::new(),
        method_calls: Vec::new(),
        suppressions: Vec::new(),
    };
    visitor.visit_file(syntax);
    Invocations {
        macros: visitor.macros,
        method_calls: visitor.method_calls,
        suppressions: visitor.suppressions,
    }
}

fn macro_violation(
    file: &models::SourceFile,
    name: &str,
    line: usize,
    kind: FileKind,
) -> Vec<models::Violation> {
    if constants::PANIC_MACROS.contains(&name) {
        return vec![models::Violation::new(
            "RSH003",
            file.relative_path(),
            Some(line),
            format!("library code invokes {name}!"),
            "return a Result with a crate error type from errors.rs",
        )];
    }
    if constants::ASSERT_MACROS.contains(&name) {
        return vec![models::Violation::new(
            "RSH004",
            file.relative_path(),
            Some(line),
            format!("library code invokes {name}!"),
            "replace the assertion with an explicit guard returning a crate error",
        )];
    }
    if constants::STDIO_MACROS.contains(&name) && kind != FileKind::BinAdapter {
        return vec![models::Violation::new(
            "RSH011",
            file.relative_path(),
            Some(line),
            format!("library code writes to stdio via {name}!"),
            "return data to the caller; only the bin adapter may print",
        )];
    }
    Vec::new()
}

struct ComparisonVisitor {
    string_lines: Vec<usize>,
    number_lines: Vec<usize>,
}

impl<'ast> Visit<'ast> for ComparisonVisitor {
    fn visit_expr_binary(&mut self, node: &'ast syn::ExprBinary) {
        let equality = matches!(node.op, syn::BinOp::Eq(_) | syn::BinOp::Ne(_));
        let ordering = matches!(
            node.op,
            syn::BinOp::Lt(_) | syn::BinOp::Le(_) | syn::BinOp::Gt(_) | syn::BinOp::Ge(_)
        );
        for operand in [node.left.as_ref(), node.right.as_ref()] {
            if equality && string_literal_line(operand).is_some() {
                self.string_lines.extend(string_literal_line(operand));
            }
            if (equality || ordering) && magic_number_line(operand).is_some() {
                self.number_lines.extend(magic_number_line(operand));
            }
        }
        syn::visit::visit_expr_binary(self, node);
    }
}

fn string_literal_line(operand: &syn::Expr) -> Option<usize> {
    let syn::Expr::Lit(literal) = operand else {
        return None;
    };
    let syn::Lit::Str(inner) = &literal.lit else {
        return None;
    };
    Some(inner.span().start().line)
}

fn magic_number_line(operand: &syn::Expr) -> Option<usize> {
    if let syn::Expr::Unary(unary) = operand {
        if matches!(unary.op, syn::UnOp::Neg(_)) {
            return magic_number_line(&unary.expr).and_then(|line| {
                let allowed = integer_digits(&unary.expr).as_deref() == Some("1");
                match allowed {
                    true => None,
                    false => Some(line),
                }
            });
        }
    }
    let syn::Expr::Lit(literal) = operand else {
        return None;
    };
    match &literal.lit {
        syn::Lit::Int(inner) => {
            let allowed = constants::ALLOWED_COMPARISON_NUMBERS.contains(&inner.base10_digits());
            match allowed {
                true => None,
                false => Some(inner.span().start().line),
            }
        }
        syn::Lit::Float(inner) => Some(inner.span().start().line),
        _ => None,
    }
}

fn integer_digits(operand: &syn::Expr) -> Option<String> {
    let syn::Expr::Lit(literal) = operand else {
        return None;
    };
    let syn::Lit::Int(inner) = &literal.lit else {
        return None;
    };
    Some(inner.base10_digits().to_owned())
}

fn check_comparisons(file: &models::SourceFile, syntax: &syn::File) -> Vec<models::Violation> {
    let mut visitor = ComparisonVisitor {
        string_lines: Vec::new(),
        number_lines: Vec::new(),
    };
    visitor.visit_file(syntax);
    let mut violations: Vec<models::Violation> = Vec::new();
    for line in &visitor.string_lines {
        violations.push(models::Violation::new(
            "RSH007",
            file.relative_path(),
            Some(*line),
            "string literal directly controls a comparison",
            "name the decision value in constants.rs and compare against the name",
        ));
    }
    for line in &visitor.number_lines {
        violations.push(models::Violation::new(
            "RSH008",
            file.relative_path(),
            Some(*line),
            "non-canonical numeric literal directly controls a comparison",
            "name the threshold in constants.rs; only -1, 0, and 1 are self-explanatory",
        ));
    }
    violations
}

fn check_comment_lines(file: &models::SourceFile) -> Vec<models::Violation> {
    let mut violations: Vec<models::Violation> = Vec::new();
    for (index, line) in file.source.lines().enumerate() {
        let trimmed = line.trim_start();
        let is_plain_comment =
            trimmed.starts_with("//") && !trimmed.starts_with("///") && !trimmed.starts_with("//!");
        if is_plain_comment {
            violations.push(models::Violation::new(
                "RSH002",
                file.relative_path(),
                Some(index + 1),
                "standalone comments are not allowed",
                "use clear names or move lasting explanation into docs or tests",
            ));
        }
    }
    violations
}

fn check_doc_comment_length(file: &models::SourceFile) -> Vec<models::Violation> {
    let mut violations: Vec<models::Violation> = Vec::new();
    let mut run_start: Option<usize> = None;
    let mut run_length: usize = 0;
    for (index, line) in file.source.lines().enumerate() {
        let trimmed = line.trim_start();
        let is_doc = trimmed.starts_with("///") || trimmed.starts_with("//!");
        if is_doc {
            run_length += 1;
            if run_start.is_none() {
                run_start = Some(index + 1);
            }
            continue;
        }
        violations.extend(doc_run_violation(file, run_start, run_length));
        run_start = None;
        run_length = 0;
    }
    violations.extend(doc_run_violation(file, run_start, run_length));
    violations
}

fn doc_run_violation(
    file: &models::SourceFile,
    run_start: Option<usize>,
    run_length: usize,
) -> Vec<models::Violation> {
    let Some(start) = run_start else {
        return Vec::new();
    };
    if run_length <= 1 {
        return Vec::new();
    }
    vec![models::Violation::new(
        "RSH001",
        file.relative_path(),
        Some(start),
        format!("doc comment spans {run_length} lines"),
        "keep one summary line and move extended rationale into docs or tests",
    )]
}
