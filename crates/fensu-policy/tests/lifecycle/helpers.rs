//! Shared non-Fensu lifecycle fixtures.

use std::collections::HashMap;
use std::path::PathBuf;
use std::process::{Command, Stdio};
use std::thread;
use std::time::Duration;

use fensu_policy::lifecycle::constants::ANALYSIS_BATCH_SCHEMA_VERSION;
use fensu_policy::lifecycle::models::{
    AnalysisBatchRequest, AnalysisInput, CustomHostOutputLimits, Finding, FindingSeverity,
    RuntimeIdentity,
};

use crate::test_types::ConsumerFacts;

pub(crate) fn consumer_request() -> AnalysisBatchRequest<ConsumerFacts> {
    AnalysisBatchRequest {
        schema_version: ANALYSIS_BATCH_SCHEMA_VERSION,
        required_capabilities: vec!["sql-relations".to_owned()],
        identity: RuntimeIdentity {
            producer: "sqlbuild-facts-3".to_owned(),
            fact_schema: "sql-facts-2".to_owned(),
            runtime: "fensu-policy-1".to_owned(),
            rule_pack: "sqbk-7".to_owned(),
            configuration: "kata-config-4".to_owned(),
        },
        inputs: vec![AnalysisInput {
            path: "models/orders.sql".to_owned(),
            fingerprint: "source-1".to_owned(),
            facts: ConsumerFacts {
                columns: HashMap::from([("order_id".to_owned(), "integer".to_owned())]),
            },
        }],
    }
}

pub(crate) fn empty_request() -> AnalysisBatchRequest<()> {
    AnalysisBatchRequest {
        schema_version: ANALYSIS_BATCH_SCHEMA_VERSION,
        required_capabilities: vec!["relations".to_owned()],
        identity: RuntimeIdentity {
            producer: "producer-1".to_owned(),
            fact_schema: "facts-1".to_owned(),
            runtime: "runtime-1".to_owned(),
            rule_pack: "rules-1".to_owned(),
            configuration: "config-1".to_owned(),
        },
        inputs: Vec::new(),
    }
}

pub(crate) fn versioned_requests() -> Vec<AnalysisBatchRequest<()>> {
    let baseline = empty_request();
    let mut producer = baseline.clone();
    producer.identity.producer = "producer-2".to_owned();
    let mut facts = baseline.clone();
    facts.identity.fact_schema = "facts-2".to_owned();
    let mut runtime = baseline.clone();
    runtime.identity.runtime = "runtime-2".to_owned();
    let mut rules = baseline.clone();
    rules.identity.rule_pack = "rules-2".to_owned();
    let mut configuration = baseline.clone();
    configuration.identity.configuration = "config-2".to_owned();
    vec![baseline, producer, facts, runtime, rules, configuration]
}

pub(crate) fn finding(code: &str, path: &str, symbol: Option<&str>) -> Finding {
    Finding {
        code: code.to_owned(),
        path: path.to_owned(),
        line: Some(1),
        column: Some(0),
        symbol: symbol.map(str::to_owned),
        message: "fixture finding".to_owned(),
        remediation: Some("fix the fixture".to_owned()),
        severity: FindingSeverity::Blocking,
    }
}

pub(crate) fn host_output_limits() -> CustomHostOutputLimits {
    CustomHostOutputLimits {
        stdout_bytes: 512 * 1_024,
        stderr_bytes: 512 * 1_024,
    }
}

#[cfg(unix)]
pub(crate) fn host_command() -> (PathBuf, Vec<String>) {
    (
        PathBuf::from("/bin/sh"),
        vec![
            "-c".to_owned(),
            "cat >/dev/null; printf '%s\\n' '{\"protocol\":1,\"runtime_version\":\"fixture-runtime-1\",\"error\":null,\"payload\":{\"hosted\":true},\"messages\":[]}'".to_owned(),
        ],
    )
}

#[cfg(unix)]
pub(crate) fn hanging_host_command() -> (PathBuf, Vec<String>) {
    (
        PathBuf::from("/bin/sh"),
        vec!["-c".to_owned(), "sleep 5".to_owned()],
    )
}

#[cfg(unix)]
pub(crate) fn process_tree_host_command(pid_file: &std::path::Path) -> (PathBuf, Vec<String>) {
    (
        PathBuf::from("/bin/sh"),
        vec![
            "-c".to_owned(),
            format!("sleep 30 & echo \"$$ $!\" > '{}'; wait", pid_file.display()),
        ],
    )
}

#[cfg(unix)]
pub(crate) fn process_is_running(pid: u32) -> bool {
    Command::new("/bin/kill")
        .args(["-0", &pid.to_string()])
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status()
        .is_ok_and(|status| status.success())
}

#[cfg(unix)]
pub(crate) fn backpressure_host_command() -> (PathBuf, Vec<String>) {
    (
        PathBuf::from("/bin/sh"),
        vec![
            "-c".to_owned(),
            "dd if=/dev/zero bs=1024 count=256 >&2 2>/dev/null; cat >/dev/null; printf '%s\\n' '{\"protocol\":1,\"runtime_version\":\"runtime-1\",\"error\":null,\"payload\":{},\"messages\":[]}'".to_owned(),
        ],
    )
}

#[cfg(unix)]
pub(crate) fn response_host_command(response: &str) -> (PathBuf, Vec<String>) {
    (
        PathBuf::from("/bin/sh"),
        vec![
            "-c".to_owned(),
            format!("cat >/dev/null; printf '%s\\n' '{response}'"),
        ],
    )
}

#[cfg(unix)]
pub(crate) fn oversized_stdout_host_command() -> (PathBuf, Vec<String>) {
    (
        PathBuf::from("/bin/sh"),
        vec![
            "-c".to_owned(),
            "cat >/dev/null; printf '123456789'; sleep 30".to_owned(),
        ],
    )
}

#[cfg(unix)]
pub(crate) fn oversized_stderr_host_command() -> (PathBuf, Vec<String>) {
    (
        PathBuf::from("/bin/sh"),
        vec![
            "-c".to_owned(),
            "cat >/dev/null; printf '123456789' >&2; sleep 30".to_owned(),
        ],
    )
}

#[cfg(unix)]
pub(crate) fn successful_leader_with_descendant_command(
    pid_file: &std::path::Path,
) -> (PathBuf, Vec<String>) {
    (
        PathBuf::from("/bin/sh"),
        vec![
            "-c".to_owned(),
            format!(
                "cat >/dev/null; sleep 30 >/dev/null 2>&1 & echo $! > '{}'; printf '%s\\n' '{{\"protocol\":1,\"runtime_version\":\"runtime-1\",\"error\":null,\"payload\":{{}},\"messages\":[]}}'; exit 0",
                pid_file.display()
            ),
        ],
    )
}

#[cfg(windows)]
pub(crate) fn host_command() -> (PathBuf, Vec<String>) {
    (
        PathBuf::from("cmd.exe"),
        vec![
            "/C".to_owned(),
            "more >NUL & echo {\"protocol\":1,\"runtime_version\":\"fixture-runtime-1\",\"error\":null,\"payload\":{\"hosted\":true},\"messages\":[]}".to_owned(),
        ],
    )
}

#[cfg(windows)]
pub(crate) fn process_tree_host_command(pid_file: &std::path::Path) -> (PathBuf, Vec<String>) {
    let pid_file = pid_file.display().to_string().replace('\'', "''");
    (
        PathBuf::from("powershell.exe"),
        vec![
            "-NoProfile".to_owned(),
            "-Command".to_owned(),
            format!(
                "$child = Start-Process powershell.exe -ArgumentList '-NoProfile','-Command','Start-Sleep -Seconds 30' -PassThru; Set-Content -Path '{pid_file}' -Value \"$PID $($child.Id)\"; Start-Sleep -Seconds 30"
            ),
        ],
    )
}

#[cfg(windows)]
pub(crate) fn process_is_running(pid: u32) -> bool {
    Command::new("powershell.exe")
        .args([
            "-NoProfile",
            "-Command",
            &format!(
                "if (Get-Process -Id {pid} -ErrorAction SilentlyContinue) {{ exit 0 }} else {{ exit 1 }}"
            ),
        ])
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status()
        .is_ok_and(|status| status.success())
}

#[cfg(windows)]
pub(crate) fn hanging_host_command() -> (PathBuf, Vec<String>) {
    (
        PathBuf::from("powershell.exe"),
        vec![
            "-NoProfile".to_owned(),
            "-Command".to_owned(),
            "Start-Sleep -Seconds 5".to_owned(),
        ],
    )
}

#[cfg(windows)]
pub(crate) fn response_host_command(response: &str) -> (PathBuf, Vec<String>) {
    (
        PathBuf::from("cmd.exe"),
        vec!["/C".to_owned(), format!("more >NUL & echo {response}")],
    )
}

#[cfg(windows)]
pub(crate) fn oversized_stdout_host_command() -> (PathBuf, Vec<String>) {
    (
        PathBuf::from("cmd.exe"),
        vec![
            "/C".to_owned(),
            "more >NUL & <NUL set /P =123456789 & ping -n 31 127.0.0.1 >NUL".to_owned(),
        ],
    )
}

#[cfg(windows)]
pub(crate) fn oversized_stderr_host_command() -> (PathBuf, Vec<String>) {
    (
        PathBuf::from("cmd.exe"),
        vec![
            "/C".to_owned(),
            "more >NUL & <NUL set /P =123456789 1>&2 & ping -n 31 127.0.0.1 >NUL".to_owned(),
        ],
    )
}

#[cfg(windows)]
pub(crate) fn successful_leader_with_descendant_command(
    pid_file: &std::path::Path,
) -> (PathBuf, Vec<String>) {
    let pid_file = pid_file.display().to_string().replace('\'', "''");
    (
        PathBuf::from("powershell.exe"),
        vec![
            "-NoProfile".to_owned(),
            "-Command".to_owned(),
            format!(
                "$input | Out-Null; $child = Start-Process powershell.exe -ArgumentList '-NoProfile','-Command','Start-Sleep -Seconds 30' -PassThru; Set-Content -Path '{pid_file}' -Value $child.Id; Write-Output '{{\"protocol\":1,\"runtime_version\":\"runtime-1\",\"error\":null,\"payload\":{{}},\"messages\":[]}}'"
            ),
        ],
    )
}

pub(crate) fn process_stops(pid: u32) -> bool {
    thread::sleep(Duration::from_millis(100));
    !process_is_running(pid)
}

#[cfg(unix)]
pub(crate) fn early_failure_host_command() -> (PathBuf, Vec<String>) {
    (
        PathBuf::from("/bin/sh"),
        vec![
            "-c".to_owned(),
            "printf 'actionable failure\\n' >&2; exit 7".to_owned(),
        ],
    )
}

#[cfg(windows)]
pub(crate) fn early_failure_host_command() -> (PathBuf, Vec<String>) {
    (
        PathBuf::from("cmd.exe"),
        vec![
            "/C".to_owned(),
            "echo actionable failure 1>&2 & exit /B 7".to_owned(),
        ],
    )
}
