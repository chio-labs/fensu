use cap_std::fs::Dir;

use crate::repository_io::models::OperationLock;

pub(crate) fn acquire_operation_lock(
    repository: &Dir,
    path: &str,
) -> Result<OperationLock, String> {
    crate::repository_io::_helpers::files::acquire_operation_lock(repository, path)
}
