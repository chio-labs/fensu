use std::io::{self, Write};
use std::process::ExitCode;

use fensu_cli::command::main::run_cli::run_cli;

fn main() -> ExitCode {
    let output = run_cli();
    let _ = io::stdout().write_all(output.stdout.as_bytes());
    let _ = io::stderr().write_all(output.stderr.as_bytes());
    ExitCode::from(u8::try_from(output.exit_code).unwrap_or(2))
}
