use std::env;
use std::path::Path;

use crate::command::main::{check, help, init, map, memory, rule, skills};
use crate::configuration::main::custom_rules;
use crate::helpers::process;
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
        "check" => {
            if custom_rules::custom_rules_are_configured(Path::new("."))? {
                process::run_python(arguments).map(CliOutput::delegated)
            } else {
                check::run(&arguments[1..])
            }
        }
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
