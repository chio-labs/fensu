//! Shared native core-rule output models.

use std::collections::HashMap;

use fensu_facts::extension::models::ProgramHandle;

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NativeFaultRow {
    pub code: String,
    pub line: u32,
    pub column: u32,
    pub message: Option<String>,
    pub remediation: Option<String>,
    pub path: Option<String>,
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
        Self {
            path,
            scope,
            module_parts,
            program,
        }
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

#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct NativeRuleContext {
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
    pub observations: HashMap<String, Vec<String>>,
    pub custom_registrations: Vec<(String, String, String, String, u32, u32)>,
    pub repo_root: String,
    pub rule_options: HashMap<String, HashMap<String, String>>,
}

impl NativeRuleContext {
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
}

#[derive(Clone, Debug, Default)]
pub struct NativeProjectPlane {
    pub modules: Vec<NativeProjectModule>,
    pub entrypoint_modules: Vec<String>,
}
