//! Embedded resources stay inside the including file's ownership domain.

use std::path::{Path, PathBuf};

use syn::parse::discouraged::Speculative;
use syn::parse::Parser;
use syn::spanned::Spanned;
use syn::visit::Visit;

use crate::models;

pub(crate) fn check(
    repo_root: &Path,
    file: &models::SourceFile,
    ownership_roots: &[String],
) -> Vec<models::Violation> {
    let Some(syntax) = &file.syntax.file else {
        return Vec::new();
    };
    let mut visitor = EmbeddedVisitor {
        file,
        domain: domain_directory(repo_root, file, ownership_roots),
        violations: Vec::new(),
    };
    visitor.visit_file(syntax);
    visitor.violations
}

fn domain_directory(
    repo_root: &Path,
    file: &models::SourceFile,
    ownership_roots: &[String],
) -> Option<PathBuf> {
    let root = file.ownership_root(ownership_roots)?;
    let relative = file.ownership_relative(ownership_roots)?;
    let (domain, _) = relative.split_once('/')?;
    if matches!(domain, "bin" | "tests") {
        return None;
    }
    Some(repo_root.join(root).join(domain))
}

struct EmbeddedVisitor<'a> {
    file: &'a models::SourceFile,
    domain: Option<PathBuf>,
    violations: Vec<models::Violation>,
}

impl EmbeddedVisitor<'_> {
    fn visit_tokens(&mut self, tokens: proc_macro2::TokenStream) {
        let parser = |input: syn::parse::ParseStream<'_>| -> syn::Result<()> {
            while !input.is_empty() {
                let fork = input.fork();
                if let Ok(node) = fork.parse::<syn::Macro>() {
                    input.advance_to(&fork);
                    self.visit_macro(&node);
                } else if let proc_macro2::TokenTree::Group(group) = input.parse()? {
                    self.visit_tokens(group.stream());
                }
            }
            Ok(())
        };
        if let Err(error) = parser.parse2(tokens) {
            self.violations
                .push(models::Violation::new(models::ViolationRequest {
                    code: "RSL106",
                    path: self.file.relative_path(),
                    line: Some(error.span().start().line),
                    message: format!("cannot inspect embedded file macro tokens: {error}"),
                    remediation: "use a literal embedded file path in valid Rust macro tokens",
                }));
        }
    }

    fn check_macro(&mut self, node: &syn::Macro) {
        let parser = syn::punctuated::Punctuated::<syn::LitStr, syn::Token![,]>::parse_terminated;
        let message = match parser.parse2(node.tokens.clone()) {
            Ok(literals) if literals.len() == 1 => literals
                .first()
                .and_then(|literal| self.path_fault(&literal.value())),
            _ => Some("embedded file paths must be literal"),
        };
        if let Some(message) = message {
            self.violations.push(models::Violation::new(models::ViolationRequest {
                code: "RSL106",
                path: self.file.relative_path(),
                line: Some(node.span().start().line),
                message,
                remediation: "embed an existing file using a literal path within the including source domain",
            }));
        }
    }

    fn path_fault(&self, literal: &str) -> Option<&'static str> {
        let Some(domain) = &self.domain else {
            return Some(
                "embedded files require an owning domain; source-root files cannot embed resources",
            );
        };
        let candidate = self.file.path.parent()?.join(literal);
        let Ok(resolved) = candidate.canonicalize() else {
            return Some("embedded file target is missing or cannot be resolved");
        };
        if !resolved.starts_with(domain) {
            return Some("embedded file target escapes the including source domain");
        }
        if !resolved.is_file() {
            return Some("embedded file target must be an existing file");
        }
        None
    }
}

impl<'ast> Visit<'ast> for EmbeddedVisitor<'_> {
    fn visit_macro(&mut self, node: &'ast syn::Macro) {
        let segments = node
            .path
            .segments
            .iter()
            .map(|part| part.ident.to_string())
            .collect::<Vec<_>>();
        let supported_prefix = match segments.as_slice() {
            [_] => true,
            [prefix, _] => matches!(prefix.as_str(), "std" | "core"),
            _ => false,
        };
        let is_include = matches!(
            segments.last().map(String::as_str),
            Some("include_str" | "include_bytes")
        ) && supported_prefix;
        if is_include {
            self.check_macro(node);
        }
        self.visit_tokens(node.tokens.clone());
    }
}
