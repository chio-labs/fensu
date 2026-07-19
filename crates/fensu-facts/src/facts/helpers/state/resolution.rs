//! Resolve mutation candidates against lexical scope ownership.

use std::collections::{HashMap, HashSet};

use ruff_python_ast::{Expr, ModModule, Stmt};
use ruff_text_size::{Ranged, TextRange};

use crate::facts::helpers::metrics::mutations::{attribute_root_name, is_mutator_call};
use crate::facts::helpers::shape::breadth::{breadth_first_from, breadth_first_with_parents};
use crate::facts::helpers::shape::nodes::ShapeNode;
use crate::facts::helpers::state::scopes::{
    argument_names, function_local_bindings, scope_metadata,
};

pub(crate) fn outer_mutation_ranges(module: &ModModule) -> Vec<TextRange> {
    let (nodes, parents) = breadth_first_with_parents(module);
    let module_bindings: HashSet<&str> = scope_metadata(&module.body, false).bindings;
    let declarations_present = nodes
        .iter()
        .any(|node| matches!(node, ShapeNode::Stmt(Stmt::Global(_) | Stmt::Nonlocal(_))));
    let mut resolver = Resolver {
        nodes: &nodes,
        parents: &parents,
        module_bindings,
        local_cache: HashMap::new(),
        enclosing_cache: HashMap::new(),
    };
    let mut ranges: Vec<TextRange> = Vec::new();
    for candidate in candidate_positions(&nodes, declarations_present) {
        if let Some(range) = resolver.resolve(candidate) {
            ranges.push(range);
        }
    }
    ranges
}

struct LocalScope<'a> {
    bindings: HashSet<&'a str>,
    global_names: HashSet<&'a str>,
    nonlocal_names: HashSet<&'a str>,
}

struct Resolver<'a, 'b> {
    nodes: &'b [ShapeNode<'a>],
    parents: &'b [Option<usize>],
    module_bindings: HashSet<&'a str>,
    local_cache: HashMap<usize, LocalScope<'a>>,
    enclosing_cache: HashMap<usize, HashSet<&'a str>>,
}

impl<'a> Resolver<'a, '_> {
    fn resolve(&mut self, candidate: usize) -> Option<TextRange> {
        let owner = self.owning_function(candidate)?;
        if !self.inside_owned_body(candidate, owner) {
            return None;
        }
        self.ensure_local_scope(owner);
        self.ensure_enclosing(owner);
        let shadowed = self.comprehension_bindings(candidate, owner);
        let scope = self.local_cache.get(&owner)?;
        let enclosing = self.enclosing_cache.get(&owner)?;
        let mut outer: HashSet<&'a str> = self.module_bindings.clone();
        outer.extend(enclosing);
        outer_mutation(
            &self.nodes[candidate],
            &scope.bindings,
            &outer,
            &scope.global_names,
            &scope.nonlocal_names,
            &shadowed,
        )
    }

    fn owning_function(&self, candidate: usize) -> Option<usize> {
        let mut current = self.parents[candidate];
        while let Some(position) = current {
            match &self.nodes[position] {
                ShapeNode::Stmt(Stmt::FunctionDef(_)) | ShapeNode::Expr(Expr::Lambda(_)) => {
                    return Some(position);
                }
                ShapeNode::Stmt(Stmt::ClassDef(_)) => return None,
                _ => {}
            }
            current = self.parents[position];
        }
        None
    }

    fn inside_owned_body(&self, candidate: usize, owner: usize) -> bool {
        let mut current = candidate;
        while let Some(parent) = self.parents[current] {
            if parent == owner {
                break;
            }
            current = parent;
        }
        if self.parents[current] != Some(owner) {
            return false;
        }
        match (&self.nodes[owner], &self.nodes[current]) {
            (ShapeNode::Expr(Expr::Lambda(lambda)), ShapeNode::Expr(child)) => {
                std::ptr::eq::<Expr>(&*lambda.body, *child)
            }
            (ShapeNode::Stmt(Stmt::FunctionDef(function)), ShapeNode::Stmt(child)) => function
                .body
                .iter()
                .any(|statement| std::ptr::eq(statement, *child)),
            _ => false,
        }
    }

    fn ensure_local_scope(&mut self, owner: usize) {
        if self.local_cache.contains_key(&owner) {
            return;
        }
        let scope = match &self.nodes[owner] {
            ShapeNode::Expr(Expr::Lambda(lambda)) => LocalScope {
                bindings: lambda
                    .parameters
                    .as_deref()
                    .map(argument_names)
                    .unwrap_or_default(),
                global_names: HashSet::new(),
                nonlocal_names: HashSet::new(),
            },
            ShapeNode::Stmt(Stmt::FunctionDef(function)) => {
                let metadata = function_local_bindings(function);
                LocalScope {
                    bindings: metadata.bindings,
                    global_names: metadata.global_names,
                    nonlocal_names: metadata.nonlocal_names,
                }
            }
            _ => LocalScope {
                bindings: HashSet::new(),
                global_names: HashSet::new(),
                nonlocal_names: HashSet::new(),
            },
        };
        self.local_cache.insert(owner, scope);
    }

    fn ensure_enclosing(&mut self, owner: usize) {
        if self.enclosing_cache.contains_key(&owner) {
            return;
        }
        let mut bindings: HashSet<&'a str> = HashSet::new();
        let mut current = self.parents[owner];
        while let Some(position) = current {
            if matches!(
                &self.nodes[position],
                ShapeNode::Stmt(Stmt::FunctionDef(_)) | ShapeNode::Expr(Expr::Lambda(_))
            ) {
                self.ensure_local_scope(position);
                if let Some(scope) = self.local_cache.get(&position) {
                    bindings.extend(&scope.bindings);
                }
            }
            current = self.parents[position];
        }
        self.enclosing_cache.insert(owner, bindings);
    }

    fn comprehension_bindings(&self, candidate: usize, owner: usize) -> HashSet<&'a str> {
        let mut bindings: HashSet<&'a str> = HashSet::new();
        let mut current = self.parents[candidate];
        while let Some(position) = current {
            if position == owner {
                break;
            }
            let generators = match &self.nodes[position] {
                ShapeNode::Expr(Expr::ListComp(inner)) => Some(&inner.generators),
                ShapeNode::Expr(Expr::SetComp(inner)) => Some(&inner.generators),
                ShapeNode::Expr(Expr::DictComp(inner)) => Some(&inner.generators),
                ShapeNode::Expr(Expr::Generator(inner)) => Some(&inner.generators),
                ShapeNode::GeneratorInCall(inner, _) => Some(&inner.generators),
                _ => None,
            };
            if let Some(generators) = generators {
                for generator in generators {
                    for node in breadth_first_from(ShapeNode::Expr(&generator.target)) {
                        if let ShapeNode::Expr(Expr::Name(name)) = node {
                            bindings.insert(name.id.as_str());
                        }
                    }
                }
            }
            current = self.parents[position];
        }
        bindings
    }
}

fn candidate_positions(nodes: &[ShapeNode<'_>], declarations_present: bool) -> Vec<usize> {
    let matchers: [fn(&ShapeNode<'_>) -> bool; 6] = [
        |node| matches!(node, ShapeNode::Stmt(Stmt::Assign(_))),
        |node| matches!(node, ShapeNode::Stmt(Stmt::AnnAssign(_))),
        |node| matches!(node, ShapeNode::Stmt(Stmt::AugAssign(_))),
        |node| matches!(node, ShapeNode::Expr(Expr::Named(_))),
        |node| matches!(node, ShapeNode::Stmt(Stmt::Delete(_))),
        |node| matches!(node, ShapeNode::Expr(Expr::Call(_))),
    ];
    let mut candidates: Vec<usize> = Vec::new();
    for matcher in matchers {
        for (position, node) in nodes.iter().enumerate() {
            if !matcher(node) {
                continue;
            }
            if let ShapeNode::Expr(Expr::Call(call)) = node {
                if !is_mutator_call(call) {
                    continue;
                }
            }
            if declarations_present || can_mutate_without_declaration(node) {
                candidates.push(position);
            }
        }
    }
    candidates
}

fn can_mutate_without_declaration(node: &ShapeNode<'_>) -> bool {
    if matches!(node, ShapeNode::Expr(Expr::Call(_))) {
        return true;
    }
    mutation_targets(node)
        .iter()
        .any(|target| !matches!(target, Expr::Name(_)))
}

fn mutation_targets<'a>(node: &ShapeNode<'a>) -> Vec<&'a Expr> {
    match node {
        ShapeNode::Stmt(Stmt::Assign(inner)) => inner.targets.iter().collect(),
        ShapeNode::Stmt(Stmt::AnnAssign(inner)) => vec![&inner.target],
        ShapeNode::Stmt(Stmt::AugAssign(inner)) => vec![&inner.target],
        ShapeNode::Expr(Expr::Named(inner)) => vec![&inner.target],
        ShapeNode::Stmt(Stmt::Delete(inner)) => inner.targets.iter().collect(),
        _ => Vec::new(),
    }
}

fn outer_mutation(
    node: &ShapeNode<'_>,
    local_bindings: &HashSet<&str>,
    outer_bindings: &HashSet<&str>,
    global_names: &HashSet<&str>,
    nonlocal_names: &HashSet<&str>,
    shadowed_names: &HashSet<&str>,
) -> Option<TextRange> {
    for target in mutation_targets(node) {
        let name = match target {
            Expr::Name(inner) => Some(inner.id.as_str()),
            _ => attribute_root_name(target),
        };
        if let Some(name) = name {
            if name_resolves_outer(
                name,
                matches!(target, Expr::Name(_)),
                local_bindings,
                outer_bindings,
                global_names,
                nonlocal_names,
                shadowed_names,
            ) {
                return Some(target.range());
            }
        }
    }
    if let ShapeNode::Expr(Expr::Call(call)) = node {
        if let Expr::Attribute(attribute) = &*call.func {
            if let Some(name) = attribute_root_name(&attribute.value) {
                if name_resolves_outer(
                    name,
                    false,
                    local_bindings,
                    outer_bindings,
                    global_names,
                    nonlocal_names,
                    shadowed_names,
                ) {
                    return Some(call.range());
                }
            }
        }
    }
    None
}

fn name_resolves_outer(
    name: &str,
    direct_name: bool,
    local_bindings: &HashSet<&str>,
    outer_bindings: &HashSet<&str>,
    global_names: &HashSet<&str>,
    nonlocal_names: &HashSet<&str>,
    shadowed_names: &HashSet<&str>,
) -> bool {
    if shadowed_names.contains(name) {
        return false;
    }
    if global_names.contains(name) || nonlocal_names.contains(name) {
        return true;
    }
    if direct_name || local_bindings.contains(name) {
        return false;
    }
    outer_bindings.contains(name)
}
