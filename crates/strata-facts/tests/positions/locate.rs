//! Byte-offset conversion behavior over the position-semantics matrix.

use strata_facts::positions::main::locate_offset::locate_offset;

use crate::test_types;

#[test]
fn given_position_matrix_when_locating_offsets_then_matches_cpython_conventions() {
    let test_cases = [
        test_types::LocateOffsetTestCase {
            description: "empty source maps offset zero to line one column zero",
            source: "",
            offset: 0,
            expected_line: 1,
            expected_column: 0,
        },
        test_types::LocateOffsetTestCase {
            description: "ascii line without trailing newline maps a middle offset",
            source: "value = 1",
            offset: 6,
            expected_line: 1,
            expected_column: 6,
        },
        test_types::LocateOffsetTestCase {
            description: "offset at end of file without trailing newline stays on the last line",
            source: "value = 1",
            offset: 9,
            expected_line: 1,
            expected_column: 9,
        },
        test_types::LocateOffsetTestCase {
            description: "offset at end of file after a trailing newline starts a new line",
            source: "value = 1\n",
            offset: 10,
            expected_line: 2,
            expected_column: 0,
        },
        test_types::LocateOffsetTestCase {
            description: "offset beyond the source length clamps to the final position",
            source: "value = 1\n",
            offset: 99,
            expected_line: 2,
            expected_column: 0,
        },
        test_types::LocateOffsetTestCase {
            description: "third line offset counts every earlier newline",
            source: "a = 1\nb = 2\nc = 3\n",
            offset: 16,
            expected_line: 3,
            expected_column: 4,
        },
        test_types::LocateOffsetTestCase {
            description: "carriage return before a newline stays inside the earlier line",
            source: "a = 1\r\nb = 2\n",
            offset: 7,
            expected_line: 2,
            expected_column: 0,
        },
        test_types::LocateOffsetTestCase {
            description: "carriage return byte itself belongs to the earlier line",
            source: "a = 1\r\nb = 2\n",
            offset: 5,
            expected_line: 1,
            expected_column: 5,
        },
        test_types::LocateOffsetTestCase {
            description: "a retained utf-8 byte order mark shifts byte columns on line one",
            source: "\u{feff}x = 1\n",
            offset: 3,
            expected_line: 1,
            expected_column: 3,
        },
        test_types::LocateOffsetTestCase {
            description: "multibyte characters advance columns by utf-8 byte width",
            source: "\u{e9}\u{e9} = 1\n",
            offset: 5,
            expected_line: 1,
            expected_column: 5,
        },
        test_types::LocateOffsetTestCase {
            description: "offsets inside f-string replacement fields resolve like any byte",
            source: "name = 1\ntext = f\"{name}\"\n",
            offset: 19,
            expected_line: 2,
            expected_column: 10,
        },
        test_types::LocateOffsetTestCase {
            description: "offset on a blank separator line maps to that line at column zero",
            source: "a = 1\n\nb = 2\n",
            offset: 6,
            expected_line: 2,
            expected_column: 0,
        },
    ];

    for test_case in &test_cases {
        let actual = locate_offset(test_case.source, test_case.offset);

        assert_eq!(
            (actual.line, actual.column),
            (test_case.expected_line, test_case.expected_column),
            "case failed: {}",
            test_case.description
        );
    }
}
