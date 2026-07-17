//! Verify the embedded database and Git foundations.

use std::path::Path;

use duckdb::Connection;

/// Exercise the embedded database and pure-Rust Git foundations.
pub fn probe_dependencies(repository_root: &Path) -> Result<String, String> {
    let connection = Connection::open_in_memory().map_err(|error| error.to_string())?;
    let value: i32 = connection
        .query_row("SELECT 1", [], |row| row.get(0))
        .map_err(|error| error.to_string())?;
    if value != 1 {
        return Err("DuckDB dependency probe returned an unexpected value".to_owned());
    }

    let repository = gix::discover(repository_root).map_err(|error| error.to_string())?;
    let _ignore_parser = repository
        .ignore_pattern_parser()
        .map_err(|error| error.to_string())?;
    connection.version().map_err(|error| error.to_string())
}
