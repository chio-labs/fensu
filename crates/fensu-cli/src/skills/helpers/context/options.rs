use crate::skills::models::{SkillOptions, SkillTarget};

const ARGUMENT_TERMINATOR: &str = "--";
const HELP_OPTION: &str = "help";
const HELP_SHORT_OPTION: &str = "-h";

pub(crate) const HELP: &str = "usage: fensu skills [-h] [--global] [--target {opencode,claude,agents}]\n                    [--force] [--check] [--install-root git|project|PATH]\n\noptions:\n  -h, --help            show this help message and exit\n  --global\n  --target {opencode,claude,agents}\n  --force\n  --check               verify deterministic installed bytes without writing\n                        files\n  --install-root git|project|PATH\n                        install locally at the Git root, project root, or an\n                        explicit path\n";

pub(crate) fn parse_options(arguments: &[String]) -> Result<SkillOptions, String> {
    let mut options = SkillOptions::default();
    let mut index = 0;
    let mut positional = Vec::new();
    let mut terminated = false;
    while index < arguments.len() {
        let argument = &arguments[index];
        if terminated {
            positional.push(argument.clone());
            index += 1;
            continue;
        }
        if argument == ARGUMENT_TERMINATOR {
            terminated = true;
            index += 1;
            continue;
        }
        let (name, inline) = argument
            .split_once('=')
            .map_or((argument.as_str(), None), |(name, value)| {
                (name, Some(value))
            });
        let resolved = option_name(name)?;
        match resolved {
            HELP_OPTION => {
                let _ = reject_inline(inline, "--help")?;
                options.help = true;
                return Ok(options);
            }
            "global" => {
                let _ = reject_inline(inline, "--global")?;
                options.global_install = true;
            }
            "force" => {
                let _ = reject_inline(inline, "--force")?;
                options.force = true;
            }
            "check" => {
                let _ = reject_inline(inline, "--check")?;
                options.check = true;
            }
            "target" => {
                let value = option_value(arguments, &mut index, inline, "--target")?;
                let target = SkillTarget::parse(value).ok_or_else(|| {
                    format!("usage: fensu skills ...\nfensu skills: error: argument --target: invalid choice: '{value}' (choose from 'opencode', 'claude', 'agents')")
                })?;
                options.targets.push(target);
            }
            "install-root" => {
                options.install_root =
                    Some(option_value(arguments, &mut index, inline, "--install-root")?.to_owned());
            }
            "positional" => positional.push(argument.clone()),
            _ => {}
        }
        index += 1;
    }
    if !positional.is_empty() {
        return Err(format!(
            "usage: fensu skills ...\nfensu skills: error: unrecognized arguments: {}",
            positional.join(" ")
        ));
    }
    Ok(options)
}

fn option_name(value: &str) -> Result<&'static str, String> {
    if value == HELP_SHORT_OPTION {
        return Ok(HELP_OPTION);
    }
    if !value.starts_with(ARGUMENT_TERMINATOR) {
        return Ok("positional");
    }
    let candidate = &value[ARGUMENT_TERMINATOR.len()..];
    let names = [
        HELP_OPTION,
        "global",
        "target",
        "force",
        "check",
        "install-root",
    ];
    let matches = names
        .iter()
        .filter(|name| name.starts_with(candidate))
        .copied()
        .collect::<Vec<_>>();
    match matches.as_slice() {
        [name] => Ok(name),
        [] => Err(format!(
            "usage: fensu skills ...\nfensu skills: error: unrecognized arguments: {value}"
        )),
        _ => Err(format!(
            "usage: fensu skills ...\nfensu skills: error: ambiguous option: {value} could match {}",
            matches
                .iter()
                .map(|name| format!("--{name}"))
                .collect::<Vec<_>>()
                .join(", ")
        )),
    }
}

fn reject_inline(value: Option<&str>, option: &str) -> Result<bool, String> {
    if value.is_some() {
        return Err(format!(
            "fensu skills: error: argument {option}: ignored explicit argument"
        ));
    }
    Ok(true)
}

fn option_value<'a>(
    arguments: &'a [String],
    index: &mut usize,
    inline: Option<&'a str>,
    option: &str,
) -> Result<&'a str, String> {
    if let Some(value) = inline {
        return Ok(value);
    }
    *index += 1;
    arguments
        .get(*index)
        .map(String::as_str)
        .ok_or_else(|| format!("fensu skills: error: argument {option}: expected one argument"))
}
