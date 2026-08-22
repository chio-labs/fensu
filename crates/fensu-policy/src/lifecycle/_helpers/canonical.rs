//! Canonical JSON encoding and hashing.

use serde::Serialize;
use serde_json::{Map, Value};
use sha2::{Digest, Sha256};

use crate::lifecycle::constants::CACHE_IDENTITY_SCHEMA_VERSION;
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
        let mut supported = supported_capabilities.to_vec();
        supported.sort();
        supported.dedup();
        object.insert(
            "cache_identity_schema".to_owned(),
            Value::from(CACHE_IDENTITY_SCHEMA_VERSION),
        );
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

fn serialization_error(error: serde_json::Error) -> LifecycleError {
    LifecycleError::Serialization {
        message: error.to_string(),
    }
}
