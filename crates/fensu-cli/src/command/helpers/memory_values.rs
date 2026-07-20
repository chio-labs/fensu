use std::fmt::Write;

use fensu_memory::engine::models::{MemoryGraphDirection, MemoryQueryValue};

const ANSI_BOLD_CYAN: &str = "\x1b[1;36m";
const ANSI_RESET: &str = "\x1b[0m";

pub(crate) fn heading(value: &str, color: bool) -> String {
    if color {
        format!("{ANSI_BOLD_CYAN}{value}{ANSI_RESET}")
    } else {
        value.to_owned()
    }
}

pub(crate) fn query_value(value: &MemoryQueryValue) -> String {
    match value {
        MemoryQueryValue::Null => "NULL".to_owned(),
        MemoryQueryValue::Boolean(value) => value.to_string(),
        MemoryQueryValue::Integer(value) | MemoryQueryValue::String(value) => value.clone(),
        MemoryQueryValue::Float(value) => python_float(*value),
        MemoryQueryValue::Array(_) | MemoryQueryValue::Object(_) => json_value(value, false, true),
    }
}

pub(crate) fn json_value(value: &MemoryQueryValue, ascii: bool, sort_objects: bool) -> String {
    match value {
        MemoryQueryValue::Null => "null".to_owned(),
        MemoryQueryValue::Boolean(value) => value.to_string(),
        MemoryQueryValue::Integer(value) => value.clone(),
        MemoryQueryValue::Float(value) if value.is_finite() => python_float(*value),
        MemoryQueryValue::Float(value) => json_string(&python_float(*value), ascii),
        MemoryQueryValue::String(value) => json_string(value, ascii),
        MemoryQueryValue::Array(values) => format!(
            "[{}]",
            values
                .iter()
                .map(|value| json_value(value, ascii, sort_objects))
                .collect::<Vec<_>>()
                .join(",")
        ),
        MemoryQueryValue::Object(fields) => {
            let mut fields = fields.iter().collect::<Vec<_>>();
            if sort_objects {
                fields.sort_by(|left, right| left.0.cmp(&right.0));
            }
            format!(
                "{{{}}}",
                fields
                    .iter()
                    .map(|(name, value)| format!(
                        "{}:{}",
                        json_string(name, ascii),
                        json_value(value, ascii, sort_objects)
                    ))
                    .collect::<Vec<_>>()
                    .join(",")
            )
        }
    }
}

pub(crate) fn json_string(value: &str, ascii: bool) -> String {
    if !ascii {
        return match serde_json::to_string(value) {
            Ok(serialized) => serialized,
            Err(_) => String::from("\"\""),
        };
    }
    let mut output = String::from("\"");
    for character in value.chars() {
        match character {
            '"' => output.push_str("\\\""),
            '\\' => output.push_str("\\\\"),
            '\u{08}' => output.push_str("\\b"),
            '\u{0c}' => output.push_str("\\f"),
            '\n' => output.push_str("\\n"),
            '\r' => output.push_str("\\r"),
            '\t' => output.push_str("\\t"),
            '\u{00}'..='\u{1f}' => {
                let _ = write!(output, "\\u{:04x}", u32::from(character));
            }
            character if character.is_ascii() => output.push(character),
            character => {
                let mut units = [0_u16; 2];
                for unit in character.encode_utf16(&mut units) {
                    let _ = write!(output, "\\u{unit:04x}");
                }
            }
        }
    }
    output.push('"');
    output
}

pub(crate) fn direction_name(direction: MemoryGraphDirection) -> &'static str {
    match direction {
        MemoryGraphDirection::Outbound => "outbound",
        MemoryGraphDirection::Inbound => "inbound",
        MemoryGraphDirection::Both => "both",
    }
}

fn python_float(value: f64) -> String {
    if value.is_nan() {
        "nan".to_owned()
    } else if value == f64::INFINITY {
        "inf".to_owned()
    } else if value == f64::NEG_INFINITY {
        "-inf".to_owned()
    } else {
        match serde_json::to_string(&value) {
            Ok(serialized) => serialized,
            Err(_) => value.to_string(),
        }
    }
}
