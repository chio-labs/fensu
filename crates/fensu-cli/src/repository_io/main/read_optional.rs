use std::path::Path;

use cap_std::fs::Dir;

use crate::repository_io::models::SafeFileSnapshot;

pub(crate) fn read_optional(
    repository: &Dir,
    path: &Path,
) -> Result<Option<SafeFileSnapshot>, String> {
    crate::repository_io::_helpers::files::read_optional(repository, path)
}
