//! Edges are owned by execution or a declaration, never by a bare name occurrence.

use std::collections::{HashMap, HashSet};

use globset::{Glob, GlobMatcher};
use ruff_python_ast::visitor::{self, Visitor};
use ruff_python_ast::{Expr, ExprContext, Stmt};
use ruff_text_size::Ranged;

use crate::dead_code::models::{
    Analysis, Declaration, EntryPointFact, GraphFacts, Module, ProjectEntryPoint, Root,
};

const INTERNAL_KIND: &str = "local";
const ALL_BINDING: &str = "__all__";
const WILDCARD_BINDING: &str = "*";

type Bindings = HashMap<String, Option<Binding>>;

#[derive(Clone, Debug, Eq, Hash, PartialEq)]
enum Binding {
    Node(usize),
    Module(String),
    Symbol(String, String),
    Attribute(Box<Binding>, String),
    Alternatives(Vec<Binding>),
}

struct Graph<'a> {
    modules: &'a [Module],
    bindings: Vec<Bindings>,
    declarations: Vec<Declaration>,
    nodes: HashMap<(usize, String), usize>,
    edges: Vec<HashSet<usize>>,
    entrypoints: Vec<EntryPointFact>,
    registries: HashMap<usize, String>,
    aliases: HashMap<usize, Binding>,
    module_indexes: HashMap<String, usize>,
    wildcard_imports: Vec<Vec<String>>,
}

pub(crate) fn extract(modules: &[Module], entries: &[ProjectEntryPoint]) -> GraphFacts {
    let mut graph = Graph {
        modules,
        bindings: Vec::new(),
        declarations: Vec::new(),
        nodes: HashMap::new(),
        edges: Vec::new(),
        entrypoints: Vec::new(),
        registries: HashMap::new(),
        aliases: HashMap::new(),
        module_indexes: modules
            .iter()
            .enumerate()
            .map(|(index, module)| (module.name.clone(), index))
            .collect(),
        wildcard_imports: vec![Vec::new(); modules.len()],
    };
    for (index, module) in modules.iter().enumerate() {
        graph.add(index, "", "module", 0);
        let mut bindings = Bindings::new();
        Declarations {
            graph: &mut graph,
            module: index,
            bindings: &mut bindings,
            conditional: false,
        }
        .visit_body(&module.program.module().body);
        graph.bindings.push(bindings);
    }
    for (index, module) in modules.iter().enumerate() {
        let owner = graph.nodes[&(index, String::new())];
        for parent in modules.iter().filter(|parent| {
            parent.initializer && module.name.starts_with(&format!("{}.", parent.name))
        }) {
            graph.edge(owner, &Binding::Module(parent.name.clone()));
        }
        for hook in ["__getattr__", "__dir__", "__path__"] {
            graph.edge(
                owner,
                &Binding::Symbol(module.name.clone(), hook.to_owned()),
            );
        }
        let mut walker = Uses {
            graph: &mut graph,
            module: index,
            owner,
            locals: Vec::new(),
            class_scopes: HashSet::new(),
            visible_class_scope: None,
            execution_only: false,
            withheld: None,
        };
        walker.visit_body(&module.program.module().body);
    }
    for (index, module) in modules.iter().enumerate() {
        let exports = &module.program.declaration_rows().static_all_names;
        let implicit = module.package;
        if implicit || !exports.is_empty() || module.name.ends_with(".__main__") {
            let kind = if implicit {
                "package"
            } else if module.name.ends_with(".__main__") {
                "main"
            } else {
                "export"
            };
            graph.root(&Binding::Module(module.name.clone()), kind, &module.name);
        }
        let mut names = graph.bindings[index].keys().cloned().collect::<Vec<_>>();
        names.extend(exports.iter().cloned());
        if implicit {
            for imported in &graph.wildcard_imports[index] {
                if let Some(imported_index) = graph.module_indexes.get(imported) {
                    names.extend(graph.export_names(*imported_index));
                }
            }
        }
        for name in names {
            if exports.contains(&name) || implicit && !name.starts_with('_') {
                graph.root(
                    &Binding::Symbol(module.name.clone(), name.clone()),
                    "export",
                    &format!("{}:{name}", module.name),
                );
            }
        }
    }
    for entry in entries {
        let text = entry
            .reference
            .split_whitespace()
            .next()
            .unwrap_or_default();
        let reference = match text.split_once(':') {
            Some((module, symbol)) => symbol
                .split('.')
                .fold(Binding::Module(module.to_owned()), |base, name| {
                    Binding::Attribute(Box::new(base), name.to_owned())
                }),
            None => Binding::Module(text.to_owned()),
        };
        graph.root(&reference, &entry.kind, &entry.reference);
    }
    let mut references: Vec<(usize, usize)> = Vec::new();
    for (source, targets) in graph.edges.into_iter().enumerate() {
        for target in targets {
            references.push((source, target));
        }
    }
    references.sort_unstable();
    GraphFacts {
        modules: modules.iter().map(|module| module.name.clone()).collect(),
        declarations: graph.declarations,
        references,
        entrypoints: graph.entrypoints,
    }
}

pub(crate) fn analyze(
    modules: &[Module],
    entries: &[ProjectEntryPoint],
    roots: &[Root],
) -> Analysis {
    let facts = extract(modules, entries);
    let (dead, stale_roots) = evaluate_graph(&facts, roots);
    Analysis {
        dead: dead
            .into_iter()
            .map(|index| facts.declarations[index].clone())
            .collect(),
        stale_roots,
    }
}

pub(crate) fn evaluate_graph(facts: &GraphFacts, roots: &[Root]) -> (Vec<usize>, Vec<usize>) {
    let mut reachable_roots = facts
        .entrypoints
        .iter()
        .filter_map(|entry| entry.node)
        .collect::<HashSet<_>>();
    let mut stale_roots: Vec<usize> = Vec::new();
    for (index, root) in roots.iter().enumerate() {
        let module_patterns = compile_patterns(&root.modules);
        let symbol_patterns = compile_patterns(&root.symbols);
        let matches = facts
            .declarations
            .iter()
            .enumerate()
            .filter_map(|(node, declaration)| {
                (!declaration.name.is_empty()
                    && declaration.kind != INTERNAL_KIND
                    && matches_patterns(&module_patterns, &facts.modules[declaration.module])
                    && matches_patterns(&symbol_patterns, &declaration.name))
                .then_some(node)
            })
            .collect::<Vec<_>>();
        if matches.is_empty() {
            stale_roots.push(index);
        }
        reachable_roots.extend(matches);
    }
    let mut adjacency: HashMap<usize, Vec<usize>> = HashMap::new();
    for &(source, target) in &facts.references {
        adjacency.entry(source).or_default().push(target);
    }
    let mut live: HashSet<usize> = HashSet::new();
    let mut pending = reachable_roots.into_iter().collect::<Vec<_>>();
    while let Some(node) = pending.pop() {
        if live.insert(node) {
            if let Some(targets) = adjacency.get(&node) {
                pending.extend(targets.iter().copied());
            }
        }
    }
    let dead: Vec<usize> = facts
        .declarations
        .iter()
        .enumerate()
        .filter_map(|(node, declaration)| {
            (!live.contains(&node) && declaration.kind != INTERNAL_KIND).then_some(node)
        })
        .collect();
    (dead, stale_roots)
}

fn compile_patterns(patterns: &[String]) -> Vec<GlobMatcher> {
    let mut compiled: Vec<GlobMatcher> = Vec::new();
    for pattern in patterns {
        match Glob::new(pattern) {
            Ok(glob) => compiled.push(glob.compile_matcher()),
            Err(_) => return Vec::new(),
        }
    }
    compiled
}

fn matches_patterns(patterns: &[GlobMatcher], value: &str) -> bool {
    patterns.iter().any(|pattern| pattern.is_match(value))
}

impl Graph<'_> {
    fn export_names(&self, module: usize) -> HashSet<String> {
        let mut names: HashSet<String> = HashSet::new();
        let mut seen: HashSet<usize> = HashSet::new();
        let mut pending: Vec<usize> = vec![module];
        while let Some(current) = pending.pop() {
            if !seen.insert(current) {
                continue;
            }
            let is_root = current == module;
            let program = &self.modules[current].program;
            if program.module().body.iter().any(declares_all) {
                names.extend(
                    program
                        .declaration_rows()
                        .static_all_names
                        .iter()
                        .filter(|name| is_root || !name.starts_with('_'))
                        .cloned(),
                );
                continue;
            }
            names.extend(
                self.bindings[current]
                    .keys()
                    .filter(|name| !name.starts_with('_'))
                    .cloned(),
            );
            pending.extend(
                self.wildcard_imports[current]
                    .iter()
                    .filter_map(|imported| self.module_indexes.get(imported))
                    .copied(),
            );
        }
        names
    }

    fn add(&mut self, module: usize, name: &str, kind: &'static str, offset: usize) -> usize {
        let key = (module, name.to_owned());
        if let Some(node) = self.nodes.get(&key) {
            return *node;
        }
        let node = self.declarations.len();
        let position = self.modules[module].program.index().locate(offset);
        self.declarations.push(Declaration {
            module,
            name: name.to_owned(),
            kind,
            line: position.line,
            column: position.column,
        });
        self.edges.push(HashSet::new());
        self.nodes.insert(key, node);
        if !name.is_empty() {
            let execution = self.nodes[&(module, String::new())];
            self.edges[node].insert(execution);
        }
        node
    }

    fn declare(
        &mut self,
        module: usize,
        statement: &Stmt,
        mut bindings: Bindings,
        conditional: bool,
    ) -> Bindings {
        let previous = conditional.then(|| bindings.clone());
        let declaration = match statement {
            Stmt::FunctionDef(value) => Some((value.name.as_str(), "function")),
            Stmt::ClassDef(value) => Some((value.name.as_str(), "class")),
            Stmt::Assign(value) => {
                for target in &value.targets {
                    if let Expr::Name(name) = target {
                        if name.id.as_str() != ALL_BINDING {
                            let node = self.add(
                                module,
                                name.id.as_str(),
                                "constant",
                                statement.start().to_usize(),
                            );
                            self.register_constructor(node, &value.value, &bindings);
                            bindings.insert(name.id.to_string(), Some(Binding::Node(node)));
                        }
                    }
                }
                None
            }
            Stmt::AnnAssign(value) => {
                if let Expr::Name(name) = &*value.target {
                    Some((name.id.as_str(), "constant"))
                } else {
                    None
                }
            }
            _ => None,
        };
        if let Some((name, kind)) = declaration {
            let node = self.add(module, name, kind, statement.start().to_usize());
            match statement {
                Stmt::AnnAssign(value) => {
                    if let Some(value) = &value.value {
                        self.register_constructor(node, value, &bindings);
                    }
                }
                Stmt::FunctionDef(value) => {
                    for decorator in &value.decorator_list {
                        let expression = match &decorator.expression {
                            Expr::Call(call) => &*call.func,
                            expression => expression,
                        };
                        if static_reference(expression, &bindings)
                            .as_ref()
                            .and_then(reference_path)
                            .as_deref()
                            == Some("click.group")
                        {
                            self.registries.insert(node, "click.Group".to_owned());
                        }
                    }
                }
                _ => {}
            }
            bindings.insert(name.to_owned(), Some(Binding::Node(node)));
        }
        bindings = import_bindings(
            statement,
            &self.modules[module].name,
            self.modules[module].initializer,
            bindings,
        );
        if let Stmt::ImportFrom(value) = statement {
            if value
                .names
                .iter()
                .any(|name| name.name.as_str() == WILDCARD_BINDING)
            {
                let base = import_base(
                    &self.modules[module].name,
                    value.level,
                    value.module.as_ref().map(|name| name.as_str()),
                    self.modules[module].initializer,
                );
                self.wildcard_imports[module].push(base);
                bindings.remove("*");
            }
        }
        if let Some(previous) = previous {
            for (name, binding) in bindings.iter_mut() {
                let Some(current) = binding.clone() else {
                    continue;
                };
                let Some(Some(old)) = previous.get(name) else {
                    continue;
                };
                if old == &current {
                    continue;
                }
                let mut choices = match old {
                    Binding::Alternatives(values) => values.clone(),
                    value => vec![value.clone()],
                };
                let additional = match current {
                    Binding::Alternatives(values) => values,
                    value => vec![value],
                };
                for value in additional {
                    if !choices.contains(&value) {
                        choices.push(value);
                    }
                }
                *binding = Some(Binding::Alternatives(choices));
            }
        }
        bindings
    }

    fn register_constructor(&mut self, node: usize, value: &Expr, bindings: &Bindings) {
        if let Some(reference) = static_reference(value, bindings) {
            self.aliases.insert(node, reference);
        }
        let Expr::Call(call) = value else {
            return;
        };
        if static_reference(&call.func, bindings)
            .as_ref()
            .and_then(reference_path)
            .as_deref()
            == Some("importlib.import_module")
        {
            if let Some(Expr::StringLiteral(module)) = call.arguments.args.first() {
                self.aliases
                    .insert(node, Binding::Module(module.value.to_str().to_owned()));
            }
        }
        if let Some(kind) = static_reference(&call.func, bindings)
            .as_ref()
            .and_then(reference_path)
            .filter(|kind| {
                matches!(
                    kind.as_str(),
                    "fastapi.FastAPI"
                        | "fastapi.APIRouter"
                        | "flask.Flask"
                        | "flask.Blueprint"
                        | "typer.Typer"
                        | "click.Group"
                )
            })
        {
            self.registries.insert(node, kind);
        }
    }

    fn resolve(&self, reference: &Binding, seen: HashSet<Binding>) -> Option<usize> {
        self.resolve_all(reference, seen).into_iter().next()
    }

    fn resolve_all(&self, reference: &Binding, seen: HashSet<Binding>) -> Vec<usize> {
        self.resolve_bindings(reference, seen)
            .into_iter()
            .filter_map(|binding| match binding {
                Binding::Node(node) => Some(node),
                Binding::Module(module) => self
                    .module_indexes
                    .get(&module)
                    .and_then(|index| self.nodes.get(&(*index, String::new())))
                    .copied(),
                _ => None,
            })
            .collect()
    }

    fn resolve_bindings(&self, reference: &Binding, mut seen: HashSet<Binding>) -> Vec<Binding> {
        if !seen.insert(reference.clone()) {
            return Vec::new();
        }
        match reference {
            Binding::Node(_) | Binding::Module(_) => vec![reference.clone()],
            Binding::Symbol(module, name) => self
                .lookup(module, name)
                .iter()
                .flat_map(|binding| self.resolve_bindings(binding, seen.clone()))
                .collect(),
            Binding::Attribute(base, name) => {
                let bases = self.resolve_bindings(base, seen.clone());
                let mut resolved: Vec<Binding> = Vec::new();
                for base in bases {
                    match base {
                        Binding::Module(module) => resolved.extend(self.resolve_bindings(
                            &Binding::Symbol(module, name.clone()),
                            seen.clone(),
                        )),
                        Binding::Node(node) => {
                            resolved.push(base);
                            if let Some(alias) = self.aliases.get(&node) {
                                resolved.extend(self.resolve_bindings(
                                    &Binding::Attribute(Box::new(alias.clone()), name.clone()),
                                    seen.clone(),
                                ));
                            }
                        }
                        _ => {}
                    }
                }
                resolved
            }
            Binding::Alternatives(values) => values
                .iter()
                .flat_map(|binding| self.resolve_bindings(binding, seen.clone()))
                .collect(),
        }
    }

    fn lookup(&self, module: &str, name: &str) -> Vec<Binding> {
        let Some(index) = self.module_indexes.get(module) else {
            return Vec::new();
        };
        if let Some(binding) = self.bindings[*index].get(name) {
            return binding.clone().into_iter().collect();
        }
        let mut values = self.wildcard_imports[*index]
            .iter()
            .filter(|imported| {
                self.module_indexes
                    .get(*imported)
                    .is_some_and(|index| self.export_names(*index).contains(name))
            })
            .map(|imported| Binding::Symbol(imported.clone(), name.to_owned()))
            .collect::<Vec<_>>();
        let child = format!("{module}.{name}");
        if self.module_indexes.contains_key(&child) {
            values.push(Binding::Module(child));
        }
        values
    }

    fn edge(&mut self, owner: usize, reference: &Binding) {
        let targets = self.resolve_all(reference, HashSet::new());
        self.edges[owner].extend(targets);
    }

    fn root(&mut self, reference: &Binding, kind: &str, label: &str) {
        let targets = self.resolve_all(reference, HashSet::new());
        if targets.is_empty() {
            self.entrypoints.push(EntryPointFact {
                node: None,
                kind: kind.to_owned(),
                reference: label.to_owned(),
            });
        }
        for target in targets {
            self.entrypoints.push(EntryPointFact {
                node: Some(target),
                kind: kind.to_owned(),
                reference: label.to_owned(),
            });
        }
    }
}

struct Declarations<'a, 'm> {
    graph: &'a mut Graph<'m>,
    module: usize,
    bindings: &'a mut Bindings,
    conditional: bool,
}

fn declares_all(statement: &Stmt) -> bool {
    match statement {
        Stmt::Assign(value) => value
            .targets
            .iter()
            .any(|target| matches!(target, Expr::Name(name) if name.id.as_str() == ALL_BINDING)),
        Stmt::AnnAssign(value) => {
            value.value.is_some()
                && matches!(&*value.target, Expr::Name(name) if name.id.as_str() == ALL_BINDING)
        }
        _ => false,
    }
}

fn static_reference(expression: &Expr, bindings: &Bindings) -> Option<Binding> {
    match expression {
        Expr::Name(name) => bindings.get(name.id.as_str()).cloned().flatten(),
        Expr::Attribute(attribute) => Some(Binding::Attribute(
            Box::new(static_reference(&attribute.value, bindings)?),
            attribute.attr.to_string(),
        )),
        _ => None,
    }
}

fn reference_path(reference: &Binding) -> Option<String> {
    match reference {
        Binding::Module(module) => Some(module.clone()),
        Binding::Symbol(module, name) => Some(format!("{module}.{name}")),
        Binding::Attribute(base, name) => Some(format!("{}.{name}", reference_path(base)?)),
        _ => None,
    }
}

impl<'a> Visitor<'a> for Declarations<'_, '_> {
    fn visit_stmt(&mut self, statement: &'a Stmt) {
        let bindings = std::mem::take(self.bindings);
        *self.bindings = self
            .graph
            .declare(self.module, statement, bindings, self.conditional);
        if !matches!(
            statement,
            Stmt::FunctionDef(_)
                | Stmt::ClassDef(_)
                | Stmt::Assign(_)
                | Stmt::AnnAssign(_)
                | Stmt::Import(_)
                | Stmt::ImportFrom(_)
        ) {
            let previous = self.conditional;
            self.conditional = true;
            visitor::walk_stmt(self, statement);
            self.conditional = previous;
        }
    }
}

fn import_bindings(
    statement: &Stmt,
    module: &str,
    initializer: bool,
    mut bindings: Bindings,
) -> Bindings {
    match statement {
        Stmt::Import(value) => {
            for alias in &value.names {
                let (bound, target) = match &alias.asname {
                    Some(name) => (name.as_str(), alias.name.as_str()),
                    None => {
                        let first = alias.name.as_str().split('.').next().unwrap_or_default();
                        (first, first)
                    }
                };
                bindings.insert(bound.to_owned(), Some(Binding::Module(target.to_owned())));
            }
        }
        Stmt::ImportFrom(value) => {
            let base = import_base(
                module,
                value.level,
                value.module.as_ref().map(|name| name.as_str()),
                initializer,
            );
            for alias in &value.names {
                let bound = alias.asname.as_ref().unwrap_or(&alias.name).to_string();
                let reference = if base == module && bound == alias.name.as_str() {
                    bindings
                        .get(&bound)
                        .cloned()
                        .flatten()
                        .unwrap_or_else(|| Binding::Module(format!("{base}.{}", alias.name)))
                } else {
                    Binding::Symbol(base.clone(), alias.name.to_string())
                };
                bindings.insert(bound, Some(reference));
            }
        }
        _ => {}
    }
    bindings
}

fn import_base(module: &str, level: u32, imported: Option<&str>, initializer: bool) -> String {
    if level == 0 {
        return imported.unwrap_or_default().to_owned();
    }
    let mut parts = module.split('.').collect::<Vec<_>>();
    let drop = level.saturating_sub(u32::from(initializer));
    for _ in 0..drop {
        parts.pop();
    }
    if let Some(imported) = imported {
        parts.extend(imported.split('.'));
    }
    parts.join(".")
}

struct Uses<'a, 'm> {
    graph: &'a mut Graph<'m>,
    module: usize,
    owner: usize,
    locals: Vec<Bindings>,
    class_scopes: HashSet<usize>,
    visible_class_scope: Option<usize>,
    execution_only: bool,
    withheld: Option<usize>,
}

impl Uses<'_, '_> {
    fn name(&self, name: &str) -> Option<Binding> {
        for (index, locals) in self.locals.iter().enumerate().rev() {
            if self.class_scopes.contains(&index) && Some(index) != self.visible_class_scope {
                continue;
            }
            if let Some(binding) = locals.get(name) {
                return binding.clone();
            }
        }
        self.graph.bindings[self.module]
            .get(name)
            .cloned()
            .flatten()
            .or_else(|| {
                (!self.graph.wildcard_imports[self.module].is_empty()).then(|| {
                    Binding::Symbol(
                        self.graph.modules[self.module].name.clone(),
                        name.to_owned(),
                    )
                })
            })
    }

    fn reference(&self, expression: &Expr) -> Option<Binding> {
        match expression {
            Expr::Name(value) => self.name(value.id.as_str()),
            Expr::Attribute(value) => Some(Binding::Attribute(
                Box::new(self.reference(&value.value)?),
                value.attr.to_string(),
            )),
            Expr::Call(value)
                if self
                    .reference(&value.func)
                    .as_ref()
                    .and_then(reference_path)
                    .as_deref()
                    == Some("importlib.import_module") =>
            {
                match value.arguments.args.first()? {
                    Expr::StringLiteral(value) if !value.value.to_str().starts_with('.') => {
                        Some(Binding::Module(value.value.to_str().to_owned()))
                    }
                    _ => None,
                }
            }
            _ => None,
        }
    }

    fn definition_owner(&self, name: &str) -> usize {
        if self.locals.is_empty() {
            self.graph
                .nodes
                .get(&(self.module, name.to_owned()))
                .copied()
                .unwrap_or(self.owner)
        } else {
            self.locals
                .last()
                .and_then(|bindings| bindings.get(name))
                .and_then(Option::as_ref)
                .and_then(|binding| self.graph.resolve(binding, HashSet::new()))
                .unwrap_or(self.owner)
        }
    }
}

impl Uses<'_, '_> {
    fn annotation_uses(&mut self, expression: &Expr) {
        if let Expr::StringLiteral(value) = expression {
            if let Ok(parsed) =
                crate::parsing::main::parse_expression_strict::parse_expression_strict(
                    value.value.to_str(),
                    self.graph.modules[self.module].program.version(),
                )
            {
                let mut walker = Uses {
                    graph: self.graph,
                    module: self.module,
                    owner: self.owner,
                    locals: self.locals.clone(),
                    class_scopes: self.class_scopes.clone(),
                    visible_class_scope: self.visible_class_scope,
                    execution_only: self.execution_only,
                    withheld: self.withheld,
                };
                walker.visit_expr(&parsed.syntax().body);
            }
        } else {
            self.visit_expr(expression);
        }
    }

    fn function_uses(&mut self, value: &ruff_python_ast::StmtFunctionDef) {
        let previous = self.owner;
        let owner = self.definition_owner(value.name.as_str());
        let previous_withheld = self.withheld;
        self.withheld = self.withheld.or(Some(owner));
        for decorator in &value.decorator_list {
            let callable = match &decorator.expression {
                Expr::Call(call) => &*call.func,
                expression => expression,
            };
            let reference = self.reference(callable);
            if reference.as_ref().and_then(reference_path).as_deref() == Some("atexit.register") {
                self.graph.edges[previous].insert(owner);
            }
            if let Some(Binding::Attribute(base, method)) = &reference {
                if let Some(registry) = self.graph.resolve(base, HashSet::new()) {
                    if self
                        .graph
                        .registries
                        .get(&registry)
                        .is_some_and(|kind| registration_method(kind, method))
                    {
                        self.graph.edges[registry].insert(owner);
                    }
                }
            }
            self.visit_decorator(decorator);
        }
        self.visit_parameters(&value.parameters);
        if let Some(returns) = &value.returns {
            self.visit_annotation(returns);
        }
        self.withheld = previous_withheld;
        if self.execution_only {
            return;
        }
        self.owner = owner;
        let mut locals = LocalBindings::default();
        locals.visit_body(&value.body);
        for name in &locals.outer_bindings {
            locals.values.remove(name);
        }
        for (name, offset) in &locals.definitions {
            let hidden = format!("<locals>:{offset}");
            let node = self.graph.add(self.module, &hidden, INTERNAL_KIND, *offset);
            let parent = &self.graph.declarations[owner];
            let qualifier = match parent.kind {
                "class" => format!("{}.{}", parent.name, value.name),
                _ => parent.name.clone(),
            };
            self.graph.declarations[node].name = format!("{qualifier}.<locals>.{name}");
            locals
                .values
                .insert(name.clone(), Some(Binding::Node(node)));
        }
        for parameter in value.parameters.iter() {
            locals.values.insert(parameter.name().to_string(), None);
        }
        self.locals.push(locals.values);
        let previous_class_scope = self.visible_class_scope.take();
        self.visit_body(&value.body);
        self.visible_class_scope = previous_class_scope;
        self.locals.pop();
        self.owner = previous;
    }

    fn class_uses(&mut self, value: &ruff_python_ast::StmtClassDef) {
        let previous = self.owner;
        let declaration = self.definition_owner(value.name.as_str());
        let previous_withheld = self.withheld;
        self.withheld = self.withheld.or(Some(declaration));
        for decorator in &value.decorator_list {
            self.visit_decorator(decorator);
        }
        if let Some(arguments) = &value.arguments {
            self.visit_arguments(arguments);
        }
        let previous_execution = self.execution_only;
        self.execution_only = true;
        let previous_class_scope = self.visible_class_scope;
        self.visible_class_scope = Some(self.locals.len());
        self.class_scopes.insert(self.locals.len());
        self.locals.push(Bindings::new());
        self.visit_body(&value.body);
        self.locals.pop();
        self.class_scopes.remove(&self.locals.len());
        self.visible_class_scope = previous_class_scope;
        self.execution_only = previous_execution;
        self.withheld = previous_withheld;
        if previous_execution {
            return;
        }
        self.owner = declaration;
        self.visible_class_scope = Some(self.locals.len());
        self.class_scopes.insert(self.locals.len());
        self.locals.push(Bindings::new());
        self.visit_body(&value.body);
        self.locals.pop();
        self.class_scopes.remove(&self.locals.len());
        self.visible_class_scope = previous_class_scope;
        self.owner = previous;
    }

    fn assignment_uses(&mut self, value: &ruff_python_ast::StmtAssign) {
        let previous = self.owner;
        for target in &value.targets {
            if let Expr::Name(name) = target {
                if name.id.as_str() == ALL_BINDING {
                    self.execution_only = true;
                    self.visit_expr(&value.value);
                    self.execution_only = false;
                    continue;
                }
                let declaration = self.definition_owner(name.id.as_str());
                self.execution_only = true;
                self.withheld = Some(declaration);
                self.visit_expr(&value.value);
                self.withheld = None;
                self.execution_only = false;
                self.owner = declaration;
                self.visit_expr(&value.value);
                self.owner = previous;
            } else {
                self.execution_only = true;
                self.visit_expr(&value.value);
                self.assignment_target_uses(target);
                self.execution_only = false;
            }
        }
        self.owner = previous;
    }

    fn local_assignment_uses(&mut self, value: &ruff_python_ast::StmtAssign) {
        self.visit_expr(&value.value);
        let reference = self.reference(&value.value);
        for target in &value.targets {
            if let Expr::Name(name) = target {
                if let Some(locals) = self.locals.last_mut() {
                    locals.insert(name.id.to_string(), reference.clone());
                }
            } else {
                self.visit_expr(target);
            }
        }
    }

    fn annotated_assignment_uses(&mut self, value: &ruff_python_ast::StmtAnnAssign) {
        let previous = self.owner;
        self.assignment_target_uses(&value.target);
        let declaration = if let Expr::Name(name) = &*value.target {
            self.definition_owner(name.id.as_str())
        } else {
            previous
        };
        self.execution_only = true;
        self.withheld = Some(declaration);
        self.visit_annotation(&value.annotation);
        if let Some(value) = &value.value {
            self.visit_expr(value);
        }
        self.withheld = None;
        self.execution_only = false;
        self.owner = declaration;
        self.visit_annotation(&value.annotation);
        if let Some(value) = &value.value {
            self.visit_expr(value);
        }
        self.owner = previous;
    }

    fn assignment_target_uses(&mut self, target: &Expr) {
        match target {
            Expr::Attribute(value) => self.visit_expr(&value.value),
            Expr::Subscript(value) => {
                self.visit_expr(&value.value);
                self.visit_expr(&value.slice);
            }
            Expr::Tuple(value) => {
                for target in &value.elts {
                    self.assignment_target_uses(target);
                }
            }
            Expr::List(value) => {
                for target in &value.elts {
                    self.assignment_target_uses(target);
                }
            }
            Expr::Starred(value) => self.assignment_target_uses(&value.value),
            _ => {}
        }
    }
}

impl<'a> Visitor<'a> for Uses<'_, '_> {
    fn visit_annotation(&mut self, expression: &'a Expr) {
        self.annotation_uses(expression);
    }

    fn visit_stmt(&mut self, statement: &'a Stmt) {
        match statement {
            Stmt::FunctionDef(value) => self.function_uses(value),
            Stmt::ClassDef(value) => self.class_uses(value),
            Stmt::Assign(value) if self.locals.is_empty() => self.assignment_uses(value),
            Stmt::Assign(value) => self.local_assignment_uses(value),
            Stmt::AnnAssign(value) if self.locals.is_empty() => {
                self.annotated_assignment_uses(value)
            }
            Stmt::AugAssign(value) => {
                if let Some(reference) = self.reference(&value.target) {
                    self.graph.edge(self.owner, &reference);
                }
                visitor::walk_stmt(self, statement);
            }
            Stmt::Import(value) => {
                for alias in &value.names {
                    self.graph
                        .edge(self.owner, &Binding::Module(alias.name.to_string()));
                }
                self.bind_import(statement);
            }
            Stmt::ImportFrom(value) => {
                let module = &self.graph.modules[self.module];
                let base = import_base(
                    &module.name,
                    value.level,
                    value.module.as_ref().map(|name| name.as_str()),
                    module.initializer,
                );
                self.graph.edge(self.owner, &Binding::Module(base.clone()));
                for alias in &value.names {
                    let child = format!("{base}.{}", alias.name);
                    let bound = self.graph.module_indexes.get(&base).is_some_and(|index| {
                        self.graph.bindings[*index].contains_key(alias.name.as_str())
                    });
                    if !bound && self.graph.module_indexes.contains_key(&child) {
                        self.graph.edge(self.owner, &Binding::Module(child));
                    } else if let Some(index) = self.graph.module_indexes.get(&base) {
                        if let Some(Some(Binding::Module(imported))) =
                            self.graph.bindings[*index].get(alias.name.as_str())
                        {
                            let imported = imported.clone();
                            self.graph.edge(self.owner, &Binding::Module(imported));
                        }
                    }
                }
                self.bind_import(statement);
            }
            _ => visitor::walk_stmt(self, statement),
        }
    }

    fn visit_expr(&mut self, expression: &'a Expr) {
        if let Expr::Lambda(value) = expression {
            let mut locals = Bindings::new();
            if let Some(parameters) = &value.parameters {
                self.visit_parameters(parameters);
                for parameter in parameters.iter() {
                    locals.insert(parameter.name().to_string(), None);
                }
            }
            if !self.execution_only {
                let previous_class_scope = self.visible_class_scope.take();
                self.locals.push(locals);
                self.visit_expr(&value.body);
                self.locals.pop();
                self.visible_class_scope = previous_class_scope;
            }
            return;
        }
        if let Expr::Name(value) = expression {
            if value.ctx != ExprContext::Load {
                return;
            }
        }
        if let Some(reference) = self.reference(expression) {
            for target in self.graph.resolve_all(&reference, HashSet::new()) {
                if Some(target) != self.withheld {
                    self.graph.edges[self.owner].insert(target);
                }
            }
        }
        let comprehension = matches!(
            expression,
            Expr::ListComp(_) | Expr::SetComp(_) | Expr::DictComp(_) | Expr::Generator(_)
        );
        if comprehension {
            self.locals.push(Bindings::new());
        }
        visitor::walk_expr(self, expression);
        if comprehension {
            self.locals.pop();
        }
    }

    fn visit_comprehension(&mut self, comprehension: &'a ruff_python_ast::Comprehension) {
        self.visit_expr(&comprehension.iter);
        let mut bindings = LocalBindings::default();
        bindings.visit_expr(&comprehension.target);
        if let Some(locals) = self.locals.last_mut() {
            locals.extend(bindings.values);
        }
        for condition in &comprehension.ifs {
            self.visit_expr(condition);
        }
    }
}

impl Uses<'_, '_> {
    fn bind_import(&mut self, statement: &Stmt) {
        if let Some(locals) = self.locals.last_mut() {
            let module = &self.graph.modules[self.module];
            let previous = std::mem::take(locals);
            *locals = import_bindings(statement, &module.name, module.initializer, previous);
        }
    }
}

#[derive(Default)]
struct LocalBindings {
    values: Bindings,
    definitions: Vec<(String, usize)>,
    outer_bindings: HashSet<String>,
}

fn registration_method(kind: &str, method: &str) -> bool {
    match kind {
        "fastapi.FastAPI" | "fastapi.APIRouter" => matches!(
            method,
            "get"
                | "post"
                | "put"
                | "patch"
                | "delete"
                | "head"
                | "options"
                | "websocket"
                | "api_route"
                | "on_event"
                | "exception_handler"
                | "middleware"
        ),
        "flask.Flask" | "flask.Blueprint" => matches!(
            method,
            "route"
                | "get"
                | "post"
                | "put"
                | "patch"
                | "delete"
                | "before_request"
                | "after_request"
                | "errorhandler"
        ),
        "typer.Typer" | "click.Group" => matches!(method, "command" | "callback" | "group"),
        _ => false,
    }
}

impl<'a> Visitor<'a> for LocalBindings {
    fn visit_stmt(&mut self, statement: &'a Stmt) {
        match statement {
            Stmt::Global(value) => self
                .outer_bindings
                .extend(value.names.iter().map(ToString::to_string)),
            Stmt::Nonlocal(value) => self
                .outer_bindings
                .extend(value.names.iter().map(ToString::to_string)),
            Stmt::FunctionDef(value) => {
                self.values.insert(value.name.to_string(), None);
                self.definitions
                    .push((value.name.to_string(), statement.start().to_usize()));
            }
            Stmt::ClassDef(value) => {
                self.values.insert(value.name.to_string(), None);
                self.definitions
                    .push((value.name.to_string(), statement.start().to_usize()));
            }
            _ => visitor::walk_stmt(self, statement),
        }
    }

    fn visit_expr(&mut self, expression: &'a Expr) {
        if let Expr::Name(value) = expression {
            if value.ctx != ExprContext::Load {
                self.values.insert(value.id.to_string(), None);
            }
        }
        visitor::walk_expr(self, expression);
    }
}
