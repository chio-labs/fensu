//! Native command orchestration for Fensu.
#![forbid(unsafe_code)]

pub mod command;

mod _helpers;
mod configuration;
mod constants;
mod mapping;
mod models;
mod reporting;
mod skills;

#[cfg(test)]
mod tests;
