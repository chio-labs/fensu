use std::path::Path;

use crate::mapping::constants::MAX_COMPACT_PATH_PARTS;
use crate::mapping::models::{CallMapEntry, CallMapNode, PathMode};

const RESET: &str = "\x1b[0m";
const DIM: &str = "\x1b[2m";
const FUNCTION: &str = "\x1b[1;36m";
const UNRESOLVED: &str = "\x1b[33m";
const CYCLE: &str = "\x1b[35m";

pub(crate) fn render(
    root: &CallMapNode,
    repo_root: &Path,
    path_mode: PathMode,
    use_color: bool,
) -> String {
    let mut lines = vec![label(root, repo_root, path_mode, use_color)];
    child_lines(root, repo_root, path_mode, "", use_color, &mut lines);
    format!("{}\n", lines.join("\n"))
}

fn child_lines(
    node: &CallMapNode,
    repo_root: &Path,
    path_mode: PathMode,
    prefix: &str,
    use_color: bool,
    lines: &mut Vec<String>,
) {
    for (position, entry) in node.entries.iter().enumerate() {
        let last = position + 1 == node.entries.len();
        let connector = if last { "└── " } else { "├── " };
        let rendered_connector = color(&format!("{prefix}{connector}"), DIM, use_color);
        match entry {
            CallMapEntry::Unresolved(unresolved) => {
                let location =
                    location(&node.definition.path, unresolved.line, repo_root, path_mode);
                let function = color(&format!("{}(...)", unresolved.name), FUNCTION, use_color);
                let rendered_location = color(&location, DIM, use_color);
                let marker = color(
                    &format!("(unresolved {})", unresolved.reason),
                    UNRESOLVED,
                    use_color,
                );
                lines.push(format!(
                    "{rendered_connector}{function}{rendered_location}  {marker}"
                ));
            }
            CallMapEntry::Node(child) => {
                lines.push(format!(
                    "{rendered_connector}{}",
                    label(child, repo_root, path_mode, use_color)
                ));
                let child_prefix = format!("{prefix}{}", if last { "    " } else { "│   " });
                child_lines(child, repo_root, path_mode, &child_prefix, use_color, lines);
            }
        }
    }
}

fn label(node: &CallMapNode, repo_root: &Path, path_mode: PathMode, use_color: bool) -> String {
    let display_name = node.dispatch_class_name.as_ref().map_or_else(
        || node.definition.qualified_name(),
        |class| format!("{class}.{}", node.definition.name),
    );
    let function = color(&format!("{display_name}(...)"), FUNCTION, use_color);
    let location = location(
        &node.definition.path,
        node.definition.syntax.line,
        repo_root,
        path_mode,
    );
    let rendered_location = color(&location, DIM, use_color);
    let marker = if node.cycle {
        color("  (cycle)", CYCLE, use_color)
    } else if node.truncated {
        color("  (depth limit)", DIM, use_color)
    } else {
        String::new()
    };
    format!("{function}{rendered_location}{marker}")
}

fn location(path: &Path, line: u32, repo_root: &Path, path_mode: PathMode) -> String {
    if path_mode == PathMode::None {
        return String::new();
    }
    let display = if path_mode != PathMode::Absolute {
        path.strip_prefix(repo_root).unwrap_or(path)
    } else {
        path
    };
    let mut text = display.to_string_lossy().replace('\\', "/");
    if path_mode == PathMode::Compact {
        let parts = text.split('/').collect::<Vec<_>>();
        if parts.len() > MAX_COMPACT_PATH_PARTS {
            text = format!(
                "{}/{}/…/{}/{}",
                parts[0],
                parts[1],
                parts[parts.len() - 2],
                parts[parts.len() - 1]
            );
        }
    }
    format!("  {text}:{line}")
}

fn color(text: &str, style: &str, enabled: bool) -> String {
    if text.is_empty() || !enabled {
        text.to_owned()
    } else {
        format!("{style}{text}{RESET}")
    }
}
