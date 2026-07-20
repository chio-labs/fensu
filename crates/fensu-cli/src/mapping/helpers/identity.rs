pub(crate) fn qualify(name: &str, owning_class: Option<&str>) -> String {
    owning_class.map_or_else(|| name.to_owned(), |class| format!("{class}.{name}"))
}

pub(crate) fn build_function_key(module: &str, name: &str, class: Option<&str>) -> String {
    format!("{module}.{}", qualify(name, class))
}

pub(crate) fn build_class_key(module: &str, name: &str) -> String {
    format!("{module}.{name}")
}
