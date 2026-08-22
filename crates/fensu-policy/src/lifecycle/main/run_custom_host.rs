//! Invoke one custom-rule host through a versioned stdin/stdout exchange.

use serde::de::DeserializeOwned;
use serde::{Deserialize, Serialize};
use serde_json::Value;

use crate::lifecycle::_helpers::canonical;
use crate::lifecycle::_helpers::hosting::{exchange, HostExchange};
use crate::lifecycle::constants::CUSTOM_HOST_PROTOCOL_VERSION;
use crate::lifecycle::errors::LifecycleError;
use crate::lifecycle::models::{CustomHostInvocation, CustomHostResponse};

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct RawCustomHostResponse {
    protocol: u32,
    runtime_version: String,
    error: Option<String>,
    payload: Option<Value>,
    messages: Vec<String>,
}

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
        output_limits,
        request,
    } = invocation;
    if request.protocol != CUSTOM_HOST_PROTOCOL_VERSION {
        return Err(LifecycleError::HostProtocol {
            actual: request.protocol,
            expected: CUSTOM_HOST_PROTOCOL_VERSION,
        });
    }
    if request.runtime_version.trim().is_empty() {
        return Err(LifecycleError::InvalidConfiguration {
            message: "custom host runtime version must be non-empty".to_owned(),
        });
    }
    if output_limits.stdout_bytes == 0 || output_limits.stderr_bytes == 0 {
        return Err(LifecycleError::InvalidConfiguration {
            message: "custom host output limits must be greater than zero".to_owned(),
        });
    }
    let input = canonical::canonical_json(request)?;
    let output = exchange(HostExchange {
        program,
        arguments,
        input: &input,
        timeout,
        output_limits,
    })?;
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
    let response =
        serde_json::from_slice::<RawCustomHostResponse>(&output.stdout).map_err(|error| {
            LifecycleError::HostResponse {
                message: error.to_string(),
            }
        })?;
    if response.protocol != request.protocol {
        return Err(LifecycleError::HostProtocol {
            actual: response.protocol,
            expected: request.protocol,
        });
    }
    if response.runtime_version.trim().is_empty() {
        return Err(LifecycleError::HostResponse {
            message: "runtime_version must be non-empty".to_owned(),
        });
    }
    if response.runtime_version != request.runtime_version {
        return Err(LifecycleError::HostRuntimeVersion {
            actual: response.runtime_version,
            expected: request.runtime_version.clone(),
        });
    }
    let payload = match (response.error, response.payload) {
        (Some(message), None) if !message.trim().is_empty() => {
            return Err(LifecycleError::HostFailure { message });
        }
        (None, Some(payload)) => {
            serde_json::from_value(payload).map_err(|error| LifecycleError::HostResponse {
                message: error.to_string(),
            })?
        }
        _ => {
            return Err(LifecycleError::HostResponse {
                message: "response must contain exactly one non-empty error or payload".to_owned(),
            });
        }
    };
    let mut messages = response.messages;
    if !stderr.is_empty() {
        messages.push(stderr);
    }
    Ok(CustomHostResponse {
        protocol: response.protocol,
        runtime_version: response.runtime_version,
        error: None,
        payload: Some(payload),
        messages,
    })
}
