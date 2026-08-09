//! Check skill freshness for every target routed through the custom host.

use std::path::Path;

use crate::configuration::main::load_targets;
use crate::skills::main::core_freshness;

pub(crate) fn all_target_custom_freshness(invocation: &Path, target: Option<&str>) -> String {
    let Ok(configs) = load_targets::load_targets(invocation, target) else {
        return String::new();
    };
    if configs.len() <= 1 {
        return String::new();
    }
    let mut messages: Vec<String> = Vec::new();
    for (_, config) in configs {
        let message = core_freshness::core_freshness(invocation, config.target.as_deref())
            .unwrap_or_default();
        if !message.is_empty() && !messages.contains(&message) {
            messages.push(message);
        }
    }
    messages.concat()
}
