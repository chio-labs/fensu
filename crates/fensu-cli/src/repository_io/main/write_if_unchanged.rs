use crate::repository_io::models::WriteRequest;

pub(crate) fn write_if_unchanged(request: WriteRequest<'_>) -> Result<(), String> {
    crate::repository_io::_helpers::files::write_if_unchanged(request)
}
