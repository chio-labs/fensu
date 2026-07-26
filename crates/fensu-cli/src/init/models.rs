//! Initialisation survey and layout models.

#[derive(Debug)]
pub(crate) struct RepositorySurvey {
    pub(crate) package_roots: Vec<String>,
    pub(crate) empty: bool,
}

#[derive(Debug)]
pub(crate) struct InitPlan {
    pub(crate) roots: Vec<String>,
    pub(crate) tests: Vec<String>,
    pub(crate) tooling: Vec<String>,
    pub(crate) project_name: Option<String>,
}
