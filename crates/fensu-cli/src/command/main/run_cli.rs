use std::env;
use std::path::Path;

use crate::check::main::check_routing::check_routing;
use crate::check::main::clean_caches::clean_caches;
use crate::check::main::prepare_cleanup::prepare_cleanup;
use crate::command::_helpers::check_partition::execution::partitioned_check;
use crate::command::main::{check, help, init, map, rule, skills, target};
use crate::configuration::main::load_targets;
use crate::models::CliOutput;

pub(super) fn run_cli() -> CliOutput {
    let arguments = env::args().skip(1).collect::<Vec<_>>();
    dispatch(&arguments).unwrap_or_else(CliOutput::error)
}

fn dispatch(arguments: &[String]) -> Result<CliOutput, String> {
    let Some(command) = arguments.first().map(String::as_str) else {
        return Ok(CliOutput::error(
            "Usage: fensu {check,init,rule,skills,map,target} ...".to_owned(),
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
        "rule" => rule::rule(&arguments[1..]),
        "skills" => skills::run(&arguments[1..]),
        "target" => target::run(&arguments[1..]),
        _ => Ok(CliOutput {
            stdout: String::new(),
            stderr: format!(
                "Unknown command: {command}\nUsage: fensu {{check,init,rule,skills,map,target}} ...\n"
            ),
            exit_code: 2,
        }),
    }
}

fn dispatch_check(arguments: &[String]) -> Result<CliOutput, String> {
    let routing = check_routing(arguments)?;
    if routing.help {
        return check::run(arguments, None);
    }
    let loaded = load_targets::load_targets(Path::new("."), routing.target)?;
    let cleanup = prepare_cleanup(Path::new("."), routing.target);
    let result = match partitioned_check(arguments, &loaded) {
        Some(output) => Ok(output),
        None => check::run(arguments, None),
    };
    if result
        .as_ref()
        .is_ok_and(|output| matches!(output.exit_code, 0 | 1))
        && !arguments
            .iter()
            .any(|argument| matches!(argument.as_str(), "--help" | "-h"))
    {
        for cleanup in &cleanup {
            clean_caches(cleanup);
        }
    }
    result
}
