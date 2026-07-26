//! Strictly decode bounded PEP 263 aliases without consulting CPython's codec registry.

use encoding_rs::Encoding;

use crate::mapping::models::SourceSnapshot;

pub(crate) fn decode_source(snapshot: &SourceSnapshot) -> Result<String, String> {
    let bytes = snapshot.source.as_slice();
    let (encoding, offset) = if bytes.starts_with(&[0xef, 0xbb, 0xbf]) {
        ("utf-8", 3)
    } else {
        (detect_cookie(bytes).unwrap_or("utf-8"), 0)
    };
    let normalized = normalize_encoding(encoding);
    let decoded = match normalized.as_str() {
        "utf8" => std::str::from_utf8(&bytes[offset..])
            .map(str::to_owned)
            .map_err(|_| "invalid or missing encoding declaration".to_owned()),
        "ascii" => decode_ascii(&bytes[offset..]),
        "latin1" => Ok(bytes[offset..]
            .iter()
            .map(|byte| char::from(*byte))
            .collect()),
        _ => decode_registered(&bytes[offset..], encoding),
    };
    decoded
        .map(|text| text.replace("\r\n", "\n").replace('\r', "\n"))
        .map_err(|message| format!("Could not parse {}: {message}", snapshot.path.display()))
}

fn decode_ascii(bytes: &[u8]) -> Result<String, String> {
    if bytes.iter().all(u8::is_ascii) {
        Ok(bytes.iter().map(|byte| char::from(*byte)).collect())
    } else {
        Err("source is not valid ASCII".to_owned())
    }
}

fn decode_registered(bytes: &[u8], name: &str) -> Result<String, String> {
    let Some(encoding) = Encoding::for_label(name.as_bytes()) else {
        return Err(format!(
            "unsupported Python source encoding '{name}'; native map supports UTF-8, ASCII, Latin-1, and strict encoding_rs labels"
        ));
    };
    encoding
        .decode_without_bom_handling_and_without_replacement(bytes)
        .map(|decoded| decoded.into_owned())
        .ok_or_else(|| format!("source is not valid {}", encoding.name()))
}

fn detect_cookie(bytes: &[u8]) -> Option<&str> {
    let first_two = bytes.split(|byte| *byte == b'\n').take(2);
    for line in first_two {
        let Ok(ascii) = std::str::from_utf8(line) else {
            continue;
        };
        let Some(marker) = ascii.find("coding") else {
            continue;
        };
        let Some(rest) = ascii.get(marker + "coding".len()..) else {
            continue;
        };
        let rest = rest.trim_start();
        let Some(rest) = rest.strip_prefix(':').or_else(|| rest.strip_prefix('=')) else {
            continue;
        };
        let value = rest.trim_start();
        let end = value
            .find(|character: char| {
                !(character.is_ascii_alphanumeric() || "-_.".contains(character))
            })
            .unwrap_or(value.len());
        if end > 0 {
            return value.get(..end);
        }
    }
    None
}

fn normalize_encoding(value: &str) -> String {
    let normalized = value.to_ascii_lowercase().replace(['-', '_'], "");
    match normalized.as_str() {
        "utf8" | "utf8sig" => "utf8".to_owned(),
        "ascii" | "usascii" | "646" => "ascii".to_owned(),
        "latin1" | "iso88591" | "cp819" | "l1" => "latin1".to_owned(),
        _ => normalized,
    }
}
