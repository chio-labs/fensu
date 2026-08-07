pub(crate) fn is_rule_code(value: &str) -> bool {
    crate::configuration::_helpers::selectors::valid_code(value)
}
