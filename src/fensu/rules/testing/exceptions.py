"""Errors raised by the public custom-rule testing harness."""


class RuleHarnessError(Exception):
    """A rule case cannot be evaluated safely or unambiguously."""
