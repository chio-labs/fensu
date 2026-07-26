//! Fixed text emitted by initialisation.

pub(crate) const INIT_USAGE: &str = "usage: fensu init [-h] [--yes] [--root ROOTS [ROOTS ...]] [--tests TESTS [TESTS ...]] [--tooling TOOLING [TOOLING ...]] [--skills | --no-skills] [--name NAME]\n\noptions:\n  -h, --help\n";
pub(crate) const NEXT_STEPS: &str = "\n-> Next\n\n    fensu check            run anytime\n    fensu rule FFA001      inspect any code in the output\n";
pub(crate) const FENSU_IGNORE: &str = "# Fensu\n.fensu/cache/\n";
