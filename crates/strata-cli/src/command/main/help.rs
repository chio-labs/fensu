pub(crate) fn help() -> String {
    "Usage: strata {init,check,rule,map,skills} ...\n\nCommands:\n  init    Initialize Strata configuration for a repository.\n  check   Evaluate repository architecture rules.\n  rule    Show details for one rule.\n  map     Render a downstream project call map.\n  skills  Generate and install agent guidance.\n\nRun `strata <command> --help` for command-specific options.\n".to_owned()
}
