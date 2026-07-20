use std::collections::{BTreeMap, BTreeSet};

use crate::mapping::helpers::identity::{build_class_key, build_function_key};
use crate::mapping::constants::{
    CLASS_RECEIVER, EXPRESSION_ATTRIBUTE, EXPRESSION_CALL, EXPRESSION_NAME, EXPRESSION_STRING,
    EXPRESSION_SUBSCRIPT, SELF_RECEIVER,
};
use crate::mapping::models::{
    CallMapEntry, CallMapNode, ClassDefinition, FunctionDefinition, MappingCall,
    MappingExpression, MappingStatement, ProjectIndex, ResolvedCallable, UnresolvedCall,
};

type MethodCache = BTreeMap<(String, String, bool), Option<FunctionDefinition>>;
type ReceiverState = BTreeMap<String, Option<String>>;

pub(crate) fn build_tree(
    root: FunctionDefinition,
    index: &ProjectIndex,
    depth: usize,
) -> CallMapNode {
    let dispatch = root
        .owning_class
        .as_deref()
        .map(|class| build_class_key(&root.module_name, class));
    build_node(
        root,
        dispatch,
        index,
        depth,
        &BTreeSet::new(),
        &mut MethodCache::new(),
    )
}

fn build_node(
    definition: FunctionDefinition,
    dispatch_class_key: Option<String>,
    index: &ProjectIndex,
    remaining_depth: usize,
    ancestors: &BTreeSet<(String, Option<String>)>,
    method_cache: &mut MethodCache,
) -> CallMapNode {
    let key = (definition.key(), dispatch_class_key.clone());
    let dispatch_class_name =
        dispatch_class_name(&definition, dispatch_class_key.as_deref(), index);
    if ancestors.contains(&key) {
        return CallMapNode {
            definition,
            entries: Vec::new(),
            dispatch_class_name,
            cycle: true,
            truncated: false,
        };
    }
    let call_entries = call_entries(
        &definition,
        dispatch_class_key.as_deref(),
        index,
        method_cache,
    );
    if remaining_depth == 0 {
        return CallMapNode {
            definition,
            entries: Vec::new(),
            dispatch_class_name,
            cycle: false,
            truncated: !call_entries.is_empty(),
        };
    }
    let mut next_ancestors = ancestors.clone();
    next_ancestors.insert(key);
    let entries = call_entries
        .into_iter()
        .map(|entry| match entry {
            PendingEntry::Unresolved(unresolved) => CallMapEntry::Unresolved(unresolved),
            PendingEntry::Resolved(target) => CallMapEntry::Node(Box::new(build_node(
                target.definition,
                target.dispatch_class_key,
                index,
                remaining_depth - 1,
                &next_ancestors,
                method_cache,
            ))),
        })
        .collect();
    CallMapNode {
        definition,
        entries,
        dispatch_class_name,
        cycle: false,
        truncated: false,
    }
}

enum PendingEntry {
    Resolved(Box<ResolvedCallable>),
    Unresolved(UnresolvedCall),
}

fn call_entries(
    definition: &FunctionDefinition,
    dispatch_class_key: Option<&str>,
    index: &ProjectIndex,
    method_cache: &mut MethodCache,
) -> Vec<PendingEntry> {
    let mut entries = Vec::new();
    let mut seen = BTreeSet::new();
    let parameter_names = parameter_names(definition);
    let untyped_parameters = untyped_parameter_names(definition);
    let receiver_states = receiver_states(definition, dispatch_class_key, index, method_cache);
    for (position, call) in definition.syntax.calls().enumerate() {
        let local_types = receiver_states.get(position).cloned().unwrap_or_default();
        if call.callee.kind == EXPRESSION_NAME && parameter_names.contains(call.callee.name()) {
            entries.push(PendingEntry::Unresolved(UnresolvedCall {
                name: call.callee.name().to_owned(),
                line: call.line,
                reason: "parameter call",
            }));
            continue;
        }
        let (target, unresolved) = resolve_call(
            call,
            definition,
            dispatch_class_key,
            index,
            &local_types,
            &untyped_parameters,
            method_cache,
        );
        if let Some(unresolved) = unresolved {
            entries.push(PendingEntry::Unresolved(unresolved));
        }
        if let Some(target) = target {
            let key = (target.definition.key(), target.dispatch_class_key.clone());
            if seen.insert(key) {
                entries.push(PendingEntry::Resolved(Box::new(target)));
            }
        }
    }
    entries
}

fn resolve_call(
    call: &MappingCall,
    definition: &FunctionDefinition,
    dispatch_class_key: Option<&str>,
    index: &ProjectIndex,
    local_types: &ReceiverState,
    untyped_parameters: &BTreeSet<String>,
    method_cache: &mut MethodCache,
) -> (Option<ResolvedCallable>, Option<UnresolvedCall>) {
    let callee = &call.callee;
    if callee.kind == EXPRESSION_NAME {
        if local_types.contains_key(callee.name()) {
            return (None, None);
        }
        let key = top_level_call_key(callee, definition);
        return (
            index
                .functions
                .get(&key)
                .cloned()
                .map(|definition| ResolvedCallable {
                    definition,
                    dispatch_class_key: None,
                }),
            None,
        );
    }
    if callee.kind != EXPRESSION_ATTRIBUTE || callee.child.is_none() {
        return (None, None);
    }
    let receiver = callee.child.as_deref().unwrap_or(callee);
    let (receiver_class, project_owned) = receiver_class(
        receiver,
        definition,
        dispatch_class_key,
        index,
        local_types,
        method_cache,
    );
    if let Some(receiver_class) = receiver_class {
        if receiver_class.protocol {
            let mut candidates = BTreeMap::new();
            for implementation_key in index
                .protocol_implementations
                .get(&receiver_class.key())
                .into_iter()
                .flatten()
            {
                let Some(implementation) = index.classes.get(implementation_key) else {
                    continue;
                };
                if let Some(method) = method_definition(
                    implementation,
                    callee.name(),
                    index,
                    method_cache,
                    &mut BTreeSet::new(),
                    true,
                ) {
                    candidates.insert(
                        (method.key(), implementation.key()),
                        ResolvedCallable {
                            definition: method,
                            dispatch_class_key: Some(implementation.key()),
                        },
                    );
                }
            }
            if candidates.len() == 1 {
                return (candidates.into_values().next(), None);
            }
            return (None, Some(unresolved(call, "protocol dispatch")));
        }
        if let Some(target) = method_definition(
            &receiver_class,
            callee.name(),
            index,
            method_cache,
            &mut BTreeSet::new(),
            false,
        ) {
            return (
                Some(ResolvedCallable {
                    definition: target,
                    dispatch_class_key: Some(receiver_class.key()),
                }),
                None,
            );
        }
        let reason = if is_direct_self(receiver) {
            "self method"
        } else {
            "dynamic attribute"
        };
        return (None, Some(unresolved(call, reason)));
    }
    let root = root_name(receiver);
    if root.is_some_and(|name| untyped_parameters.contains(name)) {
        return (None, Some(unresolved(call, "parameter method")));
    }
    if is_direct_self(receiver) {
        return (None, Some(unresolved(call, "self method")));
    }
    if project_owned {
        return (None, Some(unresolved(call, "dynamic attribute")));
    }
    if root.is_some_and(|name| local_types.contains_key(name)) {
        return (None, None);
    }
    let target = imported_module_call_key(callee, definition)
        .and_then(|key| index.functions.get(&key))
        .cloned()
        .map(|definition| ResolvedCallable {
            definition,
            dispatch_class_key: None,
        });
    (target, None)
}

fn receiver_class(
    expression: &MappingExpression,
    definition: &FunctionDefinition,
    dispatch_class_key: Option<&str>,
    index: &ProjectIndex,
    local_types: &ReceiverState,
    method_cache: &mut MethodCache,
) -> (Option<ClassDefinition>, bool) {
    if expression.kind == EXPRESSION_NAME {
        if matches!(expression.name(), SELF_RECEIVER | CLASS_RECEIVER)
            && definition.owning_class.is_some()
        {
            let key = dispatch_class_key.map(str::to_owned).unwrap_or_else(|| {
                build_class_key(
                    &definition.module_name,
                    definition.owning_class.as_deref().unwrap_or_default(),
                )
            });
            return (index.classes.get(&key).cloned(), true);
        }
        if let Some(local_key) = local_types.get(expression.name()) {
            return (
                local_key
                    .as_deref()
                    .and_then(|key| index.classes.get(key))
                    .cloned(),
                local_key.is_some(),
            );
        }
        let direct = resolve_class_expression(expression, definition, index, false);
        return (direct.clone(), direct.is_some());
    }
    let root = root_name(expression);
    let direct = if root.is_none_or(|name| !local_types.contains_key(name)) {
        resolve_class_expression(expression, definition, index, false)
    } else {
        None
    };
    if direct.is_some() {
        return (direct, true);
    }
    if expression.kind == EXPRESSION_CALL {
        if let Some(child) = expression.child.as_deref() {
            let child_root = root_name(child);
            let constructor = if child_root.is_none_or(|name| !local_types.contains_key(name)) {
                resolve_class_expression(child, definition, index, false)
            } else {
                None
            };
            if constructor.is_some() {
                return (constructor, true);
            }
            let factory = called_function(
                child,
                definition,
                dispatch_class_key,
                index,
                local_types,
                method_cache,
            );
            let Some(factory) = factory else {
                return (None, false);
            };
            let Some(returns) = &factory.syntax.returns else {
                return (None, true);
            };
            let returned = resolve_class_expression(returns, &factory, index, true);
            return (returned.clone(), returned.is_some());
        }
    }
    if expression.kind == EXPRESSION_ATTRIBUTE {
        if let Some(child) = expression.child.as_deref() {
            let (owner, project_owned) = receiver_class(
                child,
                definition,
                dispatch_class_key,
                index,
                local_types,
                method_cache,
            );
            let Some(owner) = owner else {
                return (None, project_owned);
            };
            let reference = owner
                .instance_attributes
                .get(expression.name())
                .or_else(|| owner.class_attributes.get(expression.name()));
            let Some(reference) = reference else {
                return (None, true);
            };
            let resolved = resolve_class_expression(
                &reference.expression,
                &class_as_function(&owner),
                index,
                reference.annotation,
            );
            return (resolved.clone(), resolved.is_some());
        }
    }
    (None, false)
}

fn called_function(
    callee: &MappingExpression,
    definition: &FunctionDefinition,
    dispatch_class_key: Option<&str>,
    index: &ProjectIndex,
    local_types: &ReceiverState,
    method_cache: &mut MethodCache,
) -> Option<FunctionDefinition> {
    if callee.kind == EXPRESSION_NAME {
        if local_types.contains_key(callee.name()) {
            return None;
        }
        return index
            .functions
            .get(&top_level_call_key(callee, definition))
            .cloned();
    }
    if callee.kind != EXPRESSION_ATTRIBUTE {
        return None;
    }
    let child = callee.child.as_deref()?;
    let (receiver, _) = receiver_class(
        child,
        definition,
        dispatch_class_key,
        index,
        local_types,
        method_cache,
    );
    if let Some(receiver) = receiver {
        return method_definition(
            &receiver,
            callee.name(),
            index,
            method_cache,
            &mut BTreeSet::new(),
            false,
        );
    }
    if root_name(child).is_some_and(|name| local_types.contains_key(name)) {
        return None;
    }
    imported_module_call_key(callee, definition).and_then(|key| index.functions.get(&key).cloned())
}

fn method_definition(
    class: &ClassDefinition,
    method_name: &str,
    index: &ProjectIndex,
    cache: &mut MethodCache,
    active: &mut BTreeSet<(String, String)>,
    exclude_protocol_bases: bool,
) -> Option<FunctionDefinition> {
    let cache_key = (class.key(), method_name.to_owned(), exclude_protocol_bases);
    if let Some(cached) = cache.get(&cache_key) {
        return cached.clone();
    }
    let active_key = (class.key(), method_name.to_owned());
    if !active.insert(active_key.clone()) {
        return None;
    }
    let direct_key = build_function_key(&class.module_name, method_name, Some(&class.name));
    if let Some(direct) = index.functions.get(&direct_key).cloned() {
        cache.insert(cache_key, Some(direct.clone()));
        active.remove(&active_key);
        return Some(direct);
    }
    let mut candidates = BTreeMap::new();
    for base in &class.bases {
        let owner = class_as_function(class);
        let Some(base_class) = resolve_class_expression(base, &owner, index, false) else {
            continue;
        };
        if exclude_protocol_bases && base_class.protocol {
            continue;
        }
        if let Some(inherited) = method_definition(
            &base_class,
            method_name,
            index,
            cache,
            active,
            exclude_protocol_bases,
        ) {
            candidates.insert(inherited.key(), inherited);
        }
    }
    active.remove(&active_key);
    let result = (candidates.len() == 1)
        .then(|| candidates.into_values().next())
        .flatten();
    cache.insert(cache_key, result.clone());
    result
}

fn resolve_class_expression(
    expression: &MappingExpression,
    definition: &FunctionDefinition,
    index: &ProjectIndex,
    annotation: bool,
) -> Option<ClassDefinition> {
    if expression.kind == EXPRESSION_SUBSCRIPT {
        return expression
            .child
            .as_deref()
            .and_then(|child| resolve_class_expression(child, definition, index, annotation));
    }
    if expression.kind == EXPRESSION_STRING {
        return expression
            .string_value
            .as_deref()
            .and_then(forward_expression)
            .and_then(|parsed| resolve_class_expression(&parsed, definition, index, annotation));
    }
    let imports = if annotation {
        &definition.imports.annotation
    } else {
        &definition.imports.runtime
    };
    if expression.kind == EXPRESSION_NAME {
        let local = build_class_key(&definition.module_name, expression.name());
        if let Some(class) = index.classes.get(&local) {
            return Some(class.clone());
        }
        return imports
            .symbols
            .get(expression.name())
            .and_then(|(module, name)| index.classes.get(&build_class_key(module, name)))
            .cloned();
    }
    if expression.kind == EXPRESSION_ATTRIBUTE {
        let spelling = expression.parts.join(".");
        let resolved = spelling.split_once('.').and_then(|(first, remainder)| {
            imports
                .modules
                .get(first)
                .map(|module| format!("{module}.{remainder}"))
        });
        return index
            .classes
            .get(resolved.as_deref().unwrap_or(&spelling))
            .cloned();
    }
    None
}

fn receiver_states(
    definition: &FunctionDefinition,
    dispatch_class_key: Option<&str>,
    index: &ProjectIndex,
    method_cache: &mut MethodCache,
) -> Vec<ReceiverState> {
    let mut bindings = definition
        .syntax
        .parameters
        .iter()
        .map(|parameter| (parameter.name.clone(), None))
        .collect::<ReceiverState>();
    let mut invalid = BTreeSet::new();
    for parameter in &definition.syntax.parameters {
        if let Some(class) = parameter
            .annotation
            .as_ref()
            .and_then(|annotation| resolve_class_expression(annotation, definition, index, true))
        {
            bindings.insert(parameter.name.clone(), Some(class.key()));
        }
    }
    let mut states = Vec::new();
    for statement in &definition.syntax.statements {
        if statement.control_flow {
            let mut statement_state = bindings.clone();
            for name in &statement.assigned_names {
                statement_state.insert(name.clone(), None);
            }
            states.extend((0..statement.calls.len()).map(|_| statement_state.clone()));
            for name in &statement.assigned_names {
                invalid.insert(name.clone());
                bindings.insert(name.clone(), None);
            }
            continue;
        }
        states.extend((0..statement.calls.len()).map(|_| bindings.clone()));
        let (name, class) = local_binding(
            statement,
            definition,
            dispatch_class_key,
            index,
            &bindings,
            method_cache,
        );
        let Some(name) = name else {
            for assigned in &statement.assigned_names {
                invalid.insert(assigned.clone());
                bindings.insert(assigned.clone(), None);
            }
            continue;
        };
        let Some(class) = class else {
            invalid.insert(name.clone());
            bindings.insert(name, None);
            continue;
        };
        if invalid.contains(&name)
            || bindings
                .get(&name)
                .is_some_and(|current| current.as_deref() != Some(class.key().as_str()))
        {
            invalid.insert(name.clone());
            bindings.insert(name, None);
        } else {
            bindings.insert(name, Some(class.key()));
        }
    }
    states
}

fn local_binding(
    statement: &MappingStatement,
    definition: &FunctionDefinition,
    dispatch_class_key: Option<&str>,
    index: &ProjectIndex,
    bindings: &ReceiverState,
    method_cache: &mut MethodCache,
) -> (Option<String>, Option<ClassDefinition>) {
    let Some(name) = statement.binding_name.clone() else {
        return (None, None);
    };
    if let Some(annotation) = &statement.binding_annotation {
        return (
            Some(name),
            resolve_class_expression(annotation, definition, index, true),
        );
    }
    let Some(value) = &statement.binding_value else {
        return (Some(name), None);
    };
    if value.kind == EXPRESSION_CALL {
        if let Some(child) = value.child.as_deref() {
            let root = root_name(child);
            let constructor = if root.is_none_or(|root| !bindings.contains_key(root)) {
                resolve_class_expression(child, definition, index, false)
            } else {
                None
            };
            if constructor.is_some() {
                return (Some(name), constructor);
            }
            let factory = called_function(
                child,
                definition,
                dispatch_class_key,
                index,
                bindings,
                method_cache,
            );
            let class = factory.as_ref().and_then(|factory| {
                factory
                    .syntax
                    .returns
                    .as_ref()
                    .and_then(|returns| resolve_class_expression(returns, factory, index, true))
            });
            return (Some(name), class);
        }
    }
    if value.kind == EXPRESSION_NAME {
        let class = bindings
            .get(value.name())
            .and_then(Option::as_deref)
            .and_then(|key| index.classes.get(key))
            .cloned();
        return (Some(name), class);
    }
    (Some(name), None)
}

fn dispatch_class_name(
    definition: &FunctionDefinition,
    dispatch_class_key: Option<&str>,
    index: &ProjectIndex,
) -> Option<String> {
    let owning = definition.owning_class.as_deref()?;
    let class = index.classes.get(dispatch_class_key?)?;
    (class.name != owning).then(|| class.name.clone())
}

fn top_level_call_key(call: &MappingExpression, definition: &FunctionDefinition) -> String {
    definition
        .imports
        .runtime
        .symbols
        .get(call.name())
        .map_or_else(
            || build_function_key(&definition.module_name, call.name(), None),
            |(module, name)| build_function_key(module, name, None),
        )
}

fn imported_module_call_key(
    call: &MappingExpression,
    definition: &FunctionDefinition,
) -> Option<String> {
    let child = call.child.as_deref()?;
    if child.kind != EXPRESSION_NAME {
        return None;
    }
    definition
        .imports
        .runtime
        .modules
        .get(child.name())
        .map(|module| build_function_key(module, call.name(), None))
}

fn unresolved(call: &MappingCall, reason: &'static str) -> UnresolvedCall {
    UnresolvedCall {
        name: call.callee.spelling.clone(),
        line: call.line,
        reason,
    }
}

fn is_direct_self(expression: &MappingExpression) -> bool {
    expression.kind == EXPRESSION_NAME
        && matches!(expression.name(), SELF_RECEIVER | CLASS_RECEIVER)
}

fn root_name(mut expression: &MappingExpression) -> Option<&str> {
    while expression.kind == EXPRESSION_ATTRIBUTE {
        expression = expression.child.as_deref()?;
    }
    (expression.kind == EXPRESSION_NAME).then(|| expression.name())
}

fn parameter_names(definition: &FunctionDefinition) -> BTreeSet<String> {
    definition
        .syntax
        .parameters
        .iter()
        .map(|parameter| parameter.name.clone())
        .collect()
}

fn untyped_parameter_names(definition: &FunctionDefinition) -> BTreeSet<String> {
    definition
        .syntax
        .parameters
        .iter()
        .filter(|parameter| parameter.annotation.is_none())
        .map(|parameter| parameter.name.clone())
        .filter(|name| !matches!(name.as_str(), SELF_RECEIVER | CLASS_RECEIVER))
        .collect()
}

fn forward_expression(value: &str) -> Option<MappingExpression> {
    let spelling = value.split_whitespace().collect::<String>();
    let base = spelling.split('[').next()?;
    let parts = base.split('.').map(str::to_owned).collect::<Vec<_>>();
    if parts.is_empty()
        || parts.iter().any(|part| {
            part.is_empty()
                || !part.chars().enumerate().all(|(index, character)| {
                    character == '_'
                        || character.is_alphanumeric() && (index > 0 || !character.is_numeric())
                })
        })
    {
        return None;
    }
    let mut expression = MappingExpression {
        kind: EXPRESSION_NAME.to_owned(),
        spelling: parts[0].clone(),
        parts: vec![parts[0].clone()],
        child: None,
        string_value: None,
    };
    for part in parts.iter().skip(1) {
        expression = MappingExpression {
            kind: EXPRESSION_ATTRIBUTE.to_owned(),
            spelling: format!("{}.{}", expression.spelling, part),
            parts: expression
                .parts
                .iter()
                .cloned()
                .chain(std::iter::once(part.clone()))
                .collect(),
            child: Some(Box::new(expression)),
            string_value: None,
        };
    }
    if spelling.contains('[') {
        expression = MappingExpression {
            kind: EXPRESSION_SUBSCRIPT.to_owned(),
            spelling,
            parts: expression.parts.clone(),
            child: Some(Box::new(expression)),
            string_value: None,
        };
    }
    Some(expression)
}

fn class_as_function(class: &ClassDefinition) -> FunctionDefinition {
    FunctionDefinition {
        module_name: class.module_name.clone(),
        name: String::new(),
        path: class.path.clone(),
        syntax: crate::mapping::models::FunctionSyntax {
            line: 0,
            parameters: Vec::new(),
            returns: None,
            statements: Vec::new(),
        },
        imports: class.imports.clone(),
        owning_class: None,
    }
}
