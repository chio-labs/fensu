//! Embedded resources and cache observations share one macro traversal.

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
    let mut visitor = EmbeddedVisitor::default();
    visitor.visit_file(syntax);
    let domain = domain_directory(repo_root, file, ownership_roots);
    let mut violations: Vec<models::Violation> = Vec::new();
    for node in visitor.macros {
        let message = match literal(&node) {
            Some(literal) => path_fault(&file.path, domain.as_deref(), &literal),
            None => Some("embedded file paths must be literal"),
        };
        if let Some(message) = message {
            violations.push(models::Violation::new(models::ViolationRequest {
                code: "RSL106", path: file.relative_path(), line: Some(node.span().start().line),
                message, remediation: "embed an existing file using a literal path within the including source domain",
            }));
        }
    }
    for error in visitor.errors {
        violations.push(models::Violation::new(models::ViolationRequest {
            code: "RSL106",
            path: file.relative_path(),
            line: Some(error.span().start().line),
            message: format!("cannot inspect embedded file macro tokens: {error}"),
            remediation: "use a literal embedded file path in valid Rust macro tokens",
        }));
    }
    violations
}

pub(crate) fn observations(file: &models::SourceFile) -> Result<Vec<String>, String> {
    let path = &file.path;
    let Some(syntax) = &file.syntax.file else {
        return Ok(Vec::new());
    };
    let mut visitor = EmbeddedVisitor::default();
    visitor.visit_file(syntax);
    if let Some(error) = visitor.errors.first() {
        return Err(format!(
            "cannot observe embedded paths in {}: {error}",
            path.display()
        ));
    }
    let mut observations: Vec<String> = Vec::new();
    for node in visitor.macros {
        let Some(literal) = literal(&node) else {
            continue;
        };
        observations.push(literal.clone());
        let candidate = path.parent().unwrap_or(path).join(&literal);
        match candidate.canonicalize() {
            Ok(resolved) => {
                observations.push(resolved.to_string_lossy().into_owned());
                observations.push(match resolved.metadata() {
                    Ok(metadata) if metadata.is_file() => "file".to_owned(),
                    Ok(metadata) if metadata.is_dir() => "directory".to_owned(),
                    Ok(_) => "other".to_owned(),
                    Err(error) => format!("unresolvable: {error}"),
                });
            }
            Err(error) => observations.push(format!("unresolvable: {error}")),
        }
    }
    Ok(observations)
}

fn literal(node: &syn::Macro) -> Option<String> {
    let parser = syn::punctuated::Punctuated::<syn::LitStr, syn::Token![,]>::parse_terminated;
    match parser.parse2(node.tokens.clone()) {
        Ok(literals) if literals.len() == 1 => literals.first().map(syn::LitStr::value),
        _ => None,
    }
}

fn domain_directory(
    repo_root: &Path,
    file: &models::SourceFile,
    roots: &[String],
) -> Option<PathBuf> {
    let root = file.ownership_root(roots)?;
    let relative = file.ownership_relative(roots)?;
    let (domain, _) = relative.split_once('/')?;
    if matches!(domain, "bin" | "tests") {
        return None;
    }
    Some(repo_root.join(root).join(domain))
}

fn path_fault(path: &Path, domain: Option<&Path>, literal: &str) -> Option<&'static str> {
    let Some(domain) = domain else {
        return Some(
            "embedded files require an owning domain; source-root files cannot embed resources",
        );
    };
    let candidate = path.parent()?.join(literal);
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

#[derive(Default)]
struct EmbeddedVisitor {
    macros: Vec<syn::Macro>,
    errors: Vec<syn::Error>,
}

impl EmbeddedVisitor {
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
            self.errors.push(error);
        }
    }
}

impl<'ast> Visit<'ast> for EmbeddedVisitor {
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
        if supported_prefix
            && matches!(
                segments.last().map(String::as_str),
                Some("include_str" | "include_bytes")
            )
        {
            self.macros.push(node.clone());
        }
        self.visit_tokens(node.tokens.clone());
    }
}
