const MEMORY_HELP: &str = "usage: fensu memory [-h] [--color {auto,always,never}]\n                    {archive,check,sync,rebuild,schema,graph,sql} ...\n\nSynchronize, inspect, and query persistent repository memory.\n\npositional arguments:\n  {archive,check,sync,rebuild,schema,graph,sql}\n    archive             archive eligible or explicit memory sources\n    check               validate canonical memory sources\n    sync                synchronize changed sources\n    rebuild             replace the complete memory index\n    schema              show public relation metadata\n    graph               retrieve a bounded document relationship graph\n    sql                 run read-only SQL\n\noptions:\n  -h, --help            show this help message and exit\n  --color {auto,always,never}\n                        ANSI color behavior\n";
const GRAPH_HELP: &str = "usage: fensu memory graph [-h] [--direction {outbound,inbound,both}]\n                          [--relationship {link,related,depends-on,supersedes,discovered-from,implements,documents}]\n                          [--depth DEPTH] [--max-nodes MAX_NODES]\n                          [--max-edges MAX_EDGES] [--include-archived]\n                          [--format {long,json}] [--color {auto,always,never}]\n                          DOCUMENT_OR_PATTERN\n\npositional arguments:\n  DOCUMENT_OR_PATTERN\n\noptions:\n  -h, --help            show this help message and exit\n  --direction {outbound,inbound,both}\n  --relationship {link,related,depends-on,supersedes,discovered-from,implements,documents}\n  --depth DEPTH\n  --max-nodes MAX_NODES\n  --max-edges MAX_EDGES\n  --include-archived\n  --format {long,json}\n  --color {auto,always,never}\n";
const ARCHIVE_HELP: &str = "usage: fensu memory archive [-h] [--yes] [--color {auto,always,never}]\n                            [paths ...]\n\npositional arguments:\n  paths                 repository-relative canonical paths\n\noptions:\n  -h, --help            show this help message and exit\n  --yes                 confirm explicit task archive\n  --color {auto,always,never}\n";
const CHECK_HELP: &str = "usage: fensu memory check [-h] [--color {auto,always,never}]\n\noptions:\n  -h, --help            show this help message and exit\n  --color {auto,always,never}\n";
const SYNC_HELP: &str = "usage: fensu memory sync [-h] [--color {auto,always,never}]\n\noptions:\n  -h, --help            show this help message and exit\n  --color {auto,always,never}\n";
const REBUILD_HELP: &str = "usage: fensu memory rebuild [-h] [--color {auto,always,never}]\n\noptions:\n  -h, --help            show this help message and exit\n  --color {auto,always,never}\n";
const SCHEMA_HELP: &str = "usage: fensu memory schema [-h] [--color {auto,always,never}] [relation]\n\npositional arguments:\n  relation              public relation name\n\noptions:\n  -h, --help            show this help message and exit\n  --color {auto,always,never}\n";
const SQL_HELP: &str = "usage: fensu memory sql [-h] [--format {long,table,json,csv}]\n                        [--limit LIMIT | --no-limit]\n                        [--color {auto,always,never}]\n                        QUERY\n\npositional arguments:\n  QUERY                 read-only SQL query\n\noptions:\n  -h, --help            show this help message and exit\n  --format {long,table,json,csv}\n  --limit LIMIT\n  --no-limit\n  --color {auto,always,never}\n";

pub(crate) fn requested(arguments: &[String]) -> bool {
    arguments
        .iter()
        .take_while(|argument| argument.as_str() != OPTION_TERMINATOR)
        .any(|argument| matches!(argument.as_str(), "-h" | "--help"))
}

pub(crate) fn text(arguments: &[String]) -> String {
    for argument in arguments {
        let help = match argument.as_str() {
            "archive" => ARCHIVE_HELP,
            "check" => CHECK_HELP,
            "sync" => SYNC_HELP,
            "rebuild" => REBUILD_HELP,
            "schema" => SCHEMA_HELP,
            "graph" => GRAPH_HELP,
            "sql" => SQL_HELP,
            _ => continue,
        };
        return help.to_owned();
    }
    MEMORY_HELP.to_owned()
}
use crate::command::constants::OPTION_TERMINATOR;
