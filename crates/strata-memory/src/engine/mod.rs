//! Memory indexing and retrieval engine.

#[cfg(feature = "sqlite-engine")]
pub(crate) mod constants;
#[cfg(feature = "sqlite-engine")]
pub mod errors;
mod helpers;
pub mod main;
pub mod models;
