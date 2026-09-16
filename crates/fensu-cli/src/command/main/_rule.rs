use crate::catalogue::main::rule_output::rule_output;
use crate::models::CliOutput;

pub(super) fn rule(arguments: &[String]) -> Result<CliOutput, String> {
    if requests_help(arguments) {
        return Ok(CliOutput::success(
            "usage: fensu rule [-h] [--color {auto,always,never}] [--target TARGET] code\n"
                .to_owned(),
        ));
    }
    rule_output(arguments).map(CliOutput::success)
}

fn requests_help(arguments: &[String]) -> bool {
    let mut index = 0;
    while index < arguments.len() {
        if matches!(arguments[index].as_str(), "--target" | "--color") {
            index += 2;
            continue;
        }
        if matches!(arguments[index].as_str(), "--help" | "-h") {
            return true;
        }
        index += 1;
    }
    false
}
