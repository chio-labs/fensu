//! Command adapter printing structure violations for the current repository.

use std::process;

fn main() {
    let Ok(repo_root) = std::env::current_dir() else {
        process::exit(2);
    };
    let violations =
        fensu_structure_checker::rules::main::check_repository::check_repository(&repo_root);
    for violation in &violations {
        let location = match violation.line {
            Some(line) => format!("{}:{line}", violation.path.display()),
            None => violation.path.display().to_string(),
        };
        println!("{location}: {} {}", violation.code, violation.message);
        println!("    help: {}", violation.remediation);
    }
    if !violations.is_empty() {
        process::exit(1);
    }
}
