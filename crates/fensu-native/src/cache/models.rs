//! Native cache operation models.

#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) enum CanonicalValue {
    Null,
    Bool(bool),
    Integer(String),
    String(String),
    List(Vec<CanonicalValue>),
    Object(Vec<(String, CanonicalValue)>),
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct NativeIndexEntry {
    pub path: String,
    pub source_fingerprint: String,
    pub result_fingerprint: String,
    pub record_fingerprint: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub(crate) struct NativeDependencyKey {
    pub query_path: String,
    pub kind: String,
    pub pattern: Option<String>,
    pub recursive: bool,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct NativeDependencyObservation {
    pub requester_path: String,
    pub key: NativeDependencyKey,
    pub dependency_path: String,
    pub answer: CanonicalValue,
}

#[derive(Debug)]
pub(crate) struct NativeGenerationPlan {
    pub mode: String,
    pub index_fingerprint: Option<String>,
    pub entries: Vec<NativeIndexEntry>,
    pub cached_results: Vec<CanonicalValue>,
    pub contributions: Vec<CanonicalValue>,
    pub miss_paths: Vec<String>,
    pub hits: usize,
    pub misses: usize,
    pub invalidations: usize,
}

#[derive(Debug)]
pub(crate) struct NativePublicationCandidate {
    pub path: String,
    pub source_fingerprint: String,
    pub payload: CanonicalValue,
    pub contribution: Option<CanonicalValue>,
    pub observations: Vec<NativeDependencyObservation>,
}

#[derive(Debug, Default)]
pub(crate) struct NativePublicationPreparation {
    pub candidates: Vec<NativePublicationCandidate>,
    pub non_cacheable: usize,
    pub internal_error: bool,
}

#[derive(Debug, Default)]
pub(crate) struct NativePublicationResult {
    pub writes: usize,
    pub non_cacheable: usize,
    pub storage_failed: bool,
    pub internal_error: bool,
    pub index_fingerprint: Option<String>,
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
