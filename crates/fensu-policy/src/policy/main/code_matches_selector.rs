//! Match validated rule identities and selectors.

use crate::policy::types::RuleCodeGrammar;

/// Return whether a valid exact code starts with a valid selector.
pub(in crate::policy) fn code_matches_selector<Grammar>(
    grammar: &Grammar,
    code: &str,
    selector: &str,
) -> bool
where
    Grammar: RuleCodeGrammar + ?Sized,
{
    grammar.code_matches_selector(code, selector)
}
