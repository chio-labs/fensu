use std::collections::HashSet;
use std::env;
use std::fs;
use std::path::PathBuf;

const TRAILING_SPACE_ESCAPE_LF: &str = "\\x20\n";
const TRAILING_SPACE_ESCAPE_CRLF: &str = "\\x20\r\n";
const GENERATED_RULE_FIELDS: &[&str] = &[
    "constraints",
    "thresholds",
    "contract_behaviors",
    "configuration_inputs",
    "limits",
];

fn main() {
    let catalogue = include_bytes!("assets/catalogue.json");
    let catalogue_value = serde_json::from_slice::<serde_json::Value>(catalogue)
        .expect("catalogue asset contains JSON");
    let entries = catalogue_value
        .as_array()
        .filter(|entries| !entries.is_empty())
        .expect("catalogue asset contains a nonempty array");
    let mut codes = HashSet::new();
    for entry in entries {
        let code = entry
            .get("code")
            .and_then(serde_json::Value::as_str)
            .expect("catalogue entry contains a string code");
        assert!(
            codes.insert(code),
            "catalogue contains duplicate code {code}"
        );
        for field in GENERATED_RULE_FIELDS {
            assert!(
                entry.get(field).is_some_and(serde_json::Value::is_array),
                "catalogue entry {code} has no generated {field} array"
            );
        }
    }
    let python_gitignore = std::str::from_utf8(include_bytes!("assets/python.gitignore"))
        .expect("gitignore asset contains UTF-8")
        .replace(TRAILING_SPACE_ESCAPE_CRLF, " \r\n")
        .replace(TRAILING_SPACE_ESCAPE_LF, " \n");
    let output = PathBuf::from(env::var_os("OUT_DIR").expect("output directory"));
    fs::write(output.join("catalogue.json"), catalogue).expect("write generated catalogue");
    fs::write(output.join("python.gitignore"), python_gitignore).expect("write gitignore template");
    println!("cargo:rerun-if-changed=assets/catalogue.json");
    println!("cargo:rerun-if-changed=assets/python.gitignore");
}
