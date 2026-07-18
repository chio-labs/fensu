//! Shared native core-rule output models.

use std::collections::HashMap;

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NativeFaultRow {
    pub code: String,
    pub line: u32,
    pub column: u32,
    pub message: Option<String>,
    pub remediation: Option<String>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
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
}
