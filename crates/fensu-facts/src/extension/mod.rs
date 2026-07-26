//! Python extension-module adapter.

#[cfg(feature = "python")]
pub mod _helpers;
#[cfg(feature = "python")]
pub mod main;
pub mod models;
