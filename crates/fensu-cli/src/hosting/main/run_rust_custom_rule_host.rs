//! Run Python-authored rules over one versioned native Rust fact payload.

use fensu_policy::lifecycle::constants::CUSTOM_HOST_PROTOCOL_VERSION;
use fensu_policy::lifecycle::models::{
    CustomHostInvocation, CustomHostOutputLimits, CustomHostRequest,
};
use fensu_policy::run_custom_host;

use crate::check::models::{RustCustomRulePayload, RustCustomRuleResponse};
use crate::hosting::_helpers::authoring::verify_authoring_version;
use crate::hosting::_helpers::interpreter::python_executable;
use crate::hosting::constants::{
    RUST_HOST_STDERR_LIMIT, RUST_HOST_STDOUT_LIMIT, RUST_HOST_TIMEOUT,
};

pub(crate) fn run_rust_custom_rule_host(
    payload: RustCustomRulePayload,
) -> Result<RustCustomRuleResponse, String> {
    verify_authoring_version()?;
    let program = python_executable()?;
    let arguments = vec![
        "-c".to_owned(),
        "from fensu.cli.main._rust_custom_rule_host import run_rust_custom_rule_protocol; raise SystemExit(run_rust_custom_rule_protocol())".to_owned(),
    ];
    let request = CustomHostRequest {
        protocol: CUSTOM_HOST_PROTOCOL_VERSION,
        runtime_version: env!("CARGO_PKG_VERSION").to_owned(),
        payload,
    };
    let response = run_custom_host::<_, RustCustomRuleResponse>(CustomHostInvocation {
        program: &program,
        arguments: &arguments,
        timeout: RUST_HOST_TIMEOUT,
        output_limits: CustomHostOutputLimits {
            stdout_bytes: RUST_HOST_STDOUT_LIMIT,
            stderr_bytes: RUST_HOST_STDERR_LIMIT,
        },
        request: &request,
    })
    .map_err(|error| format!("Rust custom-rule host failed: {error}"))?;
    response
        .payload
        .ok_or_else(|| "Rust custom-rule host returned no payload.".to_owned())
}
