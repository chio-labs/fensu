use crate::configuration::_helpers::validation;

pub(crate) fn validate_document(text: &str) -> Result<(), String> {
    let document = toml::from_slice::<toml::Value>(text.as_bytes())
        .map_err(|error| format!("Configuration is not valid TOML: {error}"))?;
    let table = document
        .as_table()
        .ok_or_else(|| "Configuration did not contain a TOML table.".to_owned())?;
    validation::validate(table)
}
