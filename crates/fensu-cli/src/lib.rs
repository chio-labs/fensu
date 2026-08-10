//! Native command orchestration for Fensu.
#![forbid(unsafe_code)]

pub mod command;

mod analyzer;
mod catalogue;
mod check;
mod configuration;
mod constants;
mod hosting;
mod init;
mod mapping;
mod models;
mod reporting;
mod repository_io;
mod skills;
mod target_command;

#[cfg(test)]
mod tests;
