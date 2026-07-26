//! Python extension-module adapter.

#[cfg(feature = "python")]
pub mod _helpers;
#[cfg(feature = "python")]
pub mod main;
pub mod models;
#[path = "_helpers/queries/owner_symbols.rs"]
mod owner_symbols;
