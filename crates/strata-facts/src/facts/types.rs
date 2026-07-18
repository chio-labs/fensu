//! Fact extraction enums.

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum FactFamily {
    Annotations,
    Comments,
    AssignmentReferences,
    ClassDeclarations,
    Comparisons,
    Contracts,
    ControlFlow,
    Declarations,
    Functions,
    Hygiene,
    LocalCallEdges,
    NamedCalls,
    OuterStateMutations,
    ParameterMutationOccurrences,
    ParameterMutations,
    References,
    TestFunctions,
    TestModule,
}

#[derive(Clone, Debug, PartialEq)]
pub enum LiteralValueRow {
    StringSource(String),
    Bytes(Vec<u8>),
    Integer(String),
    Float(f64),
    Complex { real: f64, imag: f64 },
    Boolean(bool),
    None,
}
