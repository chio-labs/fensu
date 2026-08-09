use crate::configuration::_helpers::validation;

pub(crate) fn validate_document(text: &str, pyproject: bool) -> Result<(), String> {
    let document = toml::from_slice::<toml::Value>(text.as_bytes())
        .map_err(|error| format!("Configuration is not valid TOML: {error}"))?;
    let value = if pyproject {
        document
            .get("tool")
            .and_then(|value| value.get("fensu"))
            .ok_or_else(|| "pyproject.toml does not contain [tool.fensu].".to_owned())?
    } else {
        &document
    };
    let table = value
        .as_table()
        .ok_or_else(|| "Configuration did not contain a TOML table.".to_owned())?;
    validation::validate_without_selection(table)
}
