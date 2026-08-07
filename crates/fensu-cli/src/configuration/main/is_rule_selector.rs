pub(crate) fn is_rule_selector(value: &str) -> bool {
    crate::configuration::_helpers::selectors::valid_selector(value)
}
