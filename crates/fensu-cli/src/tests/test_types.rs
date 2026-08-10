pub(crate) struct RenderColorTestCase {
    pub(crate) description: &'static str,
    pub(crate) source: &'static str,
    pub(crate) line: u32,
    pub(crate) column: u32,
    pub(crate) expected_output: &'static str,
}

pub(crate) struct PathMatchTestCase {
    pub(crate) description: &'static str,
    pub(crate) path: &'static str,
    pub(crate) pattern: &'static str,
    pub(crate) expected_matches: bool,
}

pub(crate) struct PathExpansionTestCase {
    pub(crate) description: &'static str,
    pub(crate) pattern: &'static str,
    pub(crate) expected_patterns: &'static [&'static str],
}

pub(crate) struct CacheIdentityFramingTestCase {
    pub(crate) description: &'static str,
    pub(crate) first_analyzer: AnalyzerId,
    pub(crate) first_target: &'static str,
    pub(crate) first_root: &'static str,
    pub(crate) second_analyzer: AnalyzerId,
    pub(crate) second_target: &'static str,
    pub(crate) second_root: &'static str,
    pub(crate) expected_equal: bool,
}

pub(crate) struct WebTestLayoutIdentityTestCase {
    pub(crate) description: &'static str,
    pub(crate) first_layout: crate::models::TestLayout,
    pub(crate) second_layout: crate::models::TestLayout,
    pub(crate) expected_equal: bool,
}

pub(crate) struct TargetRootRepresentationTestCase {
    pub(crate) description: &'static str,
    pub(crate) configured: &'static str,
    pub(crate) expected_root: &'static str,
}

pub(crate) struct WindowsPathContainmentTestCase {
    pub(crate) description: &'static str,
    pub(crate) path: &'static str,
    pub(crate) root: &'static str,
    pub(crate) expected_relative: Option<&'static str>,
}

pub(crate) struct WindowsFilesystemContainmentTestCase {
    pub(crate) description: &'static str,
    pub(crate) run: fn() -> Option<bool>,
    pub(crate) expected_confined: bool,
}

pub(crate) struct MissingSuffixSymlinkTargetTestCase {
    pub(crate) description: &'static str,
    pub(crate) configured: &'static str,
    pub(crate) expected_root: &'static str,
}

pub(crate) struct EscapingSymlinkTargetTestCase {
    pub(crate) description: &'static str,
    pub(crate) configured: &'static str,
    pub(crate) expected_error: &'static str,
}

pub(crate) struct CoreRuleRenderingTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_core_count: usize,
    pub(crate) expected_labels: &'static [&'static str],
}
use crate::analyzer::AnalyzerId;

pub(crate) struct AnalyzerContractTestCase {
    pub(crate) description: &'static str,
    pub(crate) value: &'static str,
    pub(crate) expected_analyzer: Option<AnalyzerId>,
    pub(crate) expected_display: Option<&'static str>,
    pub(crate) expected_cache_contract: Option<&'static str>,
}

pub(crate) struct MapCacheIdentityTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_path_identity_equal: bool,
    pub(crate) expected_analyzer_identity_equal: bool,
}

pub(crate) struct AnalyzerCatalogueTestCase {
    pub(crate) description: &'static str,
    pub(crate) analyzer: AnalyzerId,
    pub(crate) select: &'static [&'static str],
    pub(crate) expected_codes: &'static [&'static str],
    pub(crate) expected_error: Option<&'static str>,
}

pub(crate) struct AnalyzerRenderingTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_line: &'static str,
}

pub(crate) struct ParserContractTestCase {
    pub(crate) description: &'static str,
    pub(crate) analyzer: AnalyzerId,
    pub(crate) expected_contract: &'static str,
}

pub(crate) struct WebImportGraphTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_import_count: usize,
    pub(crate) expected_resolutions: &'static [(&'static str, Option<&'static str>)],
}

pub(crate) struct WebDirectSourceTestCase {
    pub(crate) description: &'static str,
    pub(crate) path: &'static str,
    pub(crate) analyzer: AnalyzerId,
    pub(crate) expected_discovered: bool,
    pub(crate) expected_direct: bool,
    pub(crate) expected_source_kind: Option<fensu_typescript::SourceKind>,
}

pub(crate) struct WebTestSourceTestCase {
    pub(crate) description: &'static str,
    pub(crate) path: &'static str,
    pub(crate) expected_test: bool,
}

pub(crate) struct WebConfigInheritanceTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_input_count: usize,
    pub(crate) expected_resolutions: &'static [(&'static str, Option<&'static str>)],
}

pub(crate) struct SvelteKitAliasResolutionTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_generated_present: bool,
    pub(crate) expected_resolutions: &'static [(&'static str, Option<&'static str>)],
}

pub(crate) struct WebProjectPathTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_repository_path: &'static str,
    pub(crate) expected_target_path: &'static str,
    pub(crate) expected_resolutions: &'static [(&'static str, Option<&'static str>)],
}

pub(crate) struct WebSymlinkResolutionTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_resolutions: &'static [(&'static str, Option<&'static str>)],
    pub(crate) expected_source_escape_error: &'static str,
    pub(crate) expected_alias_escape_error: &'static str,
    pub(crate) expected_base_url_escape_error: &'static str,
}

pub(crate) struct DynamicSvelteAliasTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_error_fragments: &'static [&'static str],
}

pub(crate) struct OptionalGeneratedConfigTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_missing_present: bool,
    pub(crate) expected_generated_present: bool,
}

pub(crate) struct WebRuleApplicabilityTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_analyzer_error: &'static str,
    pub(crate) expected_framework_error: &'static str,
    pub(crate) expected_generic_code: &'static str,
}
