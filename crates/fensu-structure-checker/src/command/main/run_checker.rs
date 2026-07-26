//! Render structure violations for the current repository.

use std::io::{self, Write};
use std::process::ExitCode;

pub fn run_checker() -> ExitCode {
    let Ok(repo_root) = std::env::current_dir() else {
        return ExitCode::from(2);
    };
    let violations = crate::rules::main::check_repository::check_repository(&repo_root);
    let mut stdout = io::stdout().lock();
    for violation in &violations {
        let location = match violation.line {
            Some(line) => format!("{}:{line}", violation.path.display()),
            None => violation.path.display().to_string(),
        };
        let _ = writeln!(
            stdout,
            "{location}: {} {}",
            violation.code, violation.message
        );
        let _ = writeln!(stdout, "    help: {}", violation.remediation);
    }
    if violations.is_empty() {
        ExitCode::SUCCESS
    } else {
        ExitCode::from(1)
    }
}
