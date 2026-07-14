//! Test shape rules: names, in-function cases, loops, assertions, control flow.

use syn::visit::Visit;

use crate::constants;
use crate::models;
use crate::types::FileKind;

/// Check function-level test shape rules for one test file.
pub(crate) fn check(
    file: &models::SourceFile,
    syntax: &syn::File,
    kind: FileKind,
) -> Vec<models::Violation> {
    let mut violations: Vec<models::Violation> = Vec::new();
    for item in &syntax.items {
        let syn::Item::Fn(item_fn) = item else {
            continue;
        };
        if kind == FileKind::TestHelpers {
            violations.extend(check_control_flow(file, item_fn));
        }
        if kind == FileKind::TestTopic && has_test_attribute(item_fn) {
            violations.extend(check_test_function(file, item_fn));
        }
    }
    violations
}

fn check_test_function(file: &models::SourceFile, item_fn: &syn::ItemFn) -> Vec<models::Violation> {
    let mut violations = check_test_name(file, item_fn);
    violations.extend(check_control_flow(file, item_fn));
    let body = collect_body(item_fn);
    let line = Some(item_fn.sig.ident.span().start().line);
    if body.case_binding_line.is_none() {
        violations.push(models::Violation::new(
            "RST401",
            file.relative_path(),
            line,
            "test declares no test_cases binding",
            "declare let test_cases = [ ... ]; of test_types structs first",
        ));
    }
    if body.case_binding_line.is_some() && body.case_array_length.unwrap_or(0) == 0 {
        violations.push(models::Violation::new(
            "RST411",
            file.relative_path(),
            body.case_binding_line,
            "test_cases must be a visible non-empty array literal",
            "inline at least one test_types case in the array",
        ));
    }
    for (pattern, over_cases, loop_line) in &body.for_loops {
        if *over_cases && pattern != constants::TEST_CASE_LOOP_VARIABLE {
            violations.push(models::Violation::new(
                "RST402",
                file.relative_path(),
                Some(*loop_line),
                format!("case loop binds {pattern}"),
                "name the loop variable test_case",
            ));
        }
    }
    violations.extend(check_assertions(file, item_fn, &body));
    violations.extend(check_executor(file, item_fn, &body));
    violations
}

fn check_test_name(file: &models::SourceFile, item_fn: &syn::ItemFn) -> Vec<models::Violation> {
    let name = item_fn.sig.ident.to_string();
    let well_formed =
        name.starts_with("given_") && name.contains("_when_") && name.contains("_then_");
    if well_formed {
        return Vec::new();
    }
    vec![models::Violation::new(
        "RST302",
        file.relative_path(),
        Some(item_fn.sig.ident.span().start().line),
        format!("test name {name} does not follow the naming contract"),
        "use given_<state>_when_<action>_then_<outcome>",
    )]
}

fn check_control_flow(file: &models::SourceFile, item_fn: &syn::ItemFn) -> Vec<models::Violation> {
    let mut visitor = ControlFlowVisitor { found: Vec::new() };
    visitor.visit_block(&item_fn.block);
    visitor
        .found
        .iter()
        .map(|(construct, line)| {
            models::Violation::new(
                "RST104",
                file.relative_path(),
                Some(*line),
                format!("test code contains {construct}"),
                "keep tests and their helpers branch-free; split variants into cases",
            )
        })
        .collect()
}

fn check_assertions(
    file: &models::SourceFile,
    item_fn: &syn::ItemFn,
    body: &TestBody,
) -> Vec<models::Violation> {
    let line = Some(item_fn.sig.ident.span().start().line);
    if body.assert_tokens.is_empty() {
        return vec![models::Violation::new(
            "RST404",
            file.relative_path(),
            line,
            "test contains no assertion against an expected_ field",
            "assert the observed behavior against test_case.expected_*",
        )];
    }
    let mut violations: Vec<models::Violation> = Vec::new();
    let mentions_expected = body
        .assert_tokens
        .iter()
        .any(|tokens| references_case_field(tokens, constants::EXPECTED_FIELD_PREFIX, true));
    if !mentions_expected {
        violations.push(models::Violation::new(
            "RST404",
            file.relative_path(),
            line,
            "assertions never reference an expected_ field",
            "assert against test_case.expected_* outcomes",
        ));
    }
    let mentions_description = body
        .assert_tokens
        .iter()
        .any(|tokens| references_case_field(tokens, constants::DESCRIPTION_FIELD, false));
    if !mentions_description {
        violations.push(models::Violation::new(
            "RST407",
            file.relative_path(),
            line,
            "assertion messages never include the case description",
            "add \"{}\", test_case.description to each assertion",
        ));
    }
    violations
}

fn check_executor(
    file: &models::SourceFile,
    item_fn: &syn::ItemFn,
    body: &TestBody,
) -> Vec<models::Violation> {
    let case_loops = body
        .for_loops
        .iter()
        .filter(|(_, over_cases, _)| *over_cases)
        .count();
    let executors = case_loops + body.run_cases_calls;
    if executors == 1 {
        return Vec::new();
    }
    vec![models::Violation::new(
        "RST420",
        file.relative_path(),
        Some(item_fn.sig.ident.span().start().line),
        format!("test executes its cases through {executors} paths"),
        "use exactly one for test_case loop or one helpers::run_cases call",
    )]
}

struct TestBody {
    case_binding_line: Option<usize>,
    case_array_length: Option<usize>,
    for_loops: Vec<(String, bool, usize)>,
    assert_tokens: Vec<proc_macro2::TokenStream>,
    run_cases_calls: usize,
}

struct BodyVisitor {
    body: TestBody,
}

impl<'ast> Visit<'ast> for BodyVisitor {
    fn visit_local(&mut self, node: &'ast syn::Local) {
        if pattern_name(&node.pat).as_deref() == Some(constants::TEST_CASES_BINDING) {
            self.body.case_binding_line = Some(node.let_token.span.start().line);
            self.body.case_array_length =
                node.init.as_ref().and_then(|init| array_length(&init.expr));
        }
        syn::visit::visit_local(self, node);
    }

    fn visit_expr_for_loop(&mut self, node: &'ast syn::ExprForLoop) {
        let pattern = pattern_name(&node.pat).unwrap_or_default();
        let over_cases = expression_mentions(&node.expr, constants::TEST_CASES_BINDING);
        let line = node.for_token.span.start().line;
        self.body.for_loops.push((pattern, over_cases, line));
        syn::visit::visit_expr_for_loop(self, node);
    }

    fn visit_macro(&mut self, node: &'ast syn::Macro) {
        let name = node
            .path
            .segments
            .last()
            .map(|segment| segment.ident.to_string())
            .unwrap_or_default();
        if constants::ASSERT_MACROS.contains(&name.as_str()) {
            self.body.assert_tokens.push(node.tokens.clone());
        }
        syn::visit::visit_macro(self, node);
    }

    fn visit_expr_call(&mut self, node: &'ast syn::ExprCall) {
        if let syn::Expr::Path(path) = node.func.as_ref() {
            let last = path
                .path
                .segments
                .last()
                .map(|segment| segment.ident.to_string())
                .unwrap_or_default();
            if last == constants::CASE_RUNNER_NAME {
                self.body.run_cases_calls += 1;
            }
        }
        syn::visit::visit_expr_call(self, node);
    }
}

fn references_case_field(
    stream: &proc_macro2::TokenStream,
    field_name: &str,
    prefix: bool,
) -> bool {
    let tokens: Vec<proc_macro2::TokenTree> = stream.clone().into_iter().collect();
    if tokens.windows(3).any(|window| {
        let [
            proc_macro2::TokenTree::Ident(_owner),
            proc_macro2::TokenTree::Punct(dot),
            proc_macro2::TokenTree::Ident(field),
        ] = window
        else {
            return false;
        };
        let matches_field = match prefix {
            true => field.to_string().starts_with(field_name),
            false => field == field_name,
        };
        dot.as_char() == '.' && matches_field
    }) {
        return true;
    }
    tokens.iter().any(|token| match token {
        proc_macro2::TokenTree::Group(group) => {
            references_case_field(&group.stream(), field_name, prefix)
        }
        _ => false,
    })
}

struct ControlFlowVisitor {
    found: Vec<(&'static str, usize)>,
}

impl<'ast> Visit<'ast> for ControlFlowVisitor {
    fn visit_expr_if(&mut self, node: &'ast syn::ExprIf) {
        self.found
            .push(("an if branch", node.if_token.span.start().line));
        syn::visit::visit_expr_if(self, node);
    }

    fn visit_expr_match(&mut self, node: &'ast syn::ExprMatch) {
        self.found
            .push(("a match expression", node.match_token.span.start().line));
        syn::visit::visit_expr_match(self, node);
    }

    fn visit_expr_while(&mut self, node: &'ast syn::ExprWhile) {
        self.found
            .push(("a while loop", node.while_token.span.start().line));
        syn::visit::visit_expr_while(self, node);
    }

    fn visit_expr_loop(&mut self, node: &'ast syn::ExprLoop) {
        self.found
            .push(("a bare loop", node.loop_token.span.start().line));
        syn::visit::visit_expr_loop(self, node);
    }
}

struct MentionVisitor {
    name: String,
    found: bool,
}

impl<'ast> Visit<'ast> for MentionVisitor {
    fn visit_expr_path(&mut self, node: &'ast syn::ExprPath) {
        if node.path.is_ident(&self.name) {
            self.found = true;
        }
        syn::visit::visit_expr_path(self, node);
    }
}

fn collect_body(item_fn: &syn::ItemFn) -> TestBody {
    let mut visitor = BodyVisitor {
        body: TestBody {
            case_binding_line: None,
            case_array_length: None,
            for_loops: Vec::new(),
            assert_tokens: Vec::new(),
            run_cases_calls: 0,
        },
    };
    visitor.visit_block(&item_fn.block);
    visitor.body
}

fn pattern_name(pattern: &syn::Pat) -> Option<String> {
    match pattern {
        syn::Pat::Ident(pat_ident) => Some(pat_ident.ident.to_string()),
        syn::Pat::Type(pat_type) => pattern_name(&pat_type.pat),
        _ => None,
    }
}

fn array_length(expression: &syn::Expr) -> Option<usize> {
    match expression {
        syn::Expr::Array(array) => Some(array.elems.len()),
        syn::Expr::Reference(reference) => array_length(&reference.expr),
        _ => None,
    }
}

fn expression_mentions(expression: &syn::Expr, name: &str) -> bool {
    let mut visitor = MentionVisitor {
        name: name.to_owned(),
        found: false,
    };
    visitor.visit_expr(expression);
    visitor.found
}

fn has_test_attribute(item_fn: &syn::ItemFn) -> bool {
    item_fn
        .attrs
        .iter()
        .any(|attribute| attribute.path().is_ident("test"))
}
