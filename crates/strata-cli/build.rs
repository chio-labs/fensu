use std::env;
use std::fs;
use std::path::PathBuf;

fn main() {
    let catalogue = include_bytes!("assets/catalogue.json");
    serde_json::from_slice::<serde_json::Value>(catalogue).expect("catalogue asset contains JSON");
    let output = PathBuf::from(env::var_os("OUT_DIR").expect("output directory"));
    fs::write(output.join("catalogue.json"), catalogue).expect("write generated catalogue");
    fs::write(
        output.join("python.gitignore"),
        include_bytes!("assets/python.gitignore"),
    )
    .expect("write gitignore template");
    println!("cargo:rerun-if-changed=assets/catalogue.json");
    println!("cargo:rerun-if-changed=assets/python.gitignore");
}
