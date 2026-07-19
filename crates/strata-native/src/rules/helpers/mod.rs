//! Fact-row policy helpers for native rules.

#[path = "annotations/annotations.rs"]
pub(crate) mod annotations;
#[path = "hygiene/hygiene.rs"]
pub(crate) mod hygiene;
#[path = "layers/local.rs"]
mod layer_local;
#[path = "layers/project.rs"]
mod layer_project;
#[path = "layers/layers.rs"]
pub(crate) mod layers;
#[path = "naming/naming.rs"]
pub(crate) mod naming;
#[path = "naming_globs/naming_globs.rs"]
pub(crate) mod naming_globs;
#[path = "project_queries/project_queries.rs"]
pub(crate) mod project_queries;
#[path = "roles/declarations.rs"]
mod role_declarations;
#[path = "roles/paths.rs"]
mod role_paths;
#[path = "roles/project_layout.rs"]
mod role_project_layout;
#[path = "roles/project_layout_paths.rs"]
mod role_project_layout_paths;
#[path = "roles/project_layout_queries.rs"]
mod role_project_layout_queries;
#[path = "roles/surfaces.rs"]
mod role_surfaces;
#[path = "roles/roles.rs"]
pub(crate) mod roles;
#[path = "shape/shape.rs"]
pub(crate) mod shape;
#[path = "tests/layout.rs"]
mod test_layout;
#[path = "tests/names.rs"]
mod test_names;
#[path = "tests/tests.rs"]
pub(crate) mod tests;
