//! Compiled repository path globs with Fensu's configuration semantics.

use globset::{GlobBuilder, GlobSet, GlobSetBuilder};

use crate::configuration::main::expand_path_pattern::expand_path_pattern;
use crate::constants::GLOB_ALL;

/// Path globs: `*` stays in one segment, `**` crosses segments, bare names match at any depth.
#[derive(Clone, Debug)]
pub(crate) struct GlobList {
    set: GlobSet,
    empty: bool,
}

impl GlobList {
    pub(crate) fn new(patterns: &[String]) -> Result<Self, String> {
        let mut builder = GlobSetBuilder::new();
        for pattern in patterns {
            for expanded in expand_path_pattern(pattern)? {
                let value = if expanded.contains('/') || expanded == GLOB_ALL {
                    expanded
                } else {
                    format!("**/{expanded}")
                };
                let glob = GlobBuilder::new(&value)
                    .literal_separator(true)
                    .backslash_escape(false)
                    .build()
                    .map_err(|error| format!("Invalid path glob {pattern}: {error}"))?;
                builder.add(glob);
            }
        }
        let set = builder
            .build()
            .map_err(|error| format!("Invalid path globs: {error}"))?;
        Ok(Self {
            set,
            empty: patterns.is_empty(),
        })
    }

    pub(crate) fn is_empty(&self) -> bool {
        self.empty
    }

    pub(crate) fn matches(&self, path: &str) -> bool {
        self.set.is_match(path)
    }
}
