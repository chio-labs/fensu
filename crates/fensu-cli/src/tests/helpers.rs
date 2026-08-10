use std::fs;
use std::path::Path;

use crate::analyzer::AnalyzerId;
use crate::check::_helpers::project;
use crate::models::ScopedSource;

pub(crate) fn web_source(root: &Path, target_path: &str) -> ScopedSource {
    let path = root.join(target_path);
    ScopedSource {
        analyzer: AnalyzerId::TypeScript,
        target_identity: "web".to_owned(),
        parser_contract: AnalyzerId::TypeScript.parser_contract(),
        path: path.clone(),
        repository_path: target_path.to_owned(),
        target_path: target_path.to_owned(),
        root: root.join("src"),
        root_text: "src".to_owned(),
        scope: "root".to_owned(),
        relative_parts: target_path.split('/').skip(1).map(str::to_owned).collect(),
        fingerprint: "source-fingerprint".to_owned(),
        content: fs::read(&path).expect("web source content"),
        direct: project::is_direct_source(&path, AnalyzerId::TypeScript),
        imports: Vec::new(),
        program: None,
    }
}
