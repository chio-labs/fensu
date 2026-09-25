use fensu_facts::dead_code::models::{Module, Root};

#[derive(Default)]
pub(crate) struct ReachabilityTestCase {
    pub(crate) description: &'static str,
    pub(crate) modules: Vec<Module>,
    pub(crate) entries: &'static [&'static str],
    pub(crate) roots: Vec<Root>,
    pub(crate) expected_dead: &'static [&'static str],
    pub(crate) expected_stale: &'static [usize],
}
