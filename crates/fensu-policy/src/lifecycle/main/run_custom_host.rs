//! Invoke one custom-rule host through a versioned stdin/stdout exchange.

use serde::de::DeserializeOwned;
use serde::Serialize;

use crate::lifecycle::_helpers::canonical;
use crate::lifecycle::_helpers::hosting::exchange;
use crate::lifecycle::constants::CUSTOM_HOST_PROTOCOL_VERSION;
use crate::lifecycle::errors::LifecycleError;
use crate::lifecycle::models::{CustomHostInvocation, CustomHostResponse};

/// Run an isolated process and validate its protocol and runtime identity.
pub fn run_custom_host<RequestPayload, ResponsePayload>(
    invocation: CustomHostInvocation<'_, RequestPayload>,
) -> Result<CustomHostResponse<ResponsePayload>, LifecycleError>
where
    RequestPayload: Serialize,
    ResponsePayload: DeserializeOwned,
{
    let CustomHostInvocation {
        program,
        arguments,
        timeout,
        request,
    } = invocation;
    if request.protocol != CUSTOM_HOST_PROTOCOL_VERSION {
        return Err(LifecycleError::HostProtocol {
            actual: request.protocol,
            expected: CUSTOM_HOST_PROTOCOL_VERSION,
        });
    }
    let input = canonical::canonical_json(request)?;
    let output = exchange(program, arguments, &input, timeout)?;
    let stderr = String::from_utf8_lossy(&output.stderr).trim().to_owned();
    if !output.status.success() {
        return Err(LifecycleError::HostFailure {
            message: if stderr.is_empty() {
                format!("process exited with {}", output.status)
            } else {
                stderr
            },
        });
    }
    let mut response = serde_json::from_slice::<CustomHostResponse<ResponsePayload>>(
        &output.stdout,
    )
    .map_err(|error| LifecycleError::HostResponse {
        message: error.to_string(),
    })?;
    if response.protocol != request.protocol {
        return Err(LifecycleError::HostProtocol {
            actual: response.protocol,
            expected: request.protocol,
        });
    }
    if response.runtime_version != request.runtime_version {
        return Err(LifecycleError::HostRuntimeVersion {
            actual: response.runtime_version,
            expected: request.runtime_version.clone(),
        });
    }
    if let Some(message) = &response.error {
        return Err(LifecycleError::HostFailure {
            message: message.clone(),
        });
    }
    if !stderr.is_empty() {
        response.messages.push(stderr);
    }
    Ok(response)
}
