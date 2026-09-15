//! Run Python-authored rules over one versioned native web fact payload.

use fensu_policy::lifecycle::constants::CUSTOM_HOST_PROTOCOL_VERSION;
use fensu_policy::lifecycle::models::{
    CustomHostInvocation, CustomHostOutputLimits, CustomHostRequest,
};
use fensu_policy::run_custom_host;

use crate::check::models::{WebCustomRulePayload, WebCustomRuleResponse};
use crate::hosting::_helpers::authoring::verify_authoring_version;
use crate::hosting::_helpers::interpreter::python_executable;
use crate::hosting::constants::{WEB_HOST_STDERR_LIMIT, WEB_HOST_STDOUT_LIMIT, WEB_HOST_TIMEOUT};

pub(crate) fn run_web_custom_rule_host(
    payload: WebCustomRulePayload,
) -> Result<WebCustomRuleResponse, String> {
    verify_authoring_version()?;
    let program = python_executable()?;
    let arguments = vec![
        "-c".to_owned(),
        "from fensu.cli.main._web_custom_rule_host import run_web_custom_rule_protocol; raise SystemExit(run_web_custom_rule_protocol())".to_owned(),
    ];
    let request = CustomHostRequest {
        protocol: CUSTOM_HOST_PROTOCOL_VERSION,
        runtime_version: env!("CARGO_PKG_VERSION").to_owned(),
        payload,
    };
    let response = run_custom_host::<_, WebCustomRuleResponse>(CustomHostInvocation {
        program: &program,
        arguments: &arguments,
        timeout: WEB_HOST_TIMEOUT,
        output_limits: CustomHostOutputLimits {
            stdout_bytes: WEB_HOST_STDOUT_LIMIT,
            stderr_bytes: WEB_HOST_STDERR_LIMIT,
        },
        request: &request,
    })
    .map_err(|error| format!("Web custom-rule host failed: {error}"))?;
    response
        .payload
        .ok_or_else(|| "Web custom-rule host returned no payload.".to_owned())
}
