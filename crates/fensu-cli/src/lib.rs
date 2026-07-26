//! Native command orchestration for Fensu.
#![forbid(unsafe_code)]

pub mod command;

mod catalogue;
mod check;
mod configuration;
mod constants;
mod hosting;
mod init;
mod mapping;
mod models;
mod reporting;
mod skills;

#[cfg(test)]
mod tests;
