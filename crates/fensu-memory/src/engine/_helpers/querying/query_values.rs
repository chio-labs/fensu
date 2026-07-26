//! Conversion of SQLite query values into stable public values.

use rusqlite::types::ValueRef;

use crate::engine::models::MemoryQueryValue;

pub(crate) fn encode(value: ValueRef<'_>) -> MemoryQueryValue {
    match value {
        ValueRef::Null => MemoryQueryValue::Null,
        ValueRef::Integer(value) => MemoryQueryValue::Integer(value.to_string()),
        ValueRef::Real(value) => MemoryQueryValue::Float(value),
        ValueRef::Text(value) => {
            MemoryQueryValue::String(String::from_utf8_lossy(value).into_owned())
        }
        ValueRef::Blob(value) => MemoryQueryValue::Object(vec![
            (
                "$type".to_owned(),
                MemoryQueryValue::String("blob".to_owned()),
            ),
            (
                "hex".to_owned(),
                MemoryQueryValue::String(hex::encode(value)),
            ),
        ]),
    }
}

pub(crate) fn type_name(value: ValueRef<'_>) -> &'static str {
    match value {
        ValueRef::Null => "Null",
        ValueRef::Integer(_) => "Integer",
        ValueRef::Real(_) => "Real",
        ValueRef::Text(_) => "Text",
        ValueRef::Blob(_) => "Blob",
    }
}

pub(crate) fn approximate_bytes(value: &MemoryQueryValue) -> usize {
    match value {
        MemoryQueryValue::Null => 4,
        MemoryQueryValue::Boolean(_) => 5,
        MemoryQueryValue::Integer(value) | MemoryQueryValue::String(value) => value.len() + 2,
        MemoryQueryValue::Float(value) => value.to_string().len(),
        MemoryQueryValue::Array(values) => {
            values.iter().map(approximate_bytes).sum::<usize>() + values.len() + 2
        }
        MemoryQueryValue::Object(fields) => {
            fields
                .iter()
                .map(|(name, value)| name.len() + approximate_bytes(value) + 3)
                .sum::<usize>()
                + fields.len()
                + 2
        }
    }
}
