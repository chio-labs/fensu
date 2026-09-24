//! Extract normalised `fn` item units from Rust sources.

use std::path::Path;
use std::str::FromStr;

use proc_macro2::{Delimiter, LineColumn, Spacing, TokenStream, TokenTree};
use quote::ToTokens;
use syn::{Attribute, Block, ImplItem, Item, Signature, TraitItem, Type, Visibility};

use crate::dupes::constants::{
    PLACEHOLDER_BYTE, PLACEHOLDER_BYTE_STRING, PLACEHOLDER_CHAR, PLACEHOLDER_IDENTIFIER,
    PLACEHOLDER_LIFETIME, PLACEHOLDER_NUMBER, PLACEHOLDER_STRING,
};
use crate::dupes::models::{ExtractedUnit, RustFileUnits};

const KEYWORDS: &[&str] = &[
    "as", "async", "await", "break", "const", "continue", "crate", "dyn", "else", "enum", "extern",
    "false", "fn", "for", "if", "impl", "in", "let", "loop", "match", "mod", "move", "mut", "pub",
    "ref", "return", "self", "Self", "static", "struct", "super", "trait", "true", "type",
    "unsafe", "use", "where", "while",
];
const OPERATORS: &[&str] = &[
    "..=", "...", "<<=", ">>=", "::", "->", "=>", "==", "!=", "<=", ">=", "&&", "||", "+=", "-=",
    "*=", "/=", "%=", "^=", "&=", "|=", "..",
];
const MODULE_ROOT_FILES: &[&str] = &["mod.rs", "lib.rs", "main.rs"];
const ATTRIBUTE_MARKERS: &[&str] = &["#", "#!"];
const CALL_SUFFIXES: &[&str] = &["(", "!"];
const DOC_ATTRIBUTE: &str = "doc";
const CFG_ATTRIBUTE: &str = "cfg";
const TEST_ATTRIBUTE: &str = "test";
const NEGATION: &str = "not";
const FUNCTION_KEYWORD: &str = "fn";
const LIFETIME_MARKER: char = '\'';

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum FlatKind {
    Identifier,
    Punctuation,
    Literal,
    Lifetime,
}

#[derive(Clone, Debug)]
struct FlatToken {
    kind: FlatKind,
    text: String,
    start: LineColumn,
}

struct Scanner<'a> {
    tokens: Vec<FlatToken>,
    relative_path: &'a str,
    include_tests: bool,
    units: RustFileUnits,
}

/// Return every `fn` item with a body, skipping test-only items unless requested.
pub(crate) fn extract_rust_units(
    relative_path: &str,
    source: &str,
    include_tests: bool,
) -> RustFileUnits {
    let text = without_shebang(source);
    let (Ok(stream), Ok(file)) = (TokenStream::from_str(&text), syn::parse_file(&text)) else {
        return RustFileUnits::default();
    };
    let mut flattener = Flattener::default();
    flattener.flatten(stream);
    let mut scanner = Scanner {
        tokens: flattener.tokens,
        relative_path,
        include_tests,
        units: RustFileUnits::default(),
    };
    scanner.items(&file.items, None);
    scanner.units
}

fn without_shebang(source: &str) -> String {
    let source = source.strip_prefix('\u{feff}').unwrap_or(source);
    if source.starts_with("#!") && !source.starts_with("#![") {
        let end = source.find('\n').unwrap_or(source.len());
        return format!("{}{}", " ".repeat(end), &source[end..]);
    }
    source.to_owned()
}

#[derive(Default)]
struct Flattener {
    tokens: Vec<FlatToken>,
}

impl Flattener {
    fn flatten(&mut self, stream: TokenStream) {
        let trees: Vec<TokenTree> = stream.into_iter().collect();
        let mut index = 0;
        while index < trees.len() {
            match &trees[index] {
                TokenTree::Group(group) => {
                    let (open, close) = delimiters(group.delimiter());
                    if !open.is_empty() {
                        self.tokens
                            .push(punctuation(open, group.span_open().start()));
                    }
                    self.flatten(group.stream());
                    if !close.is_empty() {
                        self.tokens
                            .push(punctuation(close, group.span_close().start()));
                    }
                }
                TokenTree::Ident(ident) => self.tokens.push(FlatToken {
                    kind: FlatKind::Identifier,
                    text: ident.to_string(),
                    start: ident.span().start(),
                }),
                TokenTree::Literal(literal) => self.tokens.push(FlatToken {
                    kind: FlatKind::Literal,
                    text: literal.to_string(),
                    start: literal.span().start(),
                }),
                TokenTree::Punct(_) => {
                    index = self.punctuation_run(&trees, index);
                    continue;
                }
            }
            index += 1;
        }
    }

    /// Merge a joint punctuation run into the operators a Rust lexer reports.
    fn punctuation_run(&mut self, trees: &[TokenTree], start: usize) -> usize {
        let mut run: Vec<(char, LineColumn)> = Vec::new();
        let mut index = start;
        while let Some(TokenTree::Punct(punct)) = trees.get(index) {
            index += 1;
            if punct.as_char() == LIFETIME_MARKER {
                if let Some(TokenTree::Ident(ident)) = trees.get(index) {
                    self.push_operators(&run);
                    self.tokens.push(FlatToken {
                        kind: FlatKind::Lifetime,
                        text: format!("{LIFETIME_MARKER}{ident}"),
                        start: punct.span().start(),
                    });
                    return index + 1;
                }
            }
            run.push((punct.as_char(), punct.span().start()));
            if punct.spacing() == Spacing::Alone {
                break;
            }
        }
        if is_doc_attribute(trees, start, index) {
            return index + 1;
        }
        self.push_operators(&run);
        index
    }

    fn push_operators(&mut self, run: &[(char, LineColumn)]) {
        let mut position = 0;
        while position < run.len() {
            let rest: String = run[position..]
                .iter()
                .map(|(character, _)| *character)
                .collect();
            let width = OPERATORS
                .iter()
                .find(|operator| rest.starts_with(**operator))
                .map_or(1, |operator| operator.len());
            let text: String = rest.chars().take(width).collect();
            self.tokens.push(punctuation(&text, run[position].1));
            position += width;
        }
    }
}

fn delimiters(delimiter: Delimiter) -> (&'static str, &'static str) {
    match delimiter {
        Delimiter::Parenthesis => ("(", ")"),
        Delimiter::Brace => ("{", "}"),
        Delimiter::Bracket => ("[", "]"),
        Delimiter::None => ("", ""),
    }
}

fn punctuation(text: &str, start: LineColumn) -> FlatToken {
    FlatToken {
        kind: FlatKind::Punctuation,
        text: text.to_owned(),
        start,
    }
}

fn is_doc_attribute(trees: &[TokenTree], start: usize, end: usize) -> bool {
    let marker: String = trees[start..end]
        .iter()
        .filter_map(|tree| match tree {
            TokenTree::Punct(punct) => Some(punct.as_char()),
            _ => None,
        })
        .collect();
    if !ATTRIBUTE_MARKERS.contains(&marker.as_str()) {
        return false;
    }
    let Some(TokenTree::Group(group)) = trees.get(end) else {
        return false;
    };
    group.delimiter() == Delimiter::Bracket
        && matches!(group.stream().into_iter().next(), Some(TokenTree::Ident(ident)) if ident == DOC_ATTRIBUTE)
}

fn literal_placeholder(text: &str) -> &'static str {
    if text.starts_with("b'") {
        PLACEHOLDER_BYTE
    } else if text.starts_with("b\"") || text.starts_with("br") {
        PLACEHOLDER_BYTE_STRING
    } else if text.starts_with('\'') {
        PLACEHOLDER_CHAR
    } else if text.starts_with('"') || text.starts_with('r') || text.starts_with('c') {
        PLACEHOLDER_STRING
    } else {
        PLACEHOLDER_NUMBER
    }
}

fn is_test_attribute(attribute: &Attribute) -> bool {
    let path = attribute.path();
    if path.is_ident(CFG_ATTRIBUTE) {
        let words: Vec<String> = attribute
            .meta
            .to_token_stream()
            .into_iter()
            .flat_map(|tree| match tree {
                TokenTree::Group(group) => group.stream().into_iter().collect::<Vec<_>>(),
                other => vec![other],
            })
            .map(|tree| tree.to_string())
            .collect();
        return words.iter().any(|word| word == TEST_ATTRIBUTE)
            && !words.iter().any(|word| word == NEGATION);
    }
    path.segments
        .last()
        .is_some_and(|segment| segment.ident == TEST_ATTRIBUTE)
}

fn owner_name(self_type: &Type) -> Option<String> {
    match self_type {
        Type::Path(path) => path
            .path
            .segments
            .last()
            .map(|segment| segment.ident.to_string()),
        Type::Reference(reference) => owner_name(&reference.elem),
        Type::Paren(inner) => owner_name(&inner.elem),
        _ => None,
    }
}

fn first_line(parts: &[&dyn ToTokens]) -> Option<usize> {
    parts
        .iter()
        .filter_map(|part| part.to_token_stream().into_iter().next())
        .map(|tree| match tree {
            TokenTree::Group(group) => group.span_open().start().line,
            other => other.span().start().line,
        })
        .min()
}

impl Scanner<'_> {
    fn skipped(&self, attributes: &[Attribute]) -> bool {
        !self.include_tests && attributes.iter().any(is_test_attribute)
    }

    fn items(&mut self, items: &[Item], owner: Option<&str>) {
        for item in items {
            match item {
                Item::Fn(function) if !self.skipped(&function.attrs) => {
                    self.emit(owner, &function.vis, &function.sig, &function.block);
                }
                Item::Impl(block) if !self.skipped(&block.attrs) => {
                    let name = owner_name(&block.self_ty);
                    for member in &block.items {
                        if let ImplItem::Fn(function) = member {
                            if !self.skipped(&function.attrs) {
                                self.emit(
                                    name.as_deref(),
                                    &function.vis,
                                    &function.sig,
                                    &function.block,
                                );
                            }
                        }
                    }
                }
                Item::Trait(definition) if !self.skipped(&definition.attrs) => {
                    let name = definition.ident.to_string();
                    for member in &definition.items {
                        if let TraitItem::Fn(function) = member {
                            if let (Some(block), false) =
                                (&function.default, self.skipped(&function.attrs))
                            {
                                self.emit(
                                    Some(&name),
                                    &Visibility::Inherited,
                                    &function.sig,
                                    block,
                                );
                            }
                        }
                    }
                }
                Item::Mod(module) => match (self.skipped(&module.attrs), &module.content) {
                    (true, None) => self.record_test_module(&module.ident.to_string()),
                    (false, Some((_, nested))) => self.items(nested, owner),
                    (true, Some(_)) | (false, None) => {}
                },
                _ => {}
            }
        }
    }

    fn record_test_module(&mut self, name: &str) {
        let path = Path::new(self.relative_path);
        let file_name = path
            .file_name()
            .and_then(|value| value.to_str())
            .unwrap_or_default();
        let parent = path.parent().unwrap_or_else(|| Path::new(""));
        let base = if MODULE_ROOT_FILES.contains(&file_name) {
            parent.to_path_buf()
        } else {
            parent.join(path.file_stem().unwrap_or_default())
        };
        let module = base.join(name).to_string_lossy().replace('\\', "/");
        self.units.test_module_prefixes.push(format!("{module}.rs"));
        self.units.test_module_prefixes.push(format!("{module}/"));
    }

    fn emit(
        &mut self,
        owner: Option<&str>,
        visibility: &Visibility,
        signature: &Signature,
        block: &Block,
    ) {
        let start = signature.fn_token.span.start();
        let close = block.brace_token.span.close().start();
        let first = self
            .tokens
            .partition_point(|token| position(token.start) < position(start));
        let last = self
            .tokens
            .partition_point(|token| position(token.start) <= position(close));
        let name = signature.ident.to_string();
        let mut unit = ExtractedUnit {
            name: owner.map_or_else(|| name.clone(), |owner| format!("{owner}::{name}")),
            start_line: first_line(&[visibility, signature]).unwrap_or(start.line),
            end_line: close.line,
            ..ExtractedUnit::default()
        };
        for index in first..last {
            unit.normalized.push(self.normalize(index));
            unit.concrete.push(self.tokens[index].text.clone());
        }
        self.units.units.push(unit);
    }

    fn normalize(&self, index: usize) -> String {
        let token = &self.tokens[index];
        match token.kind {
            FlatKind::Identifier
                if KEYWORDS.contains(&token.text.as_str()) || self.is_call_target(index) =>
            {
                token.text.clone()
            }
            FlatKind::Identifier => PLACEHOLDER_IDENTIFIER.to_owned(),
            FlatKind::Literal => literal_placeholder(&token.text).to_owned(),
            FlatKind::Lifetime => PLACEHOLDER_LIFETIME.to_owned(),
            FlatKind::Punctuation => token.text.clone(),
        }
    }

    /// Name a called function, method, or macro: an identifier directly before `(` or `!`.
    fn is_call_target(&self, index: usize) -> bool {
        let Some(next) = self.tokens.get(index + 1) else {
            return false;
        };
        if next.kind != FlatKind::Punctuation || !CALL_SUFFIXES.contains(&next.text.as_str()) {
            return false;
        }
        index == 0 || self.tokens[index - 1].text != FUNCTION_KEYWORD
    }
}

const fn position(value: LineColumn) -> (usize, usize) {
    (value.line, value.column)
}
