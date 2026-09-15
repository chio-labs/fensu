//! Internal entry point for Fensu-owned authored `use` path collection.

pub(crate) fn use_paths(tree: &syn::UseTree) -> Vec<Vec<String>> {
    crate::rules::_helpers::imports::reference_paths::use_paths(tree)
}
