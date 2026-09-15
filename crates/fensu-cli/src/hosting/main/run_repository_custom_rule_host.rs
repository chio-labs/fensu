//! Run Python-authored rules over one bounded multi-target repository payload.

use fensu_policy::lifecycle::constants::CUSTOM_HOST_PROTOCOL_VERSION;
use fensu_policy::lifecycle::models::{
    CustomHostInvocation, CustomHostOutputLimits, CustomHostRequest,
};
use fensu_policy::run_custom_host;

use crate::check::models::{RepositoryCustomRulePayload, RepositoryCustomRuleResponse};
use crate::hosting::_helpers::authoring::verify_authoring_version;
use crate::hosting::_helpers::interpreter::python_executable;
use crate::hosting::constants::{
    REPOSITORY_HOST_STDERR_LIMIT, REPOSITORY_HOST_STDOUT_LIMIT, REPOSITORY_HOST_TIMEOUT,
};

pub(crate) fn run_repository_custom_rule_host(
    payload: RepositoryCustomRulePayload,
) -> Result<RepositoryCustomRuleResponse, String> {
    verify_authoring_version()?;
    let program = python_executable()?;
    let arguments = vec![
        "-c".to_owned(),
        "from fensu.cli.main._repository_custom_rule_host import run_repository_custom_rule_protocol; raise SystemExit(run_repository_custom_rule_protocol())".to_owned(),
    ];
    let request = CustomHostRequest {
        protocol: CUSTOM_HOST_PROTOCOL_VERSION,
        runtime_version: env!("CARGO_PKG_VERSION").to_owned(),
        payload,
    };
    let response = run_custom_host::<_, RepositoryCustomRuleResponse>(CustomHostInvocation {
        program: &program,
        arguments: &arguments,
        timeout: REPOSITORY_HOST_TIMEOUT,
        output_limits: CustomHostOutputLimits {
            stdout_bytes: REPOSITORY_HOST_STDOUT_LIMIT,
            stderr_bytes: REPOSITORY_HOST_STDERR_LIMIT,
        },
        request: &request,
    })
    .map_err(|error| format!("Repository custom-rule host failed: {error}"))?;
    response
        .payload
        .ok_or_else(|| "Repository custom-rule host returned no payload.".to_owned())
}
