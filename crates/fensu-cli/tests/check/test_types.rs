#[derive(Default)]
pub(crate) struct CheckStep {
    pub(crate) config: Option<String>,
    pub(crate) writes: Vec<(&'static str, Option<&'static str>)>,
    pub(crate) status: i32,
    pub(crate) contains: &'static [&'static str],
    pub(crate) absent: &'static [&'static str],
}

pub(crate) struct CheckTestCase {
    pub(crate) description: &'static str,
    pub(crate) config: String,
    pub(crate) expected_steps: Vec<CheckStep>,
}

pub(crate) struct InitTestCase {
    pub(crate) description: &'static str,
    pub(crate) arguments: &'static [&'static str],
    pub(crate) files: &'static [(&'static str, &'static str)],
    pub(crate) expected_enabled: bool,
}
