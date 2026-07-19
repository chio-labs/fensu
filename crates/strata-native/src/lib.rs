//! Private native extension for Strata capabilities.
#![forbid(unsafe_code)]

#[cfg(feature = "python")]
pub mod cache;
#[cfg(feature = "python")]
pub mod extension;
pub mod rules;
