use std::path::{Component, PathBuf};

use crate::target_command::constants::{
    ADD_COMMAND, HELP, PATH_OPTION, PRESET_OPTION, SVELTEKIT_PRESET,
};
use crate::target_command::models::AddRequest;

pub(crate) fn parse(arguments: &[String]) -> Result<AddRequest, String> {
    if arguments.first().map(String::as_str) != Some(ADD_COMMAND) {
        return Err(HELP.trim_end().to_owned());
    }
    let name = arguments
        .get(1)
        .filter(|value| !value.starts_with('-'))
        .cloned()
        .ok_or_else(|| "fensu target add requires NAME.".to_owned())?;
    if !valid_name(&name) {
        return Err("Target NAME must use portable ASCII letters, digits, '-' or '_'.".to_owned());
    }
    let mut preset: Option<String> = None;
    let mut path: Option<String> = None;
    let mut index = 2;
    while index < arguments.len() {
        let option = arguments[index].as_str();
        index += 1;
        let value = arguments
            .get(index)
            .filter(|value| !value.starts_with('-'))
            .cloned()
            .ok_or_else(|| format!("fensu target add: {option} requires one value."))?;
        match option {
            PRESET_OPTION if preset.is_none() => preset = Some(value),
            PATH_OPTION if path.is_none() => path = Some(value),
            PRESET_OPTION | PATH_OPTION => {
                return Err(format!(
                    "fensu target add: {option} may be supplied only once."
                ));
            }
            _ => return Err(format!("fensu target add: unknown option {option}.")),
        }
        index += 1;
    }
    if preset.as_deref() != Some(SVELTEKIT_PRESET) {
        return Err("fensu target add requires --preset sveltekit.".to_owned());
    }
    let path = path.ok_or_else(|| "fensu target add requires --path PATH.".to_owned())?;
    if !portable_path(&path) {
        return Err("--path must be a portable repository-relative directory.".to_owned());
    }
    Ok(AddRequest { name, path })
}

fn valid_name(value: &str) -> bool {
    !value.is_empty()
        && value
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || matches!(byte, b'-' | b'_'))
}

fn portable_path(value: &str) -> bool {
    let path = PathBuf::from(value);
    !path.is_absolute()
        && !value.contains('\\')
        && path
            .components()
            .all(|component| matches!(component, Component::Normal(_) | Component::CurDir))
}
