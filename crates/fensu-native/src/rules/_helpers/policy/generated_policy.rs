//! Generated fixed core-rule policy. Do not edit by hand.

#[rustfmt::skip]
pub(crate) const FFH002_ALLOWED_STANDALONE_COMMENT_PREFIXES: &[&str] = &[
    "#!",
    "# -*-",
    "# coding:",
    "# noqa",
    "# type:",
    "# pyright:",
    "# pylint:",
    "# pragma:",
];

#[rustfmt::skip]
pub(crate) const FFT301_EXCLUDED_TEST_SUPPORT_FILENAMES: &[&str] = &[
    "__init__.py",
    "conftest.py",
    "helpers.py",
    "_test_helpers.py",
    "_test_types.py",
];

#[rustfmt::skip]
pub(crate) const FFR201_FORBIDDEN_MODULE_FILENAMES: &[&str] = &[
    "misc.py",
];

#[rustfmt::skip]
pub(crate) const FFR204_FORBIDDEN_PACKAGE_NAMES: &[&str] = &[
    "base",
    "common",
    "helpers",
    "lib",
    "misc",
    "shared",
    "util",
    "utils",
];

#[rustfmt::skip]
pub(crate) const FFR301_FORBIDDEN_BUCKET_NAMES: &[&str] = &[
    "main",
    "_helpers",
    "helpers",
    "classes",
    "models",
    "types",
    "constants",
    "exceptions",
];

#[rustfmt::skip]
pub(crate) const FFR302_FORBIDDEN_BUCKET_NAMES: &[&str] = &[
    "main",
    "_helpers",
    "helpers",
    "classes",
    "models",
    "types",
    "constants",
    "exceptions",
];

#[rustfmt::skip]
pub(crate) const FFR303_RESERVED_ROLE_FILENAMES: &[&str] = &[
    "models.py",
    "types.py",
    "constants.py",
    "exceptions.py",
];

#[rustfmt::skip]
pub(crate) const FFR304_RECOGNIZED_ROLE_DIRECTORIES: &[&str] = &[
    "main",
    "_helpers",
    "classes",
    "models",
    "types",
    "constants",
    "exceptions",
];

#[rustfmt::skip]
pub(crate) const FFR304_RECOGNIZED_ROLE_FILENAMES: &[&str] = &[
    "main.py",
    "helpers.py",
    "classes.py",
    "models.py",
    "types.py",
    "constants.py",
    "exceptions.py",
];

#[rustfmt::skip]
pub(crate) const FFR305_RECOGNIZED_ROLE_DIRECTORIES: &[&str] = &[
    "main",
    "_helpers",
    "classes",
    "models",
    "types",
    "constants",
    "exceptions",
];

#[rustfmt::skip]
pub(crate) const FFR307_RECOGNIZED_ROLE_FILENAMES: &[&str] = &[
    "main.py",
    "helpers.py",
    "classes.py",
    "models.py",
    "types.py",
    "constants.py",
    "exceptions.py",
];

pub(crate) const FFR401_MAXIMUM_PRIVATE_FUNCTIONS: usize = 2;

pub(crate) const FFR401_REQUIRED_PUBLIC_FUNCTIONS: usize = 1;

#[rustfmt::skip]
pub(crate) const FFR701_ALLOWED_COMMAND_FUNCTIONS: &[&str] = &[
    "main",
    "_parse_args",
    "_build_parser",
];

#[rustfmt::skip]
pub(crate) const FFR701_ALLOWED_TOP_LEVEL_STATEMENT_KINDS: &[&str] = &[
    "import statement",
    "command function",
    "nonexecuting import guard",
];

pub(crate) const FFR701_REQUIRED_MAIN_FUNCTIONS: usize = 1;

#[rustfmt::skip]
pub(crate) const FFR702_ALLOWED_MAIN_CALL_TARGETS: &[&str] = &[
    "_parse_args",
    "imported main/ entry function",
];

#[rustfmt::skip]
pub(crate) const FFR705_ALLOWED_TOOLING_ROLE_DIRECTORIES: &[&str] = &[
    "main",
    "_helpers",
    "classes",
    "rules",
];

#[rustfmt::skip]
pub(crate) const FFR705_ALLOWED_TOOLING_ROLE_FILES: &[&str] = &[
    "models.py",
    "types.py",
    "constants.py",
    "exceptions.py",
];
