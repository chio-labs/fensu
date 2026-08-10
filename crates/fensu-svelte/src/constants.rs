//! Stable Svelte parser identities and syntax names.

pub const CACHE_CONTRACT_VERSION: &str = "svelte-backend-v11";
pub const PARSER_CONTRACT_VERSION: &str = "svelte-backend-v11";
pub(crate) const COMMENT_KIND: &str = "comment";
pub const RECOVERY_NODE_KINDS: [&str; 8] = [
    "attribute_expected_equals_tail",
    "attribute_sequence_recovery_tail",
    "erroneous_end_tag",
    "erroneous_end_tag_name",
    "incomplete_attribute_expression",
    "malformed_block",
    "orphan_branch",
    "tag_missing_whitespace_trailing",
];

pub(crate) const ATTRIBUTE_KIND: &str = "attribute";
pub(crate) const ATTRIBUTE_NAME_FIELD: &str = "name";
pub(crate) const ATTRIBUTE_VALUE_FIELD: &str = "value";
pub(crate) const CONTEXT_ATTRIBUTE: &str = "context";
pub(crate) const CONTENT_FIELD: &str = "content";
pub(crate) const ELEMENT_KIND: &str = "element";
pub(crate) const END_TAG_KIND: &str = "end_tag";
pub(crate) const EXPRESSION_KIND: &str = "expression";
pub(crate) const EXPRESSION_VALUE_KIND: &str = "expression_value";
pub(crate) const KNOWN_RUNES: [&str; 17] = [
    "$bindable",
    "$derived",
    "$derived.by",
    "$effect",
    "$effect.pending",
    "$effect.pre",
    "$effect.root",
    "$effect.tracking",
    "$host",
    "$inspect",
    "$inspect.trace",
    "$props",
    "$props.id",
    "$state",
    "$state.eager",
    "$state.raw",
    "$state.snapshot",
];
pub(crate) const LANGUAGE_ATTRIBUTE: &str = "lang";
pub(crate) const MODULE_ATTRIBUTE: &str = "module";
pub(crate) const MODULE_CONTEXT_VALUE: &str = "module";
pub(crate) const NAME_FIELD: &str = "name";
pub(crate) const PARSER_NO_TREE_MESSAGE: &str = "Svelte parser returned no syntax tree";
pub(crate) const PATTERN_KIND: &str = "pattern";
pub(crate) const RAW_TEXT_KIND: &str = "raw_text";
pub(crate) const SCRIPT_TAG: &str = "script";
pub(crate) const SNIPPET_BLOCK_KIND: &str = "snippet_block";
pub(crate) const SNIPPET_PARAMETERS_KIND: &str = "snippet_parameters";
pub(crate) const SNIPPET_TYPE_PARAMETERS_KIND: &str = "snippet_type_parameters";
pub(crate) const START_TAG_KIND: &str = "start_tag";
pub(crate) const STYLE_TAG: &str = "style";
pub(crate) const TAG_NAME_KIND: &str = "tag_name";
pub(crate) const TYPESCRIPT_LANGUAGE_VALUE: &str = "ts";
