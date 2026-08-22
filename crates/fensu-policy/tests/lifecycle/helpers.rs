//! Shared non-Fensu lifecycle fixtures.

use std::collections::HashMap;
use std::path::PathBuf;

use fensu_policy::lifecycle::constants::ANALYSIS_BATCH_SCHEMA_VERSION;
use fensu_policy::lifecycle::models::{
    AnalysisBatchRequest, AnalysisInput, Finding, FindingSeverity, RuntimeIdentity,
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
