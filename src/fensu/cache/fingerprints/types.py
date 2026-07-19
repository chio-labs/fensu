"""Persistent cache fingerprint type declarations."""

type CanonicalValue = None | bool | int | str | list["CanonicalValue"] | dict[str, "CanonicalValue"]
