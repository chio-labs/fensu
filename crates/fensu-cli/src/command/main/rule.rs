use crate::helpers::rule::rule_output;
use crate::models::CliOutput;

pub(crate) fn rule(arguments: &[String]) -> Result<CliOutput, String> {
    if arguments
        .iter()
        .any(|value| matches!(value.as_str(), "--help" | "-h"))
    {
        return Ok(CliOutput::success(
            "usage: fensu rule [-h] [--color {auto,always,never}] code\n".to_owned(),
        ));
    }
    rule_output(arguments).map(CliOutput::success)
}
