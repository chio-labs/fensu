//! Canonical JSON encoding and hashing.

use serde::Serialize;
use serde_json::{Map, Value};
use sha2::{Digest, Sha256};

use crate::lifecycle::errors::LifecycleError;

pub(crate) fn canonical_json<T: Serialize>(value: &T) -> Result<Vec<u8>, LifecycleError> {
    let value = serde_json::to_value(value).map_err(serialization_error)?;
    serde_json::to_vec(&sorted_value(value)).map_err(serialization_error)
}

pub(crate) fn fingerprint<T: Serialize>(value: &T) -> Result<String, LifecycleError> {
    let encoded = canonical_json(value)?;
    Ok(format!("{:x}", Sha256::digest(encoded)))
}

pub(crate) fn batch_fingerprint<T: Serialize>(
    value: &T,
    supported_capabilities: &[String],
) -> Result<String, LifecycleError> {
    let mut value = serde_json::to_value(value).map_err(serialization_error)?;
    if let Some(object) = value.as_object_mut() {
        if let Some(capabilities) = object
            .get_mut("required_capabilities")
            .and_then(Value::as_array_mut)
        {
            capabilities.sort_by(|left, right| left.as_str().cmp(&right.as_str()));
            capabilities.dedup();
        }
        if let Some(inputs) = object.get_mut("inputs").and_then(Value::as_array_mut) {
            inputs.sort_by_key(input_sort_key);
        }
        let mut supported = supported_capabilities.to_vec();
        supported.sort();
        supported.dedup();
        object.insert(
            "supported_capabilities".to_owned(),
            Value::Array(supported.into_iter().map(Value::String).collect()),
        );
    }
    fingerprint(&value)
}

fn sorted_value(value: Value) -> Value {
    match value {
        Value::Array(values) => Value::Array(values.into_iter().map(sorted_value).collect()),
        Value::Object(values) => {
            let mut keys = values.keys().cloned().collect::<Vec<_>>();
            keys.sort();
            let mut sorted = Map::new();
            for key in keys {
                if let Some(value) = values.get(&key) {
                    sorted.insert(key, sorted_value(value.clone()));
                }
            }
            Value::Object(sorted)
        }
        scalar => scalar,
    }
}

fn input_sort_key(value: &Value) -> (String, String, String) {
    let object = value.as_object();
    let path = object
        .and_then(|item| item.get("path"))
        .and_then(Value::as_str)
        .unwrap_or_default()
        .to_owned();
    let fingerprint = object
        .and_then(|item| item.get("fingerprint"))
        .and_then(Value::as_str)
        .unwrap_or_default()
        .to_owned();
    let encoded = serde_json::to_string(&sorted_value(value.clone())).unwrap_or_default();
    (path, fingerprint, encoded)
}

fn serialization_error(error: serde_json::Error) -> LifecycleError {
    LifecycleError::Serialization {
        message: error.to_string(),
    }
}
