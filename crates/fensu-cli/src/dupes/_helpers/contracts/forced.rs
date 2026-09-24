//! Recognise forced overrides of contract methods from the analysed Python source.

use std::collections::HashSet;
use std::path::Path;

use crate::dupes::_helpers::contracts::classes::ClassResolver;
use crate::dupes::_helpers::inputs::globs::GlobList;
use crate::dupes::constants::LANGUAGE_PYTHON;
use crate::dupes::models::{ClassKey, CloneUnit, ContractExemption};

struct ContractScope {
    contract: ClassKey,
    method_names: HashSet<String>,
    forbidden_owners: HashSet<ClassKey>,
    paths: GlobList,
}

struct ForcedOverrides {
    resolver: ClassResolver,
    scopes: Vec<ContractScope>,
}

/// Flag each unit that overrides a contract method it may not inherit from an ancestor.
pub(crate) fn find_forced_overrides(
    root: &Path,
    import_roots: &[String],
    exemptions: &[ContractExemption],
    units: &[&CloneUnit],
) -> Result<Vec<bool>, String> {
    let mut overrides = ForcedOverrides {
        resolver: ClassResolver::new(root, import_roots),
        scopes: Vec::new(),
    };
    for exemption in exemptions {
        if overrides.resolver.file_exists(&exemption.contract.path) {
            let scope = overrides.contract_scope(exemption)?;
            overrides.scopes.push(scope);
        }
    }
    Ok(units.iter().map(|unit| overrides.is_forced(unit)).collect())
}

impl ForcedOverrides {
    fn contract_scope(&mut self, exemption: &ContractExemption) -> Result<ContractScope, String> {
        let mut forbidden: HashSet<ClassKey> = HashSet::from([exemption.contract.clone()]);
        for key in std::iter::once(&exemption.contract).chain(&exemption.forbidden_owners) {
            if !self.resolver.exists(key) {
                return Err(format!(
                    "Config key dupes.contract_exemptions class {}:{} was not found in the analysed source.",
                    key.path, key.name
                ));
            }
            forbidden.insert(key.clone());
        }
        Ok(ContractScope {
            contract: exemption.contract.clone(),
            method_names: self.resolver.abstract_methods(&exemption.contract),
            forbidden_owners: forbidden,
            paths: GlobList::new(&exemption.paths)?,
        })
    }

    /// Require a top-level class method under the scope paths that derives from the contract.
    fn is_forced(&mut self, unit: &CloneUnit) -> bool {
        if unit.language != LANGUAGE_PYTHON {
            return false;
        }
        let Some((class_name, method_name)) = unit.name.split_once('.') else {
            return false;
        };
        if method_name.contains('.') {
            return false;
        }
        let key = ClassKey {
            path: unit.path.clone(),
            name: class_name.to_owned(),
        };
        for position in 0..self.scopes.len() {
            let scope = &self.scopes[position];
            if scope.method_names.contains(method_name)
                && scope.paths.matches(&unit.path)
                && self.forced_in_scope(position, &key, method_name)
            {
                return true;
            }
        }
        false
    }

    fn forced_in_scope(&mut self, position: usize, key: &ClassKey, method_name: &str) -> bool {
        let order = self.resolver.method_resolution_order(key);
        if !order.contains(&self.scopes[position].contract) {
            return false;
        }
        if !order
            .iter()
            .all(|ancestor| self.resolver.info(ancestor).complete)
        {
            return false;
        }
        for ancestor in &order[1..] {
            if self.resolver.info(ancestor).concrete.contains(method_name) {
                return self.scopes[position].forbidden_owners.contains(ancestor);
            }
        }
        true
    }
}
