//! Native command orchestration for Fensu.
#![forbid(unsafe_code)]

pub mod command;

mod _helpers;
mod catalogue;
mod configuration;
mod constants;
mod hosting;
mod mapping;
mod models;
mod reporting;
mod skills;

#[cfg(test)]
mod tests;
