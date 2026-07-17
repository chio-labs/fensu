//! Exhaustive conversion of owned DuckDB query values.

use duckdb::types::{TimeUnit, Value};

use crate::engine::constants;
use crate::engine::errors::MemoryIndexError;
use crate::engine::models::MemoryQueryValue;

const TYPE_FIELD: &str = "$type";

pub(crate) fn encode(value: Value, depth: usize) -> Result<MemoryQueryValue, MemoryIndexError> {
    if depth > constants::MAX_QUERY_VALUE_DEPTH {
        return Err(MemoryIndexError::QueryValueTooDeep {
            depth,
            maximum_depth: constants::MAX_QUERY_VALUE_DEPTH,
        });
    }
    match value {
        Value::Null => Ok(MemoryQueryValue::Null),
        Value::Boolean(value) => Ok(MemoryQueryValue::Boolean(value)),
        Value::TinyInt(value) => Ok(integer(value)),
        Value::SmallInt(value) => Ok(integer(value)),
        Value::Int(value) => Ok(integer(value)),
        Value::BigInt(value) => Ok(integer(value)),
        Value::HugeInt(value) => Ok(integer(value)),
        Value::UTinyInt(value) => Ok(integer(value)),
        Value::USmallInt(value) => Ok(integer(value)),
        Value::UInt(value) => Ok(integer(value)),
        Value::UBigInt(value) => Ok(integer(value)),
        Value::Float(value) => Ok(float(f64::from(value))),
        Value::Double(value) => Ok(float(value)),
        Value::Decimal(value) => Ok(tagged(
            "decimal",
            vec![(
                "value".to_owned(),
                MemoryQueryValue::String(value.to_string()),
            )],
        )),
        Value::Timestamp(unit, value) => Ok(temporal("timestamp", unit, value)),
        Value::Text(value) => Ok(MemoryQueryValue::String(value)),
        Value::Blob(value) => Ok(tagged(
            "blob",
            vec![(
                "hex".to_owned(),
                MemoryQueryValue::String(hex::encode(value)),
            )],
        )),
        Value::Date32(value) => Ok(tagged("date", vec![("days".to_owned(), integer(value))])),
        Value::Time64(unit, value) => Ok(temporal("time", unit, value)),
        Value::Interval {
            months,
            days,
            nanos,
        } => Ok(tagged(
            "interval",
            vec![
                ("months".to_owned(), integer(months)),
                ("days".to_owned(), integer(days)),
                ("nanos".to_owned(), integer(nanos)),
            ],
        )),
        Value::List(values) => encode_sequence("list", values, depth),
        Value::Enum(value) => Ok(tagged(
            "enum",
            vec![("value".to_owned(), MemoryQueryValue::String(value))],
        )),
        Value::Struct(values) => encode_struct(values.iter(), depth),
        Value::Array(values) => encode_sequence("array", values, depth),
        Value::Map(values) => encode_map(values.iter(), depth),
        Value::Union(value) => Ok(tagged(
            "union",
            vec![("value".to_owned(), encode(*value, depth + 1)?)],
        )),
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

fn integer(value: impl ToString) -> MemoryQueryValue {
    MemoryQueryValue::Integer(value.to_string())
}

fn float(value: f64) -> MemoryQueryValue {
    if value.is_finite() {
        return MemoryQueryValue::Float(value);
    }
    let label = if value.is_nan() {
        "nan"
    } else if value.is_sign_positive() {
        "infinity"
    } else {
        "-infinity"
    };
    tagged(
        "float",
        vec![(
            "value".to_owned(),
            MemoryQueryValue::String(label.to_owned()),
        )],
    )
}

fn temporal(kind: &str, unit: TimeUnit, value: i64) -> MemoryQueryValue {
    tagged(
        kind,
        vec![
            (
                "unit".to_owned(),
                MemoryQueryValue::String(time_unit(unit).to_owned()),
            ),
            ("value".to_owned(), integer(value)),
        ],
    )
}

fn time_unit(unit: TimeUnit) -> &'static str {
    match unit {
        TimeUnit::Second => "second",
        TimeUnit::Millisecond => "millisecond",
        TimeUnit::Microsecond => "microsecond",
        TimeUnit::Nanosecond => "nanosecond",
    }
}

fn encode_sequence(
    kind: &str,
    values: Vec<Value>,
    depth: usize,
) -> Result<MemoryQueryValue, MemoryIndexError> {
    let mut encoded = Vec::with_capacity(values.len());
    for value in values {
        encoded.push(encode(value, depth + 1)?);
    }
    Ok(tagged(
        kind,
        vec![("values".to_owned(), MemoryQueryValue::Array(encoded))],
    ))
}

fn encode_struct<'value>(
    values: impl Iterator<Item = &'value (String, Value)>,
    depth: usize,
) -> Result<MemoryQueryValue, MemoryIndexError> {
    let mut fields = Vec::new();
    for (name, value) in values {
        fields.push((name.clone(), encode(value.clone(), depth + 1)?));
    }
    Ok(tagged(
        "struct",
        vec![("fields".to_owned(), MemoryQueryValue::Object(fields))],
    ))
}

fn encode_map<'value>(
    values: impl Iterator<Item = &'value (Value, Value)>,
    depth: usize,
) -> Result<MemoryQueryValue, MemoryIndexError> {
    let mut entries = Vec::new();
    for (key, value) in values {
        entries.push(MemoryQueryValue::Object(vec![
            ("key".to_owned(), encode(key.clone(), depth + 1)?),
            ("value".to_owned(), encode(value.clone(), depth + 1)?),
        ]));
    }
    Ok(tagged(
        "map",
        vec![("entries".to_owned(), MemoryQueryValue::Array(entries))],
    ))
}

fn tagged(kind: &str, mut fields: Vec<(String, MemoryQueryValue)>) -> MemoryQueryValue {
    let mut object = Vec::with_capacity(fields.len() + 1);
    object.push((
        TYPE_FIELD.to_owned(),
        MemoryQueryValue::String(kind.to_owned()),
    ));
    object.append(&mut fields);
    MemoryQueryValue::Object(object)
}
