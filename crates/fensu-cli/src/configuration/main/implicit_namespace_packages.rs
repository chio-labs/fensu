use std::path::Path;

use crate::configuration::helpers::packages;

pub(crate) fn implicit_namespace_packages(repository: &Path, roots: &[String]) -> String {
    let directories = packages::implicit_namespace_packages(repository, roots);
    packages::report(&directories)
}
