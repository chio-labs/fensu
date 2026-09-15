//! Subject-specific result validation contracts.

use crate::cache::_helpers::schema_values::{decode_subject_exceptions, decode_subject_faults};
use crate::cache::models::CanonicalValue;
use crate::cache::tests::_helpers::{subject_exception, subject_fault};
use crate::cache::tests::test_types::SubjectSchemaTestCase;

#[test]
fn given_subject_outputs_when_validating_then_ownership_is_kind_specific() {
    let test_cases = [
        SubjectSchemaTestCase {
            description: "file faults must belong to the file subject",
            value_path: "src/example/other.py",
            owner: "src/example/owner.py",
            strict_owner: true,
            expected_faults_valid: false,
            expected_exceptions_valid: false,
        },
        SubjectSchemaTestCase {
            description: "project faults may belong to repository files",
            value_path: "src/example/other.py",
            owner: ".",
            strict_owner: false,
            expected_faults_valid: true,
            expected_exceptions_valid: true,
        },
        SubjectSchemaTestCase {
            description: "project faults cannot escape the repository",
            value_path: "../outside.py",
            owner: ".",
            strict_owner: false,
            expected_faults_valid: false,
            expected_exceptions_valid: false,
        },
    ];

    for test_case in test_cases {
        let faults = CanonicalValue::List(vec![subject_fault(test_case.value_path)]);
        let exceptions = CanonicalValue::List(vec![subject_exception(test_case.value_path)]);
        assert_eq!(
            decode_subject_faults(&faults, test_case.owner, test_case.strict_owner).is_some(),
            test_case.expected_faults_valid,
            "{}",
            test_case.description
        );
        assert_eq!(
            decode_subject_exceptions(&exceptions, test_case.owner, test_case.strict_owner)
                .is_some(),
            test_case.expected_exceptions_valid,
            "{}",
            test_case.description
        );
    }
}
