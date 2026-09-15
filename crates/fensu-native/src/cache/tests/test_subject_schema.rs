//! Subject-specific result validation contracts.

use crate::cache::_helpers::schema_values::{decode_subject_exceptions, decode_subject_faults};
use crate::cache::models::CanonicalValue;
use crate::cache::tests::_helpers::object;

fn fault(path: &str) -> CanonicalValue {
    object(&[
        ("code", CanonicalValue::String("XPC001".to_owned())),
        ("column", CanonicalValue::Null),
        ("line", CanonicalValue::Null),
        (
            "message",
            CanonicalValue::String("project finding".to_owned()),
        ),
        ("path", CanonicalValue::String(path.to_owned())),
        ("remediation", CanonicalValue::Null),
    ])
}

fn exception(path: &str) -> CanonicalValue {
    object(&[
        ("path", CanonicalValue::String(path.to_owned())),
        ("rule", CanonicalValue::String("XPC001".to_owned())),
        ("symbol", CanonicalValue::Null),
    ])
}

#[test]
fn given_file_and_project_subjects_when_validating_outputs_then_ownership_is_kind_specific() {
    let foreign_faults = CanonicalValue::List(vec![fault("src/example/other.py")]);
    let foreign_exceptions = CanonicalValue::List(vec![exception("src/example/other.py")]);

    assert!(decode_subject_faults(&foreign_faults, "src/example/owner.py", true).is_none());
    assert!(decode_subject_exceptions(&foreign_exceptions, "src/example/owner.py", true).is_none());
    assert!(decode_subject_faults(&foreign_faults, ".", false).is_some());
    assert!(decode_subject_exceptions(&foreign_exceptions, ".", false).is_some());
}

#[test]
fn given_project_subject_when_output_escapes_repository_then_validation_rejects_it() {
    let faults = CanonicalValue::List(vec![fault("../outside.py")]);
    let exceptions = CanonicalValue::List(vec![exception("../outside.py")]);

    assert!(decode_subject_faults(&faults, ".", false).is_none());
    assert!(decode_subject_exceptions(&exceptions, ".", false).is_none());
}
