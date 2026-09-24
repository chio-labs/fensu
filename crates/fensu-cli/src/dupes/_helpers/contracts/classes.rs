//! Statically resolve Python class hierarchies from the analysed worktree; nothing is imported.

use std::collections::{HashMap, HashSet};
use std::fs;
use std::path::{Path, PathBuf};

use fensu_facts::parsing::main::parse_strict::parse_strict;
use ruff_python_ast::{Expr, ModModule, PythonVersion, Stmt, StmtClassDef};

use crate::dupes::models::ClassKey;

const ABSTRACT_DECORATOR: &str = "abstractmethod";
const PYTHON_SUFFIX: &str = ".py";
const PACKAGE_INIT: &str = "__init__.py";

#[derive(Clone, Debug, Default)]
pub(crate) struct ClassInfo {
    pub(crate) bases: Vec<ClassKey>,
    pub(crate) concrete: HashSet<String>,
    pub(crate) abstract_methods: HashSet<String>,
    pub(crate) complete: bool,
}

pub(crate) struct ClassResolver {
    root: PathBuf,
    import_roots: Vec<String>,
    modules: HashMap<String, Option<ModModule>>,
    infos: HashMap<ClassKey, ClassInfo>,
    orders: HashMap<ClassKey, Vec<ClassKey>>,
    abstract_names: HashMap<ClassKey, HashSet<String>>,
}

impl ClassResolver {
    pub(crate) fn new(root: &Path, import_roots: &[String]) -> Self {
        Self {
            root: root.to_path_buf(),
            import_roots: import_roots.to_vec(),
            modules: HashMap::new(),
            infos: HashMap::new(),
            orders: HashMap::new(),
            abstract_names: HashMap::new(),
        }
    }

    pub(crate) fn file_exists(&self, path: &str) -> bool {
        self.root.join(path).is_file()
    }

    pub(crate) fn exists(&mut self, key: &ClassKey) -> bool {
        self.module(&key.path)
            .is_some_and(|module| find_class(module, &key.name).is_some())
    }

    pub(crate) fn info(&mut self, key: &ClassKey) -> ClassInfo {
        if let Some(info) = self.infos.get(key) {
            return info.clone();
        }
        let info = self.build_info(key);
        self.infos.insert(key.clone(), info.clone());
        info
    }

    /// Mirror `__abstractmethods__`: own abstract methods plus unoverridden inherited ones.
    pub(crate) fn abstract_methods(&mut self, key: &ClassKey) -> HashSet<String> {
        if let Some(names) = self.abstract_names.get(key) {
            return names.clone();
        }
        self.abstract_names.insert(key.clone(), HashSet::new());
        let info = self.info(key);
        let mut names = info.abstract_methods.clone();
        for base in &info.bases {
            names.extend(
                self.abstract_methods(base)
                    .into_iter()
                    .filter(|name| !info.concrete.contains(name)),
            );
        }
        self.abstract_names.insert(key.clone(), names.clone());
        names
    }

    /// C3-linearise the statically resolvable bases, as `type.__mro__` would.
    pub(crate) fn method_resolution_order(&mut self, key: &ClassKey) -> Vec<ClassKey> {
        if let Some(order) = self.orders.get(key) {
            return order.clone();
        }
        self.orders.insert(key.clone(), vec![key.clone()]);
        let bases = self.info(key).bases;
        let mut sequences: Vec<Vec<ClassKey>> = bases
            .iter()
            .map(|base| self.method_resolution_order(base))
            .collect();
        sequences.push(bases);
        let mut order = vec![key.clone()];
        order.extend(c3_merge(sequences));
        self.orders.insert(key.clone(), order.clone());
        order
    }

    fn module(&mut self, path: &str) -> Option<&ModModule> {
        if !self.modules.contains_key(path) {
            let parsed = match fs::read_to_string(self.root.join(path)) {
                Ok(source) => match parse_strict(&source, PythonVersion::latest()) {
                    Ok(parsed) => Some(parsed.into_syntax()),
                    Err(_) => None,
                },
                Err(_) => None,
            };
            self.modules.insert(path.to_owned(), parsed);
        }
        self.modules.get(path).and_then(Option::as_ref)
    }

    fn build_info(&mut self, key: &ClassKey) -> ClassInfo {
        let Some(module) = self.module(&key.path).cloned() else {
            return ClassInfo::default();
        };
        let Some(class) = find_class(&module, &key.name) else {
            return ClassInfo::default();
        };
        let mut info = ClassInfo {
            complete: true,
            ..ClassInfo::default()
        };
        for statement in &class.body {
            if let Stmt::FunctionDef(function) = statement {
                let abstract_method =
                    function
                        .decorator_list
                        .iter()
                        .any(|decorator| match &decorator.expression {
                            Expr::Name(name) => name.id.as_str() == ABSTRACT_DECORATOR,
                            Expr::Attribute(attribute) => {
                                attribute.attr.as_str() == ABSTRACT_DECORATOR
                            }
                            _ => false,
                        });
                let names = if abstract_method {
                    &mut info.abstract_methods
                } else {
                    &mut info.concrete
                };
                names.insert(function.name.id.to_string());
            }
        }
        for base in class.bases() {
            match self.resolve_base(&module, &key.path, base) {
                Some(resolved) => info.bases.push(resolved),
                None if self.references_repository(&module, &key.path, base) => {
                    info.complete = false;
                }
                None => {}
            }
        }
        info
    }

    fn resolve_base(&self, module: &ModModule, importer: &str, base: &Expr) -> Option<ClassKey> {
        let base = match base {
            Expr::Subscript(subscript) => subscript.value.as_ref(),
            other => other,
        };
        let Expr::Name(name) = base else {
            return None;
        };
        if find_class(module, name.id.as_str()).is_some() {
            return Some(ClassKey {
                path: importer.to_owned(),
                name: name.id.to_string(),
            });
        }
        for statement in &module.body {
            let Stmt::ImportFrom(import) = statement else {
                continue;
            };
            for alias in &import.names {
                let bound = alias.asname.as_ref().unwrap_or(&alias.name);
                if bound.as_str() == name.id.as_str() {
                    let module_name = import.module.as_ref().map(|value| value.as_str());
                    return self
                        .module_path(importer, module_name, import.level)
                        .map(|path| ClassKey {
                            path,
                            name: alias.name.to_string(),
                        });
                }
            }
        }
        None
    }

    /// Report unresolved bases that name this repository, so their ancestry stays unknown.
    fn references_repository(&self, module: &ModModule, importer: &str, base: &Expr) -> bool {
        let mut root = match base {
            Expr::Subscript(subscript) => subscript.value.as_ref(),
            other => other,
        };
        while let Expr::Attribute(attribute) = root {
            root = attribute.value.as_ref();
        }
        let Expr::Name(name) = root else {
            return true;
        };
        let bound_name = name.id.as_str();
        if find_class(module, bound_name).is_some() {
            return true;
        }
        for statement in &module.body {
            match statement {
                Stmt::ImportFrom(import) => {
                    for alias in &import.names {
                        let bound = alias.asname.as_ref().unwrap_or(&alias.name);
                        if bound.as_str() == bound_name {
                            let module_name = import.module.as_ref().map(|value| value.as_str());
                            return import.level > 0
                                || self
                                    .module_path(importer, module_name, import.level)
                                    .is_some();
                        }
                    }
                }
                Stmt::Import(import) => {
                    for alias in &import.names {
                        let bound = alias.asname.as_ref().map_or_else(
                            || alias.name.as_str().split('.').next().unwrap_or_default(),
                            |value| value.as_str(),
                        );
                        if bound == bound_name {
                            return self
                                .module_path(importer, Some(alias.name.as_str()), 0)
                                .is_some();
                        }
                    }
                }
                _ => {}
            }
        }
        false
    }

    fn module_path(&self, importer: &str, module: Option<&str>, level: u32) -> Option<String> {
        let module = module.filter(|value| !value.is_empty())?;
        let parts: Vec<&str> = module.split('.').collect();
        let bases: Vec<PathBuf> = if level > 0 {
            let mut anchor = Path::new(importer).parent()?.to_path_buf();
            for _ in 1..level {
                anchor = anchor.parent()?.to_path_buf();
            }
            vec![join_parts(anchor, &parts)]
        } else {
            self.import_roots
                .iter()
                .map(|root| join_parts(PathBuf::from(root), &parts))
                .collect()
        };
        for base in bases {
            let file = base.with_file_name(format!(
                "{}{PYTHON_SUFFIX}",
                base.file_name()?.to_string_lossy()
            ));
            for candidate in [file, base.join(PACKAGE_INIT)] {
                if self.root.join(&candidate).is_file() {
                    return Some(candidate.to_string_lossy().replace('\\', "/"));
                }
            }
        }
        None
    }
}

fn join_parts(base: PathBuf, parts: &[&str]) -> PathBuf {
    parts.iter().fold(base, |path, part| path.join(part))
}

fn find_class<'m>(module: &'m ModModule, name: &str) -> Option<&'m StmtClassDef> {
    module.body.iter().find_map(|statement| match statement {
        Stmt::ClassDef(class) if class.name.id.as_str() == name => Some(class),
        _ => None,
    })
}

/// Merge linearisations; an inconsistent hierarchy falls back to first-seen order.
fn c3_merge(sequences: Vec<Vec<ClassKey>>) -> Vec<ClassKey> {
    let mut merged: Vec<ClassKey> = Vec::new();
    let mut pending: Vec<Vec<ClassKey>> = sequences
        .into_iter()
        .filter(|sequence| !sequence.is_empty())
        .collect();
    while !pending.is_empty() {
        let tails: HashSet<&ClassKey> = pending
            .iter()
            .flat_map(|sequence| sequence.iter().skip(1))
            .collect();
        let head = pending
            .iter()
            .map(|sequence| &sequence[0])
            .find(|candidate| !tails.contains(candidate))
            .unwrap_or(&pending[0][0])
            .clone();
        pending = pending
            .into_iter()
            .map(|sequence| without_class(sequence, &head))
            .filter(|sequence| !sequence.is_empty())
            .collect();
        merged.push(head);
    }
    merged
}

fn without_class(sequence: Vec<ClassKey>, removed: &ClassKey) -> Vec<ClassKey> {
    sequence
        .into_iter()
        .filter(|item| item != removed)
        .collect()
}
