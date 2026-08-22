//! Render structure violations for the current repository.

use std::io::{self, Write};
use std::process::ExitCode;

use crate::command::_helpers::arguments;
use crate::configuration::main::load_checker_config;
use crate::models;

pub fn run_checker() -> ExitCode {
    let arguments = match arguments::parse_arguments(std::env::args_os()) {
        Ok(value) => value,
        Err(error) => return command_error(&error),
    };
    if let Some(display) = arguments.display {
        let _ = writeln!(io::stdout().lock(), "{display}");
        return ExitCode::SUCCESS;
    }
    let repo_root = match arguments
        .root
        .map_or_else(std::env::current_dir, Ok)
        .and_then(|path| path.canonicalize())
    {
        Ok(value) => value,
        Err(error) => return command_error(&format!("could not resolve repository root: {error}")),
    };
    let configured = arguments.config.is_some();
    let config = match arguments.config {
        Some(path) => match contained_config_path(&repo_root, &path)
            .and_then(|path| load_checker_config::load_checker_config(&path))
        {
            Ok(value) => value,
            Err(error) => return command_error(&error),
        },
        None => models::CheckerConfig::default(),
    };
    let violations = if configured {
        crate::rules::main::check_repository_with_config::check_repository_with_config(
            &repo_root, &config,
        )
        .map_err(|error| format!("invalid structure-checker config: {error}"))
    } else {
        Ok(crate::rules::main::check_repository::check_repository(
            &repo_root,
        ))
    };
    let violations = match violations {
        Ok(value) => value,
        Err(error) => return command_error(&error),
    };
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

fn contained_config_path(
    repo_root: &std::path::Path,
    config_path: &std::path::Path,
) -> Result<std::path::PathBuf, String> {
    let canonical = config_path.canonicalize().map_err(|error| {
        format!(
            "could not resolve structure-checker config {}: {error}",
            config_path.display()
        )
    })?;
    if !canonical.starts_with(repo_root) {
        return Err(format!(
            "structure-checker config {} escapes repository root {}",
            canonical.display(),
            repo_root.display()
        ));
    }
    Ok(canonical)
}

fn command_error(message: &str) -> ExitCode {
    let _ = writeln!(io::stderr().lock(), "error: {message}");
    ExitCode::from(2)
}
