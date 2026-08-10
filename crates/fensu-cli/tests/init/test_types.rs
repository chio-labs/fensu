pub(crate) struct InitScenarioTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_success: bool,
    pub(crate) run: fn(),
}
