pub(crate) fn valid_code(value: &str) -> bool {
    fensu_policy::policy::main::rule_code_is_exact::rule_code_is_exact(value)
}

pub(crate) fn valid_selector(value: &str) -> bool {
    fensu_policy::policy::main::rule_selector_is_valid::rule_selector_is_valid(value)
}
