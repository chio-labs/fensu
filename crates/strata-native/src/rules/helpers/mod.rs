//! Fact-row policy helpers for native rules.

#[path = "annotations/annotations.rs"]
pub(crate) mod annotations;
#[path = "hygiene/hygiene.rs"]
pub(crate) mod hygiene;
#[path = "layers/layers.rs"]
pub(crate) mod layers;
#[path = "naming/naming.rs"]
pub(crate) mod naming;
#[path = "naming_globs/naming_globs.rs"]
pub(crate) mod naming_globs;
#[path = "roles/declarations.rs"]
mod role_declarations;
#[path = "roles/paths.rs"]
mod role_paths;
#[path = "roles/surfaces.rs"]
mod role_surfaces;
#[path = "roles/roles.rs"]
pub(crate) mod roles;
#[path = "shape/shape.rs"]
pub(crate) mod shape;
#[path = "tests/tests.rs"]
pub(crate) mod tests;
