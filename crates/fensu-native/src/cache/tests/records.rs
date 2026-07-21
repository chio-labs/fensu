//! Canonical native cache-record contracts.

use crate::cache::constants::COMPRESSED_PREFIX;
use crate::cache::helpers::records::{decode_record, encode_canonical_record};
use crate::cache::models::CanonicalValue;
use crate::cache::tests::helpers::{maximum_record_bytes, object};
use crate::cache::tests::test_types::{
    CanonicalRecordTestCase, CompressionTestCase, InvalidRecordTestCase,
};

#[test]
fn given_canonical_payload_when_encoding_then_bytes_and_round_trip_are_stable() {
    let test_cases = [
        CanonicalRecordTestCase {
            description: "object keys are sorted before canonical encoding",
            kind: "metadata",
            payload: object(&[
                (
                    "zeta",
                    CanonicalValue::List(vec![
                        CanonicalValue::Integer("2".to_owned()),
                        CanonicalValue::Integer("1".to_owned()),
                    ]),
                ),
                ("alpha", CanonicalValue::Bool(true)),
            ]),
            expected_bytes: b"{\"kind\":\"metadata\",\"payload\":{\"alpha\":true,\"zeta\":[2,1]},\"schema_version\":4}",
        },
        CanonicalRecordTestCase {
            description: "non-ASCII strings retain Python-compatible escaping",
            kind: "metadata",
            payload: object(&[("caf\u{e9}", CanonicalValue::String("\u{1f600}\n".to_owned()))]),
            expected_bytes: b"{\"kind\":\"metadata\",\"payload\":{\"caf\\u00e9\":\"\\ud83d\\ude00\\n\"},\"schema_version\":4}",
        },
    ];
    for test_case in test_cases {
        let encoded =
            encode_canonical_record(test_case.kind, &test_case.payload, maximum_record_bytes())
                .expect(test_case.description);
        let decoded = decode_record(&encoded, test_case.kind, maximum_record_bytes())
            .expect(test_case.description);
        let reencoded =
            encode_canonical_record(test_case.kind, &decoded.payload, maximum_record_bytes())
                .expect(test_case.description);

        assert_eq!(
            encoded, test_case.expected_bytes,
            "{}",
            test_case.description
        );
        assert_eq!(
            reencoded, test_case.expected_bytes,
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_invalid_record_when_decoding_then_fails_soft() {
    let test_cases = [
        InvalidRecordTestCase {
            description: "truncated JSON is rejected",
            data: b"{\"kind\":\"metadata\"",
            expected_kind: "metadata",
            expected_present: false,
        },
        InvalidRecordTestCase {
            description: "unsupported schema is rejected",
            data: b"{\"kind\":\"metadata\",\"payload\":{},\"schema_version\":5}",
            expected_kind: "metadata",
            expected_present: false,
        },
        InvalidRecordTestCase {
            description: "wrong kind is rejected",
            data: b"{\"kind\":\"index\",\"payload\":{},\"schema_version\":4}",
            expected_kind: "metadata",
            expected_present: false,
        },
        InvalidRecordTestCase {
            description: "floating payload is rejected",
            data: b"{\"kind\":\"metadata\",\"payload\":1.5,\"schema_version\":4}",
            expected_kind: "metadata",
            expected_present: false,
        },
        InvalidRecordTestCase {
            description: "unknown envelope field is rejected",
            data: b"{\"extra\":true,\"kind\":\"metadata\",\"payload\":{},\"schema_version\":4}",
            expected_kind: "metadata",
            expected_present: false,
        },
        InvalidRecordTestCase {
            description: "noncanonical whitespace is rejected",
            data: b"{\"kind\": \"metadata\", \"payload\": {}, \"schema_version\": 4}",
            expected_kind: "metadata",
            expected_present: false,
        },
        InvalidRecordTestCase {
            description: "duplicate envelope key is rejected",
            data: b"{\"kind\":\"index\",\"kind\":\"metadata\",\"payload\":{},\"schema_version\":4}",
            expected_kind: "metadata",
            expected_present: false,
        },
    ];
    for test_case in test_cases {
        let actual = decode_record(
            test_case.data,
            test_case.expected_kind,
            maximum_record_bytes(),
        );

        assert_eq!(
            actual.is_some(),
            test_case.expected_present,
            "{}",
            test_case.description
        );
    }
}

#[test]
fn given_large_payload_when_encoding_then_compression_is_bounded_and_reversible() {
    let test_cases = [CompressionTestCase {
        description: "large canonical payload uses compressed framing",
        payload_size: 10_000,
        expected_compressed: true,
    }];
    for test_case in test_cases {
        let payload = object(&[(
            "source",
            CanonicalValue::String("a".repeat(test_case.payload_size)),
        )]);
        let encoded = encode_canonical_record("file_result", &payload, maximum_record_bytes())
            .expect(test_case.description);
        let decoded = decode_record(&encoded, "file_result", maximum_record_bytes())
            .expect(test_case.description);

        assert_eq!(
            encoded.starts_with(COMPRESSED_PREFIX),
            test_case.expected_compressed,
            "{}",
            test_case.description
        );
        assert_eq!(decoded.payload, payload, "{}", test_case.description);
        assert!(
            decode_record(&encoded, "file_result", 64).is_none(),
            "{}",
            test_case.description
        );
    }
}
