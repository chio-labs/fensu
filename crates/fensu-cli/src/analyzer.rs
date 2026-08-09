//! Typed analyzer identities and backend capability contracts.

use std::fmt;
use std::str::FromStr;

use serde::{Deserialize, Serialize};

#[derive(Clone, Copy, Debug, Default, Deserialize, Eq, Hash, PartialEq, Serialize)]
#[serde(rename_all = "lowercase")]
pub(crate) enum AnalyzerId {
    #[default]
    Python,
    TypeScript,
    Svelte,
}

impl AnalyzerId {
    pub(crate) const fn cache_contract(self) -> &'static str {
        match self {
            Self::Python => "python-ruff-py312-v1",
            Self::TypeScript => "typescript-backend-v1",
            Self::Svelte => "svelte-backend-v1",
        }
    }

    pub(crate) fn require_backend(self) -> Result<(), String> {
        match self {
            Self::Python => Ok(()),
            Self::TypeScript | Self::Svelte => {
                Err(format!("Known analyzer backend unavailable: {self}."))
            }
        }
    }
}

impl fmt::Display for AnalyzerId {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(match self {
            Self::Python => "python",
            Self::TypeScript => "typescript",
            Self::Svelte => "svelte",
        })
    }
}

impl FromStr for AnalyzerId {
    type Err = String;

    fn from_str(value: &str) -> Result<Self, Self::Err> {
        match value {
            "python" => Ok(Self::Python),
            "typescript" => Ok(Self::TypeScript),
            "svelte" => Ok(Self::Svelte),
            _ => Err(format!("Unknown analyzer: {value}.")),
        }
    }
}
