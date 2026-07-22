use std::env;
use std::path::Path;

use crate::command::main::{check, help, init, map, memory, rule, skills};
use crate::configuration::main::custom_rules;
use crate::helpers::{check_cleanup, process};
use crate::models::CliOutput;

pub fn run_cli() -> CliOutput {
    let arguments = env::args().skip(1).collect::<Vec<_>>();
    dispatch(&arguments).unwrap_or_else(CliOutput::error)
}

fn dispatch(arguments: &[String]) -> Result<CliOutput, String> {
    let Some(command) = arguments.first().map(String::as_str) else {
        return Ok(CliOutput::error(
            "Usage: fensu {check,init,rule,skills,map,memory} ...".to_owned(),
        ));
    };
    match command {
        "--version" => Ok(CliOutput::success(format!(
            "fensu {}\n",
            env!("CARGO_PKG_VERSION")
        ))),
        "--help" | "-h" => Ok(CliOutput::success(help::help())),
        "check" => dispatch_check(&arguments[1..]),
        "init" => init::init(&arguments[1..]),
        "map" => map::run(&arguments[1..]),
        "memory" => memory::run(&arguments[1..]),
        "rule" => rule::rule(&arguments[1..]),
        "skills" => skills::run(&arguments[1..]),
        _ => Ok(CliOutput {
            stdout: String::new(),
            stderr: format!(
                "Unknown command: {command}\nUsage: fensu {{check,init,rule,skills,map,memory}} ...\n"
            ),
            exit_code: 2,
        }),
    }
}

fn dispatch_check(arguments: &[String]) -> Result<CliOutput, String> {
    let cleanup = check_cleanup::prepare(Path::new("."));
    let result = if custom_rules::custom_rules_are_configured(Path::new("."))? {
        let exit_code = process::run_custom_check_host(arguments)?;
        Ok(CliOutput {
            stdout: String::new(),
            stderr: String::new(),
            exit_code,
        })
    } else {
        check::run(arguments)
    };
    if result
        .as_ref()
        .is_ok_and(|output| matches!(output.exit_code, 0 | 1))
        && !arguments
            .iter()
            .any(|argument| matches!(argument.as_str(), "--help" | "-h"))
    {
        if let Some(cleanup) = cleanup {
            cleanup.run();
        }
    }
    result
}
