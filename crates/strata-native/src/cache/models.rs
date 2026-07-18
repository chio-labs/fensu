//! Native cache operation models.

#[derive(Debug)]
pub(crate) enum CanonicalValue {
    Null,
    Bool(bool),
    Integer(String),
    String(String),
    List(Vec<CanonicalValue>),
    Object(Vec<(String, CanonicalValue)>),
}

impl CanonicalValue {
    pub(crate) fn as_object(&self) -> Option<&[(String, CanonicalValue)]> {
        match self {
            Self::Object(entries) => Some(entries),
            _ => None,
        }
    }

    pub(crate) fn as_list(&self) -> Option<&[CanonicalValue]> {
        match self {
            Self::List(values) => Some(values),
            _ => None,
        }
    }

    pub(crate) fn as_str(&self) -> Option<&str> {
        match self {
            Self::String(value) => Some(value),
            _ => None,
        }
    }

    pub(crate) fn as_bool(&self) -> Option<bool> {
        match self {
            Self::Bool(value) => Some(*value),
            _ => None,
        }
    }

    pub(crate) fn as_nonnegative_i64(&self) -> Option<i64> {
        match self {
            Self::Integer(value) => value.parse::<i64>().ok().filter(|value| *value >= 0),
            _ => None,
        }
    }

    pub(crate) fn is_null(&self) -> bool {
        matches!(self, Self::Null)
    }

    pub(crate) fn field(&self, name: &str) -> Option<&CanonicalValue> {
        self.as_object()?
            .iter()
            .find_map(|(key, value)| (key == name).then_some(value))
    }
}

#[derive(Debug)]
pub(crate) struct DecodedRecord {
    pub kind: String,
    pub payload: CanonicalValue,
    pub fingerprint: String,
}

#[derive(Debug)]
pub(crate) struct EncodedWrite {
    pub key: String,
    pub kind: String,
    pub data: Vec<u8>,
    pub insert_only: bool,
}

#[derive(Debug)]
pub(crate) struct CacheMutation {
    pub writes: Vec<EncodedWrite>,
    pub swept_prefix: Option<String>,
    pub retained_paths: Vec<String>,
    pub deleted_paths: Vec<String>,
}

#[derive(Debug, Default)]
pub(crate) struct CacheMetrics {
    pub reads: usize,
    pub bytes_read: usize,
    pub writes: usize,
    pub bytes_written: usize,
    pub scans: usize,
    pub deletes: usize,
}

#[derive(Debug)]
pub(crate) struct NativeReplay {
    pub targets: Vec<String>,
    pub plain_output: String,
    pub color_output: String,
    pub exit_code: i64,
    pub index_fingerprint: String,
}
