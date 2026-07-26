//! Exact canonical timestamp, category, slug, and skill-name validation.

use crate::source::constants;
use crate::source::models::ParsedDocumentName;
use crate::source::types::{ArtifactKind, DiagnosticKind, TaskCategory, TaskLifecycle};

pub(crate) fn parse_document_name(
    basename: &str,
    artifact_kind: ArtifactKind,
) -> Result<ParsedDocumentName, DiagnosticKind> {
    let stem = basename
        .strip_suffix(constants::MARKDOWN_SUFFIX)
        .ok_or(DiagnosticKind::InvalidDocumentName)?;
    let (timestamp, classified_name) = stem
        .split_once(constants::NAME_SEPARATOR)
        .ok_or(DiagnosticKind::InvalidDocumentName)?;
    validate_timestamp(timestamp)?;
    let (category, slug) = match artifact_kind {
        ArtifactKind::Task => task_name_parts(classified_name)?,
        ArtifactKind::Note => prefixed_slug(classified_name, constants::NOTE_PREFIX)?,
        ArtifactKind::Decision => prefixed_slug(classified_name, constants::DECISION_PREFIX)?,
        ArtifactKind::Skill => return Err(DiagnosticKind::InvalidDocumentName),
    };
    validate_kebab(slug)?;
    Ok(ParsedDocumentName {
        timestamp: timestamp.to_owned(),
        slug: slug.to_owned(),
        category,
    })
}

pub(crate) fn validate_skill_name(name: &str) -> Result<(), DiagnosticKind> {
    validate_kebab(name)?;
    match windows_reserved_name(name) {
        true => Err(DiagnosticKind::InvalidPlatformName),
        false => Ok(()),
    }
}

pub(crate) fn active_lifecycle(name: &str) -> Option<TaskLifecycle> {
    match name {
        constants::NOT_STARTED_DIRECTORY => Some(TaskLifecycle::NotStarted),
        constants::IN_PROGRESS_DIRECTORY => Some(TaskLifecycle::InProgress),
        constants::COMPLETED_DIRECTORY => Some(TaskLifecycle::Completed),
        constants::CANCELLED_DIRECTORY => Some(TaskLifecycle::Cancelled),
        constants::SUPERSEDED_DIRECTORY => Some(TaskLifecycle::Superseded),
        _ => None,
    }
}

pub(crate) fn archived_lifecycle(name: &str) -> Option<TaskLifecycle> {
    match name {
        constants::COMPLETED_DIRECTORY => Some(TaskLifecycle::Completed),
        constants::CANCELLED_DIRECTORY => Some(TaskLifecycle::Cancelled),
        constants::SUPERSEDED_DIRECTORY => Some(TaskLifecycle::Superseded),
        _ => None,
    }
}

fn task_name_parts(name: &str) -> Result<(Option<TaskCategory>, &str), DiagnosticKind> {
    let categories = [
        (constants::SPIKE_PREFIX, TaskCategory::Spike),
        (constants::FIX_PREFIX, TaskCategory::Fix),
        (constants::PERF_PREFIX, TaskCategory::Performance),
        (constants::FEAT_PREFIX, TaskCategory::Feature),
        (constants::REFACTOR_PREFIX, TaskCategory::Refactor),
        (constants::CHORE_PREFIX, TaskCategory::Chore),
    ];
    for (prefix, category) in categories {
        if let Some(slug) = name.strip_prefix(prefix) {
            return Ok((Some(category), slug));
        }
    }
    Err(DiagnosticKind::InvalidTaskCategory)
}

fn prefixed_slug<'name>(
    name: &'name str,
    prefix: &str,
) -> Result<(Option<TaskCategory>, &'name str), DiagnosticKind> {
    name.strip_prefix(prefix)
        .map(|slug| (None, slug))
        .ok_or(DiagnosticKind::InvalidArtifactPrefix)
}

fn validate_kebab(value: &str) -> Result<(), DiagnosticKind> {
    let bytes = value.as_bytes();
    let valid = !bytes.is_empty()
        && bytes.first().is_some_and(u8::is_ascii_lowercase)
        && bytes.last().is_some_and(u8::is_ascii_alphanumeric)
        && bytes
            .iter()
            .all(|byte| byte.is_ascii_lowercase() || byte.is_ascii_digit() || *byte == b'-')
        && !bytes.windows(2).any(|pair| pair == b"--");
    match valid {
        true => Ok(()),
        false => Err(DiagnosticKind::InvalidSlug),
    }
}

fn validate_timestamp(value: &str) -> Result<(), DiagnosticKind> {
    let bytes = value.as_bytes();
    let separators_valid = bytes.len() == constants::TIMESTAMP_LENGTH
        && bytes.get(constants::DATE_LENGTH) == Some(&b'T')
        && bytes.get(constants::SECOND_START + constants::TWO_DIGITS) == Some(&b'_')
        && bytes.last() == Some(&b'Z');
    if !separators_valid || !timestamp_digits_valid(bytes) {
        return Err(DiagnosticKind::InvalidTimestamp);
    }
    let year = number(bytes, 0, constants::FOUR_DIGITS);
    let month = number(bytes, constants::MONTH_START, constants::TWO_DIGITS);
    let day = number(bytes, constants::DAY_START, constants::TWO_DIGITS);
    let hour = number(bytes, constants::HOUR_START, constants::TWO_DIGITS);
    let minute = number(bytes, constants::MINUTE_START, constants::TWO_DIGITS);
    let second = number(bytes, constants::SECOND_START, constants::TWO_DIGITS);
    let valid = match (year, month, day, hour, minute, second) {
        (Some(year), Some(month), Some(day), Some(hour), Some(minute), Some(second)) => {
            calendar_valid(year, month, day)
                && hour <= constants::MAX_HOUR
                && minute <= constants::MAX_MINUTE
                && second <= constants::MAX_SECOND
        }
        _ => false,
    };
    match valid {
        true => Ok(()),
        false => Err(DiagnosticKind::InvalidTimestamp),
    }
}

fn timestamp_digits_valid(bytes: &[u8]) -> bool {
    bytes[..constants::DATE_LENGTH]
        .iter()
        .chain(bytes[constants::HOUR_START..constants::SECOND_START + constants::TWO_DIGITS].iter())
        .chain(bytes[constants::FRACTION_START..constants::FRACTION_END].iter())
        .all(u8::is_ascii_digit)
}

fn number(bytes: &[u8], start: usize, length: usize) -> Option<u32> {
    let mut value = 0_u32;
    for byte in bytes.get(start..start + length)? {
        value = value
            .checked_mul(10)?
            .checked_add(u32::from(byte.checked_sub(b'0')?))?;
    }
    Some(value)
}

fn calendar_valid(year: u32, month: u32, day: u32) -> bool {
    if month == 0 || month > constants::MONTHS_PER_YEAR || day == 0 {
        return false;
    }
    day <= days_in_month(year, month)
}

fn days_in_month(year: u32, month: u32) -> u32 {
    match month {
        1 | 3 | 5 | 7 | 8 | 10 | 12 => 31,
        4 | 6 | 9 | 11 => 30,
        2 if leap_year(year) => 29,
        2 => 28,
        _ => 0,
    }
}

fn leap_year(year: u32) -> bool {
    year.is_multiple_of(4) && (!year.is_multiple_of(100) || year.is_multiple_of(400))
}

fn windows_reserved_name(name: &str) -> bool {
    match name {
        "con" | "prn" | "aux" | "nul" => true,
        _ => {
            let bytes = name.as_bytes();
            let numbered_device = bytes.len() == constants::WINDOWS_DEVICE_NAME_LENGTH
                && bytes
                    .get(..3)
                    .is_some_and(|prefix| prefix == b"com" || prefix == b"lpt")
                && bytes
                    .last()
                    .is_some_and(|digit| (b'1'..=b'9').contains(digit));
            numbered_device
        }
    }
}
