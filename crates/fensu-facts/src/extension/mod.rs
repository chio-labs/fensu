//! Python extension-module adapter.

#[cfg(feature = "python")]
pub mod _helpers;
#[path = "_helpers/facades/facades.rs"]
mod facades;
#[cfg(feature = "python")]
pub mod main;
pub mod models;
#[path = "_helpers/queries/owner_symbols.rs"]
mod owner_symbols;
