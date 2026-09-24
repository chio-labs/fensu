//! Run the advisory duplicated-code report for the current repository.

use std::env;
use std::io::{self, IsTerminal, Write};
use std::time::Instant;

use crate::dupes::_helpers::inputs::arguments::parse_arguments;
use crate::dupes::_helpers::inputs::sources::discover_workspace;
use crate::dupes::_helpers::report::build::build_report;
use crate::dupes::_helpers::report::rendering::{render_json, render_text};
use crate::dupes::constants::DUPES_HELP;
use crate::models::CliOutput;

/// Exit 0 whenever analysis succeeds, regardless of findings; errors exit 2.
pub(crate) fn run_dupes(arguments: &[String]) -> Result<CliOutput, String> {
    let Some(options) = parse_arguments(arguments)? else {
        return Ok(CliOutput::success(DUPES_HELP.to_owned()));
    };
    let started = Instant::now();
    if io::stderr().is_terminal() {
        let _ = writeln!(io::stderr(), "fensu dupes: detecting duplicated code ...");
    }
    let invocation = dunce::canonicalize(env::current_dir().map_err(|error| error.to_string())?)
        .map_err(|error| error.to_string())?;
    let report = discover_workspace(&invocation, &options)
        .and_then(|workspace| build_report(&workspace, &options))
        .map_err(|error| format!("fensu dupes: analysis failed: {error}"))?;
    let stdout = if options.json {
        render_json(&report, options.top)?
    } else {
        render_text(&report, options.top)
    };
    let units: usize = report.unit_counts.values().sum();
    Ok(CliOutput {
        stdout,
        stderr: format!(
            "fensu dupes: found {} duplicated-code cluster{} across {units} units in {:.1}s (advisory)\n",
            report.clusters.len(),
            if report.clusters.len() == 1 { "" } else { "s" },
            started.elapsed().as_secs_f64()
        ),
        exit_code: 0,
    })
}
