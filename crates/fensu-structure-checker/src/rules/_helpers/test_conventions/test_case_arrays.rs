//! Local test case array facts and policy.

use syn::spanned::Spanned;
use syn::visit::Visit;

use crate::constants;
use crate::models;
use crate::rules::_helpers::imports::reference_paths;

/// Check local `test_cases` array conventions for one test function.
pub(crate) fn check(
    file: &models::SourceFile,
    syntax: &syn::File,
    item_fn: &syn::ItemFn,
) -> Vec<models::Violation> {
    let facts = collect_facts(item_fn);
    let line = Some(item_fn.sig.ident.span().start().line);
    let mut violations: Vec<models::Violation> = Vec::new();
    if facts.binding_line.is_none() {
        violations.push(models::Violation::new(models::ViolationRequest {
            code: "RST401",
            path: file.relative_path(),
            line,
            message: "test declares no test_cases binding",
            remediation: "declare let test_cases = [ ... ]; of test_types structs first",
        }));
        violations.push(models::Violation::new(models::ViolationRequest {
            code: "RST405",
            path: file.relative_path(),
            line,
            message: "test has no local test_cases parametrization binding",
            remediation: "declare a local test_cases array before executing the cases",
        }));
    }
    if facts.array_length == Some(0) {
        violations.push(models::Violation::new(models::ViolationRequest {
            code: "RST411",
            path: file.relative_path(),
            line: facts.binding_line,
            message: "test_cases must be a visible non-empty array literal",
            remediation: "inline at least one test_types case in the array",
        }));
    }
    for (pattern, over_cases, loop_line) in &facts.for_loops {
        if *over_cases && pattern != constants::TEST_CASE_LOOP_VARIABLE {
            violations.push(models::Violation::new(models::ViolationRequest {
                code: "RST402",
                path: file.relative_path(),
                line: Some(*loop_line),
                message: format!("case loop binds {pattern}"),
                remediation: "name the loop variable test_case",
            }));
            violations.push(models::Violation::new(models::ViolationRequest {
                code: "RST406",
                path: file.relative_path(),
                line: Some(*loop_line),
                message: format!("case executor binds {pattern} instead of test_case"),
                remediation: "bind each test_cases item as test_case",
            }));
        }
    }
    if facts.binding_line.is_some() && !facts.initializer_is_array {
        violations.push(models::Violation::new(models::ViolationRequest {
            code: "RST408",
            path: file.relative_path(),
            line: facts.binding_line,
            message: "test_cases values are not an inline array literal",
            remediation: "construct the visible test case values inline in the test function",
        }));
    }
    let local_case_types = local_case_types(syntax);
    for element in &facts.elements {
        violations.extend(check_element(file, element, &local_case_types));
    }
    violations
}

fn check_element(
    file: &models::SourceFile,
    element: &CaseElement,
    local_case_types: &std::collections::BTreeSet<String>,
) -> Vec<models::Violation> {
    if !element.named_struct {
        return vec![models::Violation::new(models::ViolationRequest {
            code: "RST412",
            path: file.relative_path(),
            line: Some(element.line),
            message: "test case is not a named struct literal",
            remediation: "construct a typed local test-case struct instead of a tuple or map",
        })];
    }
    let mut violations: Vec<models::Violation> = Vec::new();
    if !element
        .path
        .last()
        .is_some_and(|name| name.ends_with(constants::TEST_CASE_STRUCT_SUFFIX))
    {
        violations.push(models::Violation::new(models::ViolationRequest {
            code: "RST403",
            path: file.relative_path(),
            line: Some(element.line),
            message: "test case constructor does not name a TestCase type",
            remediation: "construct a *TestCase struct declared in local test_types.rs",
        }));
    }
    let constructor = element.path.last();
    let locally_owned = element
        .path
        .iter()
        .any(|part| part == constants::TEST_TYPES_MODULE)
        || constructor.is_some_and(|name| local_case_types.contains(name));
    if !locally_owned {
        violations.push(models::Violation::new(models::ViolationRequest {
            code: "RST413",
            path: file.relative_path(),
            line: Some(element.line),
            message: "test case constructor is not owned by local test_types",
            remediation: "construct the case through the sibling test_types module",
        }));
    }
    violations
}

struct TestCaseArrayFacts {
    binding_line: Option<usize>,
    array_length: Option<usize>,
    initializer_is_array: bool,
    elements: Vec<CaseElement>,
    for_loops: Vec<(String, bool, usize)>,
}

struct CaseElement {
    line: usize,
    path: Vec<String>,
    named_struct: bool,
}

struct FactsVisitor {
    facts: TestCaseArrayFacts,
}

impl<'ast> Visit<'ast> for FactsVisitor {
    fn visit_local(&mut self, node: &'ast syn::Local) {
        if pattern_name(&node.pat).as_deref() == Some(constants::TEST_CASES_BINDING) {
            self.facts.binding_line = Some(node.let_token.span.start().line);
            if let Some(initializer) = &node.init {
                self.facts.array_length = array_length(&initializer.expr);
                self.facts.initializer_is_array = array_expression(&initializer.expr).is_some();
                self.facts.elements = case_elements(&initializer.expr);
            }
        }
        syn::visit::visit_local(self, node);
    }

    fn visit_expr_for_loop(&mut self, node: &'ast syn::ExprForLoop) {
        let pattern = pattern_name(&node.pat).unwrap_or_default();
        let over_cases = expression_mentions(&node.expr, constants::TEST_CASES_BINDING);
        let line = node.for_token.span.start().line;
        self.facts.for_loops.push((pattern, over_cases, line));
        syn::visit::visit_expr_for_loop(self, node);
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

fn collect_facts(item_fn: &syn::ItemFn) -> TestCaseArrayFacts {
    let mut visitor = FactsVisitor {
        facts: TestCaseArrayFacts {
            binding_line: None,
            array_length: None,
            initializer_is_array: false,
            elements: Vec::new(),
            for_loops: Vec::new(),
        },
    };
    visitor.visit_block(&item_fn.block);
    visitor.facts
}

fn pattern_name(pattern: &syn::Pat) -> Option<String> {
    match pattern {
        syn::Pat::Ident(pat_ident) => Some(pat_ident.ident.to_string()),
        syn::Pat::Type(pat_type) => pattern_name(&pat_type.pat),
        _ => None,
    }
}

fn array_length(expression: &syn::Expr) -> Option<usize> {
    array_expression(expression).map(|array| array.elems.len())
}

fn array_expression(expression: &syn::Expr) -> Option<&syn::ExprArray> {
    match expression {
        syn::Expr::Array(array) => Some(array),
        syn::Expr::Reference(reference) => array_expression(&reference.expr),
        _ => None,
    }
}

fn case_elements(expression: &syn::Expr) -> Vec<CaseElement> {
    let Some(array) = array_expression(expression) else {
        return Vec::new();
    };
    array.elems.iter().map(case_element).collect()
}

fn case_element(element: &syn::Expr) -> CaseElement {
    match element {
        syn::Expr::Struct(item) => CaseElement {
            line: item.path.span().start().line,
            path: item
                .path
                .segments
                .iter()
                .map(|segment| segment.ident.to_string())
                .collect(),
            named_struct: true,
        },
        _ => CaseElement {
            line: element.span().start().line,
            path: Vec::new(),
            named_struct: false,
        },
    }
}

fn local_case_types(syntax: &syn::File) -> std::collections::BTreeSet<String> {
    let mut names: std::collections::BTreeSet<String> = std::collections::BTreeSet::new();
    for item in &syntax.items {
        let syn::Item::Use(item_use) = item else {
            continue;
        };
        for path in reference_paths::use_paths(&item_use.tree) {
            if !path.iter().any(|part| part == constants::TEST_TYPES_MODULE) {
                continue;
            }
            let Some(name) = path.last() else {
                continue;
            };
            if name != constants::TEST_TYPES_MODULE {
                let _ = names.insert(name.clone());
            }
        }
    }
    names
}

fn expression_mentions(expression: &syn::Expr, name: &str) -> bool {
    let mut visitor = MentionVisitor {
        name: name.to_owned(),
        found: false,
    };
    visitor.visit_expr(expression);
    visitor.found
}
