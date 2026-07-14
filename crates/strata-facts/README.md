# stratalint-native

Native fact-extraction core for [stratalint](https://github.com/chio-labs/strata).

This package provides the optional Rust-backed `strata_facts` extension
module. Installing it lets `strata check` extract semantic facts natively;
without it, stratalint runs on its pure-Python backend with identical
behavior. Force a backend with `STRATA_FACT_BACKEND=python|native`.
