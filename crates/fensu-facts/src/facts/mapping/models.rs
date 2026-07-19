//! Native rows consumed by Python call-map tree policy.

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct MappingExpressionRow {
    pub kind: String,
    pub spelling: String,
    pub parts: Vec<String>,
    pub child: Option<Box<MappingExpressionRow>>,
    pub string_value: Option<String>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct MappingParameterRow {
    pub name: String,
    pub annotation: Option<MappingExpressionRow>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct MappingCallRow {
    pub callee: MappingExpressionRow,
    pub line: u32,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct MappingStatementRow {
    pub control_flow: bool,
    pub assigned_names: Vec<String>,
    pub binding_name: Option<String>,
    pub binding_annotation: Option<MappingExpressionRow>,
    pub binding_value: Option<MappingExpressionRow>,
    pub calls: Vec<MappingCallRow>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct MappingFunctionRow {
    pub name: String,
    pub line: u32,
    pub owning_class: Option<String>,
    pub parameters: Vec<MappingParameterRow>,
    pub returns: Option<MappingExpressionRow>,
    pub statements: Vec<MappingStatementRow>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct MappingAttributeRow {
    pub name: String,
    pub expression: MappingExpressionRow,
    pub annotation: bool,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct MappingClassRow {
    pub name: String,
    pub line: u32,
    pub bases: Vec<MappingExpressionRow>,
    pub class_attributes: Vec<MappingAttributeRow>,
    pub instance_attributes: Vec<MappingAttributeRow>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct MappingImportAliasRow {
    pub name: String,
    pub asname: Option<String>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct MappingImportRow {
    pub module: Option<String>,
    pub level: u32,
    pub aliases: Vec<MappingImportAliasRow>,
    pub from_import: bool,
}

#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct MappingRows {
    pub runtime_imports: Vec<MappingImportRow>,
    pub annotation_imports: Vec<MappingImportRow>,
    pub functions: Vec<MappingFunctionRow>,
    pub classes: Vec<MappingClassRow>,
}
