//! Fixed text emitted by initialisation.

pub(crate) const INIT_USAGE: &str = "usage: fensu init [-h] [--yes] [--root ROOTS [ROOTS ...]] [--tests TESTS [TESTS ...]] [--tooling TOOLING [TOOLING ...]] [--skills | --no-skills] [--name NAME] [--preset sveltekit] [--exclude-target NAME [NAME ...]]\n\noptions:\n  -h, --help\n  --preset sveltekit\n  --exclude-target NAME [NAME ...]\n";
pub(crate) const NEXT_STEPS: &str = "\n-> Next\n\n    fensu check            run anytime\n    fensu rule FFA001      inspect any code in the output\n";
pub(crate) const FENSU_IGNORE: &str = "# Fensu\n.fensu/cache/\n";
pub(crate) const DEFAULT_TARGET_ROOT: &str = ".";
pub(crate) const PYTHON_TARGET_NAME: &str = "python";
pub(crate) const SVELTEKIT_PRESET: &str = "sveltekit";
pub(crate) const TESTS_ROOT: &str = "tests";
pub(crate) const WEB_TARGET_NAME: &str = "web";
