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
        if let Some(framework) = &target.framework {
            text.push_str(&format!("framework = {framework:?}\n"));
        }
        text.push_str(&format!(
            "rule_packs = {}\n",
            serde_json::to_string(&target.rule_packs).map_err(|error| error.to_string())?
        ));
        text.push_str(&format!(
            "select = {}\n",
            serde_json::to_string(&target.select).map_err(|error| error.to_string())?
        ));
    }
    Ok(text)
}
