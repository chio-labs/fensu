pub(crate) fn help() -> String {
    "Usage: fensu {init,check,rule,map,skills,memory} ...\n\nCommands:\n  init    Initialize Fensu configuration for a repository.\n  check   Evaluate repository architecture rules.\n  rule    Show details for one rule.\n  map     Render a directional project call map.\n  skills  Generate and install agent guidance.\n  memory  Synchronize, inspect, and query persistent repository memory.\n\nRun `fensu <command> --help` for command-specific options.\n".to_owned()
}
