use std::collections::{BTreeMap, BTreeSet};
use std::path::PathBuf;

use serde::{Deserialize, Serialize};

use crate::mapping::helpers::identity::{build_class_key, build_function_key, qualify};

#[derive(Clone, Debug)]
pub(crate) struct MappingSource {
    pub(crate) scan_path: PathBuf,
    pub(crate) import_root: PathBuf,
}

#[derive(Clone, Debug)]
pub(crate) struct MappingProject {
    pub(crate) repo_root: PathBuf,
    pub(crate) sources: Vec<MappingSource>,
    pub(crate) cache_enabled: bool,
}

#[derive(Clone, Debug)]
pub(crate) struct SourceSnapshot {
    pub(crate) path: PathBuf,
    pub(crate) relative_path: String,
    pub(crate) import_root_identity: String,
    pub(crate) module_name: String,
    pub(crate) source: Vec<u8>,
    pub(crate) source_fingerprint: String,
}

#[derive(Clone, Debug, Default, Deserialize, Serialize)]
pub(crate) struct ImportView {
    pub(crate) symbols: BTreeMap<String, (String, String)>,
    pub(crate) modules: BTreeMap<String, String>,
}

#[derive(Clone, Debug, Default, Deserialize, Serialize)]
pub(crate) struct ModuleImports {
    pub(crate) runtime: ImportView,
    pub(crate) annotation: ImportView,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
pub(crate) struct MappingExpression {
    pub(crate) kind: String,
    pub(crate) spelling: String,
    pub(crate) parts: Vec<String>,
    pub(crate) child: Option<Box<MappingExpression>>,
    pub(crate) string_value: Option<String>,
}

impl MappingExpression {
    pub(crate) fn name(&self) -> &str {
        self.parts
            .last()
            .map(String::as_str)
            .unwrap_or_else(|| self.spelling.rsplit('.').next().unwrap_or(&self.spelling))
    }
}

#[derive(Clone, Debug, Deserialize, Serialize)]
pub(crate) struct MappingParameter {
    pub(crate) name: String,
    pub(crate) annotation: Option<MappingExpression>,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
pub(crate) struct MappingCall {
    pub(crate) callee: MappingExpression,
    pub(crate) line: u32,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
pub(crate) struct MappingStatement {
    pub(crate) control_flow: bool,
    pub(crate) assigned_names: BTreeSet<String>,
    pub(crate) binding_name: Option<String>,
    pub(crate) binding_annotation: Option<MappingExpression>,
    pub(crate) binding_value: Option<MappingExpression>,
    pub(crate) calls: Vec<MappingCall>,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
pub(crate) struct FunctionSyntax {
    pub(crate) line: u32,
    pub(crate) parameters: Vec<MappingParameter>,
    pub(crate) returns: Option<MappingExpression>,
    pub(crate) statements: Vec<MappingStatement>,
}

impl FunctionSyntax {
    pub(crate) fn calls(&self) -> impl Iterator<Item = &MappingCall> {
        self.statements
            .iter()
            .flat_map(|statement| &statement.calls)
    }
}

#[derive(Clone, Debug, Deserialize, Serialize)]
pub(crate) struct ClassReference {
    pub(crate) expression: MappingExpression,
    pub(crate) annotation: bool,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
pub(crate) struct FunctionDefinition {
    pub(crate) module_name: String,
    pub(crate) name: String,
    pub(crate) path: PathBuf,
    pub(crate) syntax: FunctionSyntax,
    pub(crate) imports: ModuleImports,
    pub(crate) owning_class: Option<String>,
}

impl FunctionDefinition {
    pub(crate) fn qualified_name(&self) -> String {
        qualify(&self.name, self.owning_class.as_deref())
    }

    pub(crate) fn key(&self) -> String {
        build_function_key(&self.module_name, &self.name, self.owning_class.as_deref())
    }
}

#[derive(Clone, Debug, Deserialize, Serialize)]
pub(crate) struct ClassDefinition {
    pub(crate) module_name: String,
    pub(crate) name: String,
    pub(crate) path: PathBuf,
    pub(crate) imports: ModuleImports,
    pub(crate) bases: Vec<MappingExpression>,
    pub(crate) base_keys: Vec<String>,
    pub(crate) protocol: bool,
    pub(crate) class_attributes: BTreeMap<String, ClassReference>,
    pub(crate) instance_attributes: BTreeMap<String, ClassReference>,
}

impl ClassDefinition {
    pub(crate) fn key(&self) -> String {
        build_class_key(&self.module_name, &self.name)
    }
}

#[derive(Clone, Debug, Default, Deserialize, Serialize)]
pub(crate) struct ProjectIndex {
    pub(crate) functions: BTreeMap<String, FunctionDefinition>,
    pub(crate) classes: BTreeMap<String, ClassDefinition>,
    pub(crate) protocol_implementations: BTreeMap<String, Vec<String>>,
}

#[derive(Clone, Debug)]
pub(crate) struct ResolvedCallable {
    pub(crate) definition: FunctionDefinition,
    pub(crate) dispatch_class_key: Option<String>,
}

#[derive(Clone, Debug)]
pub(crate) struct UnresolvedCall {
    pub(crate) name: String,
    pub(crate) line: u32,
    pub(crate) reason: &'static str,
}

#[derive(Clone, Debug)]
pub(crate) enum CallMapEntry {
    Node(Box<CallMapNode>),
    Unresolved(UnresolvedCall),
}

#[derive(Clone, Debug)]
pub(crate) struct CallMapNode {
    pub(crate) definition: FunctionDefinition,
    pub(crate) entries: Vec<CallMapEntry>,
    pub(crate) dispatch_class_name: Option<String>,
    pub(crate) cycle: bool,
    pub(crate) truncated: bool,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum PathMode {
    Absolute,
    Relative,
    Compact,
    None,
}

#[derive(Clone, Copy, Debug, Default)]
pub(crate) struct MapCacheStats {
    pub(crate) manifest_hit: bool,
    pub(crate) parsed_files: usize,
    pub(crate) reused_file_records: usize,
    pub(crate) writes: usize,
    pub(crate) storage_failed: bool,
    pub(crate) internal_error: bool,
}

#[derive(Debug)]
pub(crate) struct MapOptions {
    pub(crate) symbol: String,
    pub(crate) depth: usize,
    pub(crate) roots: Vec<String>,
    pub(crate) path_mode: PathMode,
    pub(crate) color: String,
    pub(crate) cache_enabled: Option<bool>,
    pub(crate) cache_stats: bool,
}
