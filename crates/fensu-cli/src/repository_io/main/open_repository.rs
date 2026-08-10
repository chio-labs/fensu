use std::path::Path;

use cap_std::fs::Dir;

pub(crate) fn open_repository(repository: &Path) -> Result<Dir, String> {
    crate::repository_io::_helpers::files::open_repository(repository)
}
