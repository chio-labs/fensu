use crate::configuration::_helpers::validation::WEB_THRESHOLD_ALIASES;
use crate::configuration::constants::{DEFAULT_THRESHOLDS, SVELTEKIT_RULE_PACK};
use crate::models::DetectedTarget;

pub(crate) fn render_target_config(targets: &[DetectedTarget]) -> Result<String, String> {
    let mut text = String::new();
    for (index, target) in targets.iter().enumerate() {
        if index > 0 {
            text.push('\n');
        }
        text.push_str(&format!("[targets.{}]\n", target.name));
        text.push_str(&format!("analyzer = {:?}\n", target.analyzer.to_string()));
        text.push_str(&format!("root = {:?}\n", target.root));
        text.push_str(&format!(
            "roots = {}\n",
            serde_json::to_string(&target.roots).map_err(|error| error.to_string())?
        ));
        text.push_str(&format!(
            "tests = {}\n",
            serde_json::to_string(&target.tests).map_err(|error| error.to_string())?
        ));
        text.push_str(&format!(
            "tooling = {}\n",
            serde_json::to_string(&target.tooling).map_err(|error| error.to_string())?
        ));
        if target.analyzer != crate::analyzer::AnalyzerId::Python {
            text.push_str(&format!(
                "test_layout = {:?}\n",
                target.test_layout.to_string()
            ));
        }
        text.push_str(&format!(
            "rule_packs = {}\n",
            serde_json::to_string(&target.rule_packs).map_err(|error| error.to_string())?
        ));
        text.push_str(&format!(
            "select = {}\n",
            serde_json::to_string(&target.select).map_err(|error| error.to_string())?
        ));
        if target.analyzer == crate::analyzer::AnalyzerId::Svelte
            && target
                .rule_packs
                .iter()
                .any(|pack| pack == SVELTEKIT_RULE_PACK)
        {
            text.push_str(&format!("[targets.{}.thresholds]\n", target.name));
            for (alias, canonical) in WEB_THRESHOLD_ALIASES {
                let value = DEFAULT_THRESHOLDS
                    .iter()
                    .find_map(|(name, value)| (*name == *canonical).then_some(value))
                    .ok_or_else(|| format!("Missing default threshold {canonical}."))?;
                text.push_str(&format!("{alias} = {value}\n"));
            }
        }
    }
    Ok(text)
}
