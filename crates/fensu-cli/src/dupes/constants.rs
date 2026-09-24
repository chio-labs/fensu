//! Tuned detection constants and output vocabulary for `fensu dupes`.

pub(crate) const KGRAM_SIZE: usize = 12;
pub(crate) const WINNOW_WINDOW: usize = 6;
pub(crate) const MIN_FINGERPRINTS: usize = 6;
pub(crate) const CANDIDATE_MIN_JACCARD: f64 = 0.2;
pub(crate) const MAX_FINGERPRINT_UNITS: usize = 25;
pub(crate) const SMALL_NEAR_MISS_TOKENS: usize = 80;
pub(crate) const SMALL_NEAR_MISS_MIN_SIMILARITY: f64 = 0.9;
pub(crate) const DEFAULT_MIN_TOKENS: usize = 60;
pub(crate) const DEFAULT_MIN_SIMILARITY: f64 = 0.8;
pub(crate) const DEFAULT_TOP: usize = 30;
pub(crate) const TEXT_MAX_MEMBERS: usize = 12;
pub(crate) const DIFF_MAX_LINES: usize = 12;
pub(crate) const SIMILARITY_DECIMALS: f64 = 10_000.0;

pub(crate) const CATEGORY_EXACT: &str = "exact";
pub(crate) const CATEGORY_RENAMED: &str = "renamed";
pub(crate) const CATEGORY_NEAR_MISS: &str = "near-miss";

pub(crate) const LANGUAGE_PYTHON: &str = "python";
pub(crate) const LANGUAGE_RUST: &str = "rust";
pub(crate) const LANGUAGE_TYPESCRIPT: &str = "typescript";
pub(crate) const LANGUAGE_JAVASCRIPT: &str = "javascript";
pub(crate) const LANGUAGE_SVELTE: &str = "svelte";
pub(crate) const LANGUAGES: &[&str] = &[
    LANGUAGE_PYTHON,
    LANGUAGE_RUST,
    LANGUAGE_TYPESCRIPT,
    LANGUAGE_JAVASCRIPT,
    LANGUAGE_SVELTE,
];

pub(crate) const PLACEHOLDER_IDENTIFIER: &str = "$id";
pub(crate) const PLACEHOLDER_NUMBER: &str = "$num";
pub(crate) const PLACEHOLDER_STRING: &str = "$str";
pub(crate) const PLACEHOLDER_FSTRING: &str = "$fstr";
pub(crate) const PLACEHOLDER_BYTE_STRING: &str = "$bstr";
pub(crate) const PLACEHOLDER_CHAR: &str = "$char";
pub(crate) const PLACEHOLDER_BYTE: &str = "$byte";
pub(crate) const PLACEHOLDER_LIFETIME: &str = "$life";
pub(crate) const PLACEHOLDER_TEMPLATE: &str = "$tpl";
pub(crate) const PLACEHOLDER_REGEX: &str = "$re";
pub(crate) const MARKER_NEWLINE: &str = "$nl";
pub(crate) const MARKER_INDENT: &str = "$in";
pub(crate) const MARKER_DEDENT: &str = "$de";

pub(crate) const CONFIG_DUPES_KEY: &str = "dupes";
pub(crate) const CONFIG_EXCLUDE_KEY: &str = "exclude";
pub(crate) const CONFIG_ALLOWLIST_KEY: &str = "allowlist";
pub(crate) const CONFIG_CONTRACTS_KEY: &str = "contract_exemptions";
pub(crate) const CONFIG_PATHS_KEY: &str = "paths";
pub(crate) const CONFIG_REASON_KEY: &str = "reason";
pub(crate) const CONFIG_CONTRACT_KEY: &str = "contract";
pub(crate) const CONFIG_FORBIDDEN_OWNERS_KEY: &str = "forbidden_owners";

pub(crate) const RUST_TEST_DIRECTORIES: &[&str] = &["tests", "benches"];
pub(crate) const SCOPE_TEST: &str = "test";

pub(crate) const DUPES_HELP: &str = "usage: fensu dupes [-h] [--json] [--top TOP] [--min-similarity MIN_SIMILARITY]\n                   [--min-tokens MIN_TOKENS]\n                   [--lang {python,rust,typescript,javascript,svelte}]\n                   [--path PATH] [--include-tests] [--since REV] [--diff]\n\nReport duplicated code (advisory). Findings never fail the command: it exits 0\nwhenever analysis succeeds and 2 for usage, configuration, or IO errors.\n\noptions:\n  -h, --help            show this help message and exit\n  --json                print deterministic JSON instead of text\n  --top TOP             number of clusters to print (default 30)\n  --min-similarity MIN_SIMILARITY\n                        minimum token similarity in (0, 1] (default 0.8)\n  --min-tokens MIN_TOKENS\n                        minimum normalised tokens per unit (default 60)\n  --lang {python,rust,typescript,javascript,svelte}\n                        analyze one language; repeat for several\n  --path PATH           only clusters with a member matching this glob; repeatable\n  --include-tests       also analyze configured tests and Rust test code\n  --since REV           only clusters touching lines changed since REV,\n                        including uncommitted and untracked files\n  --diff                show where the first two visible members diverge\n";
