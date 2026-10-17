use crate::configuration::_helpers::exception_targets;
use crate::models::RustExceptionSymbol;

pub(crate) fn rust_exception_symbols(source: &str) -> Result<Vec<RustExceptionSymbol>, String> {
    exception_targets::rust_symbols(source)
}
