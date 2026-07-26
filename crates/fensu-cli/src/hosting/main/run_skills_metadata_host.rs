//! Exchange a skills metadata request with the Python host.

use crate::hosting::_helpers::metadata_exchange::{
    read_response, send_request, spawn_metadata_host,
};

pub(crate) fn run_skills_metadata_host(request: &[u8]) -> Result<Vec<u8>, String> {
    let host = spawn_metadata_host()?;
    let sent = send_request(host, request)?;
    read_response(sent)
}
