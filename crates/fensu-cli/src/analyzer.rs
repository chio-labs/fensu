//! Typed analyzer identities and backend capability contracts.

use std::fmt;
use std::str::FromStr;

use serde::{Deserialize, Serialize};

#[derive(Clone, Copy, Debug, Default, Deserialize, Eq, Hash, PartialEq, Serialize)]
#[serde(rename_all = "lowercase")]
pub(crate) enum AnalyzerId {
    #[default]
    Python,
    Rust,
    TypeScript,
    Svelte,
}

impl AnalyzerId {
    pub(crate) const fn cache_contract(self) -> &'static str {
        match self {
            Self::Python => "python-ruff-py312-v1",
            Self::Rust => fensu_rust::CACHE_CONTRACT_VERSION,
            Self::TypeScript => "typescript-policy-v4",
            Self::Svelte => "svelte-policy-v4",
        }
    }

    pub(crate) const fn parser_contract(self) -> &'static str {
        match self {
            Self::Python => "python-ruff-py312-v1",
            Self::Rust => fensu_rust::PARSER_CONTRACT_VERSION,
            Self::TypeScript => fensu_typescript::PARSER_CONTRACT_VERSION,
            Self::Svelte => fensu_svelte::PARSER_CONTRACT_VERSION,
        }
    }
}

impl fmt::Display for AnalyzerId {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(match self {
            Self::Python => "python",
            Self::Rust => "rust",
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
            "rust" => Ok(Self::Rust),
            "typescript" => Ok(Self::TypeScript),
            "svelte" => Ok(Self::Svelte),
            _ => Err(format!("Unknown analyzer: {value}.")),
        }
    }
}
