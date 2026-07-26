//! Canonical cache record encoding, decoding, and Python conversion.

use std::io::{Read, Write};

use flate2::bufread::ZlibDecoder;
use flate2::write::ZlibEncoder;
use flate2::Compression;
use pyo3::exceptions::PyValueError;
use pyo3::types::{
    PyAnyMethods, PyBool, PyBoolMethods, PyDict, PyDictMethods, PyInt, PyList, PyListMethods,
    PyString, PyStringMethods,
};
use pyo3::{Bound, IntoPyObject, Py, PyAny, PyErr, PyResult, Python};
use serde_json::Value;
use sha2::{Digest, Sha256};

use crate::cache::constants::{
    COMPRESSED_PREFIX, COMPRESSION_LEVEL, COMPRESSION_THRESHOLD, ENVELOPE_KEY_COUNT,
    MAXIMUM_BASIC_MULTILINGUAL_PLANE, RECORD_SCHEMA_VERSION,
};
use crate::cache::models::{CanonicalValue, DecodedRecord};

pub(crate) fn encode_record(
    kind: &str,
    payload: &Bound<'_, PyAny>,
    payload_is_validated: bool,
    maximum_decoded_bytes: usize,
) -> PyResult<Vec<u8>> {
    if kind.is_empty() {
        return Err(record_error());
    }
    let mut canonical = canonical_from_python(payload)?;
    if !payload_is_validated {
        sort_objects(&mut canonical);
    }
    let mut encoded = Vec::new();
    encoded.extend_from_slice(b"{\"kind\":");
    write_string(kind, &mut encoded);
    encoded.extend_from_slice(b",\"payload\":");
    write_value(&canonical, &mut encoded);
    encoded.extend_from_slice(b",\"schema_version\":4}");
    if encoded.len() > maximum_decoded_bytes {
        return Err(PyValueError::new_err(
            "Cache record exceeds the decoded size limit.",
        ));
    }
    if encoded.len() < COMPRESSION_THRESHOLD {
        return Ok(encoded);
    }
    let mut compressor = ZlibEncoder::new(Vec::new(), Compression::new(COMPRESSION_LEVEL));
    compressor
        .write_all(&encoded)
        .map_err(|_| PyValueError::new_err("Cache record compression failed."))?;
    let compressed = compressor
        .finish()
        .map_err(|_| PyValueError::new_err("Cache record compression failed."))?;
    let mut framed = Vec::with_capacity(COMPRESSED_PREFIX.len() + compressed.len());
    framed.extend_from_slice(COMPRESSED_PREFIX);
    framed.extend_from_slice(&compressed);
    Ok(framed)
}

pub(crate) fn decode_record(
    data: &[u8],
    expected_kind: &str,
    maximum_decoded_bytes: usize,
) -> Option<DecodedRecord> {
    let encoded = decompressed(data, maximum_decoded_bytes)?;
    let value: Value = serde_json::from_slice(&encoded).ok()?;
    let envelope = value.as_object()?;
    if envelope.len() != ENVELOPE_KEY_COUNT {
        return None;
    }
    let kind = envelope.get("kind")?.as_str()?;
    if kind.is_empty() || kind != expected_kind {
        return None;
    }
    if envelope.get("schema_version")?.as_i64()? != RECORD_SCHEMA_VERSION {
        return None;
    }
    let payload = canonical_from_json(envelope.get("payload")?)?;
    let canonical = encode_decoded(kind, &payload, maximum_decoded_bytes)?;
    if canonical != data {
        return None;
    }
    Some(DecodedRecord {
        kind: kind.to_owned(),
        payload,
        fingerprint: hex_digest(data),
    })
}

pub(crate) fn value_to_python(py: Python<'_>, value: CanonicalValue) -> PyResult<Py<PyAny>> {
    match value {
        CanonicalValue::Null => Ok(py.None()),
        CanonicalValue::Bool(value) => Ok(value.into_pyobject(py)?.to_owned().unbind().into_any()),
        CanonicalValue::Integer(value) => {
            let builtins = py.import("builtins")?;
            Ok(builtins.getattr("int")?.call1((value,))?.unbind())
        }
        CanonicalValue::String(value) => {
            Ok(value.into_pyobject(py)?.to_owned().unbind().into_any())
        }
        CanonicalValue::List(values) => {
            let result = PyList::empty(py);
            for value in values {
                result.append(value_to_python(py, value)?)?;
            }
            Ok(result.unbind().into_any())
        }
        CanonicalValue::Object(entries) => {
            let result = PyDict::new(py);
            for (key, value) in entries {
                result.set_item(key, value_to_python(py, value)?)?;
            }
            Ok(result.unbind().into_any())
        }
    }
}

pub(crate) fn encode_canonical_record(
    kind: &str,
    payload: &CanonicalValue,
    maximum_decoded_bytes: usize,
) -> Option<Vec<u8>> {
    let mut canonical = payload.clone();
    sort_objects(&mut canonical);
    encode_decoded(kind, &canonical, maximum_decoded_bytes)
}

pub(crate) fn content_fingerprint(data: &[u8]) -> String {
    hex_digest(data)
}

fn encode_decoded(
    kind: &str,
    payload: &CanonicalValue,
    maximum_decoded_bytes: usize,
) -> Option<Vec<u8>> {
    let mut encoded = Vec::new();
    encoded.extend_from_slice(b"{\"kind\":");
    write_string(kind, &mut encoded);
    encoded.extend_from_slice(b",\"payload\":");
    write_value(payload, &mut encoded);
    encoded.extend_from_slice(b",\"schema_version\":4}");
    if encoded.len() > maximum_decoded_bytes {
        return None;
    }
    if encoded.len() < COMPRESSION_THRESHOLD {
        return Some(encoded);
    }
    let mut compressor = ZlibEncoder::new(Vec::new(), Compression::new(COMPRESSION_LEVEL));
    compressor.write_all(&encoded).ok()?;
    let compressed = compressor.finish().ok()?;
    let mut framed = Vec::with_capacity(COMPRESSED_PREFIX.len() + compressed.len());
    framed.extend_from_slice(COMPRESSED_PREFIX);
    framed.extend_from_slice(&compressed);
    Some(framed)
}

fn decompressed(data: &[u8], maximum_decoded_bytes: usize) -> Option<Vec<u8>> {
    if !data.starts_with(COMPRESSED_PREFIX) {
        return (data.len() <= maximum_decoded_bytes).then(|| data.to_vec());
    }
    let compressed = &data[COMPRESSED_PREFIX.len()..];
    let mut decoder = ZlibDecoder::new(compressed);
    let mut decoded = Vec::new();
    decoder
        .by_ref()
        .take(maximum_decoded_bytes.saturating_add(1) as u64)
        .read_to_end(&mut decoded)
        .ok()?;
    if decoded.len() > maximum_decoded_bytes || decoder.total_in() as usize != compressed.len() {
        return None;
    }
    Some(decoded)
}

pub(crate) fn canonical_from_python(value: &Bound<'_, PyAny>) -> PyResult<CanonicalValue> {
    if value.is_none() {
        return Ok(CanonicalValue::Null);
    }
    if let Ok(boolean) = value.cast::<PyBool>() {
        return Ok(CanonicalValue::Bool(boolean.is_true()));
    }
    if value.cast::<PyInt>().is_ok() {
        return Ok(CanonicalValue::Integer(value.str()?.to_str()?.to_owned()));
    }
    if let Ok(string) = value.cast::<PyString>() {
        return Ok(CanonicalValue::String(string.to_str()?.to_owned()));
    }
    if let Ok(list) = value.cast::<PyList>() {
        let mut values = Vec::with_capacity(list.len());
        for item in list.iter() {
            values.push(canonical_from_python(&item)?);
        }
        return Ok(CanonicalValue::List(values));
    }
    if let Ok(mapping) = value.cast::<PyDict>() {
        let mut entries = Vec::with_capacity(mapping.len());
        for (key, item) in mapping.iter() {
            let key = key
                .cast::<PyString>()
                .map_err(|_| record_error())?
                .to_str()?
                .to_owned();
            entries.push((key, canonical_from_python(&item)?));
        }
        return Ok(CanonicalValue::Object(entries));
    }
    Err(record_error())
}

fn canonical_from_json(value: &Value) -> Option<CanonicalValue> {
    match value {
        Value::Null => Some(CanonicalValue::Null),
        Value::Bool(value) => Some(CanonicalValue::Bool(*value)),
        Value::Number(value) if value.is_i64() || value.is_u64() => {
            Some(CanonicalValue::Integer(value.to_string()))
        }
        Value::Number(_) => None,
        Value::String(value) => Some(CanonicalValue::String(value.clone())),
        Value::Array(values) => Some(CanonicalValue::List(
            values
                .iter()
                .map(canonical_from_json)
                .collect::<Option<Vec<_>>>()?,
        )),
        Value::Object(entries) => Some(CanonicalValue::Object(
            entries
                .iter()
                .map(|(key, value)| Some((key.clone(), canonical_from_json(value)?)))
                .collect::<Option<Vec<_>>>()?,
        )),
    }
}

fn sort_objects(value: &mut CanonicalValue) {
    match value {
        CanonicalValue::List(values) => values.iter_mut().for_each(sort_objects),
        CanonicalValue::Object(entries) => {
            entries
                .iter_mut()
                .for_each(|(_, value)| sort_objects(value));
            entries.sort_by(|left, right| left.0.cmp(&right.0));
        }
        _ => {}
    }
}

fn write_value(value: &CanonicalValue, output: &mut Vec<u8>) {
    match value {
        CanonicalValue::Null => output.extend_from_slice(b"null"),
        CanonicalValue::Bool(true) => output.extend_from_slice(b"true"),
        CanonicalValue::Bool(false) => output.extend_from_slice(b"false"),
        CanonicalValue::Integer(value) => output.extend_from_slice(value.as_bytes()),
        CanonicalValue::String(value) => write_string(value, output),
        CanonicalValue::List(values) => {
            output.push(b'[');
            for (index, value) in values.iter().enumerate() {
                if index > 0 {
                    output.push(b',');
                }
                write_value(value, output);
            }
            output.push(b']');
        }
        CanonicalValue::Object(entries) => {
            output.push(b'{');
            for (index, (key, value)) in entries.iter().enumerate() {
                if index > 0 {
                    output.push(b',');
                }
                write_string(key, output);
                output.push(b':');
                write_value(value, output);
            }
            output.push(b'}');
        }
    }
}

fn write_string(value: &str, output: &mut Vec<u8>) {
    output.push(b'"');
    for character in value.chars() {
        match character {
            '"' => output.extend_from_slice(b"\\\""),
            '\\' => output.extend_from_slice(b"\\\\"),
            '\u{08}' => output.extend_from_slice(b"\\b"),
            '\u{0c}' => output.extend_from_slice(b"\\f"),
            '\n' => output.extend_from_slice(b"\\n"),
            '\r' => output.extend_from_slice(b"\\r"),
            '\t' => output.extend_from_slice(b"\\t"),
            character if character <= '\u{7f}' && !character.is_control() => {
                output.push(character as u8);
            }
            character if (character as u32) <= MAXIMUM_BASIC_MULTILINGUAL_PLANE => {
                let _ = write!(output, "\\u{:04x}", character as u32);
            }
            character => {
                let scalar = character as u32 - 0x1_0000;
                let high = 0xd800 + (scalar >> 10);
                let low = 0xdc00 + (scalar & 0x3ff);
                let _ = write!(output, "\\u{high:04x}\\u{low:04x}");
            }
        }
    }
    output.push(b'"');
}

fn hex_digest(data: &[u8]) -> String {
    format!("{:x}", Sha256::digest(data))
}

fn record_error() -> PyErr {
    PyValueError::new_err("Cache records require a nonempty kind and canonical payload.")
}
