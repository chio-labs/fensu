//! Shared native core-rule output models.

use std::collections::HashMap;

use fensu_facts::extension::models::ProgramHandle;

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NativeExecutionTarget {
    pub repository_path: String,
    pub scope: String,
    pub root: String,
    pub relative_parts: Vec<String>,
    pub direct: bool,
    pub ownership_root: Option<String>,
    pub ownership_offset: Option<usize>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NativeExecutionRule {
    pub code: String,
    pub family: String,
    pub owner: String,
}

impl NativeExecutionRule {
    pub fn new(code: String, family: String, owner: String) -> Self {
        Self {
            code,
            family,
            owner,
        }
    }
}

#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct NativeExecutionPlan {
    pub codes: Vec<String>,
    pub identities: Vec<(String, String)>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NativeFaultRow {
    pub code: String,
    pub line: u32,
    pub column: u32,
    pub message: Option<String>,
    pub remediation: Option<String>,
    pub path: Option<String>,
}

#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct NativeDeadCodeContext {
    pub enabled: bool,
    pub roots: Vec<(Vec<String>, Vec<String>)>,
    pub entrypoints: Vec<(String, String)>,
    pub config_path: String,
}

#[derive(Clone, Debug, Eq, Hash, PartialEq)]
pub struct NativeProjectQuery {
    pub kind: String,
    pub path: String,
    pub argument: String,
}

impl NativeProjectQuery {
    pub fn key(&self) -> String {
        format!("{}\0{}\0{}", self.kind, self.path, self.argument)
    }
}

impl NativeProjectModule {
    pub fn new(
        path: String,
        scope: String,
        module_parts: Vec<String>,
        program: ProgramHandle,
    ) -> Self {
        let ownership_root = module_parts.first().cloned();
        Self {
            path,
            scope,
            module_parts,
            program,
            ownership_start: Some(1),
            ownership_root,
        }
    }

    pub fn with_ownership(
        mut self,
        ownership_start: Option<usize>,
        ownership_root: Option<String>,
    ) -> Self {
        self.ownership_start = ownership_start;
        self.ownership_root = ownership_root;
        self
    }
}

impl NativeProjectPlane {
    pub fn new(modules: Vec<NativeProjectModule>, entrypoint_modules: Vec<String>) -> Self {
        Self {
            modules,
            entrypoint_modules,
        }
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NativeRuleContext {
    pub dead_code: NativeDeadCodeContext,
    pub scope: String,
    pub role: Option<String>,
    pub is_main_module: bool,
    pub thresholds: HashMap<String, u32>,
    pub repository_path: String,
    pub contracts: Vec<(String, String)>,
    pub relative_parts: Vec<String>,
    pub is_entry_module: bool,
    pub package_name: String,
    pub tooling_packages: Vec<String>,
    pub scope_roots: Vec<(String, String)>,
    pub test_scopes: Vec<String>,
    pub ownership_root: Option<String>,
    pub ownership_roots: Vec<String>,
    pub ownership_offset: Option<usize>,
    pub observations: HashMap<String, Vec<String>>,
    pub custom_registrations: Vec<(String, String, String, String, u32, u32)>,
    pub repo_root: String,
    pub rule_options: HashMap<String, HashMap<String, String>>,
}

impl Default for NativeRuleContext {
    fn default() -> Self {
        Self {
            dead_code: NativeDeadCodeContext::default(),
            scope: String::new(),
            role: None,
            is_main_module: false,
            thresholds: HashMap::new(),
            repository_path: String::new(),
            contracts: Vec::new(),
            relative_parts: Vec::new(),
            is_entry_module: false,
            package_name: String::new(),
            tooling_packages: Vec::new(),
            scope_roots: Vec::new(),
            test_scopes: Vec::new(),
            ownership_root: None,
            ownership_roots: Vec::new(),
            ownership_offset: Some(0),
            observations: HashMap::new(),
            custom_registrations: Vec::new(),
            repo_root: String::new(),
            rule_options: HashMap::new(),
        }
    }
}

impl NativeRuleContext {
    pub fn ownership_offset(&self) -> Option<usize> {
        self.ownership_offset
    }

    pub fn observation(&self, query: &NativeProjectQuery) -> &[String] {
        self.observations
            .get(&query.key())
            .map(Vec::as_slice)
            .unwrap_or_default()
    }

    pub fn option(&self, code: &str, name: &str) -> Option<&str> {
        self.rule_options
            .get(code)
            .and_then(|values| values.get(name))
            .map(String::as_str)
    }
}

#[derive(Clone, Debug)]
pub struct NativeProjectModule {
    pub path: String,
    pub scope: String,
    pub module_parts: Vec<String>,
    pub program: ProgramHandle,
    pub ownership_start: Option<usize>,
    pub ownership_root: Option<String>,
}

#[derive(Clone, Debug, Default)]
pub struct NativeProjectPlane {
    pub modules: Vec<NativeProjectModule>,
    pub entrypoint_modules: Vec<String>,
}
