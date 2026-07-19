use std::env;
use std::fs;
use std::path::PathBuf;

const TRAILING_SPACE_ESCAPE_LF: &str = "\\x20\n";
const TRAILING_SPACE_ESCAPE_CRLF: &str = "\\x20\r\n";

fn main() {
    let catalogue = include_bytes!("assets/catalogue.json");
    serde_json::from_slice::<serde_json::Value>(catalogue).expect("catalogue asset contains JSON");
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
