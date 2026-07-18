"""Test accidental-corruption detection, not deliberate same-user record resealing."""

from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest

from strata.cache.fingerprints.types import CanonicalValue
from strata.cache.mapping._helpers.fingerprints import file_declaration_identity
from strata.cache.mapping._helpers.serialization import (
    decode_file_declarations,
    file_declarations_record,
)
from strata.cache.mapping.models import (
    ClassDeclaration,
    FileDeclarations,
    FunctionDeclaration,
    MappingIdentity,
)
from strata.cache.storage.models import CacheRecord
from strata.mapping.models import SourceSnapshot
from tests.integration.src.strata.cache.mapping._test_types import (
    MappingIdentityTestCase,
    RecordIntegrityTestCase,
)


@pytest.mark.parametrize(
    "test_case",
    [
        MappingIdentityTestCase(
            description="map contract changes file identity",
            field_name="contract",
            changed_value=2,
            expected_identity_changed=True,
        ),
        MappingIdentityTestCase(
            description="Python implementation changes file identity",
            field_name="python_implementation",
            changed_value="OtherPython",
            expected_identity_changed=True,
        ),
        MappingIdentityTestCase(
            description="Python version changes file identity",
            field_name="python_version",
            changed_value="3.99.0",
            expected_identity_changed=True,
        ),
        MappingIdentityTestCase(
            description="Strata implementation changes file identity",
            field_name="strata_implementation",
            changed_value="changed-implementation",
            expected_identity_changed=True,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_mapping_identity_component_change_when_keying_file_then_identity_changes(
    test_case: MappingIdentityTestCase,
) -> None:
    snapshot: SourceSnapshot = SourceSnapshot(
        path=Path("/repo/src/pkg/mod.py"),
        relative_path="src/pkg/mod.py",
        import_root=Path("/repo/src"),
        import_root_identity="src",
        module_name="pkg.mod",
        source=b"def run(): pass\n",
        source_fingerprint="source-fingerprint",
    )
    identity: MappingIdentity = MappingIdentity(1, "CPython", "3.12.0", "strata")
    changed: MappingIdentity = replace(identity, **{test_case.field_name: test_case.changed_value})

    original_key: str = file_declaration_identity(snapshot=snapshot, mapping_identity=identity)
    changed_key: str = file_declaration_identity(snapshot=snapshot, mapping_identity=changed)

    assert (original_key != changed_key) is test_case.expected_identity_changed


@pytest.mark.parametrize(
    "test_case",
    [
        RecordIntegrityTestCase(
            description="mutated canonical function metadata fails integrity",
            field_name="functions",
            changed_value=[],
            expected_valid=False,
        ),
        RecordIntegrityTestCase(
            description="redirected canonical path fails integrity",
            field_name="path",
            changed_value="src/pkg/other.py",
            expected_valid=False,
        ),
        RecordIntegrityTestCase(
            description="omitted canonical class metadata fails integrity",
            field_name="classes",
            changed_value=[],
            expected_valid=False,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_integrity_bound_record_when_semantics_mutate_then_decode_misses(
    test_case: RecordIntegrityTestCase,
) -> None:
    declarations: FileDeclarations = FileDeclarations(
        identity="identity",
        path="src/pkg/mod.py",
        module_name="pkg.mod",
        functions=(
            FunctionDeclaration(
                key="pkg.mod.Owner.run",
                name="run",
                qualified_name="Owner.run",
                owning_class="Owner",
            ),
        ),
        classes=(
            ClassDeclaration(
                key="pkg.mod.Owner",
                base_keys=("pkg.contracts.OwnerProtocol",),
                protocol=False,
            ),
        ),
    )
    record: CacheRecord = file_declarations_record(declarations)
    payload: dict[str, CanonicalValue] = dict(cast(dict[str, CanonicalValue], record.payload))
    payload[test_case.field_name] = cast(CanonicalValue, test_case.changed_value)
    mutated: CacheRecord = CacheRecord(kind=record.kind, payload=payload)

    decoded: FileDeclarations | None = decode_file_declarations(mutated)

    assert (decoded is not None) is test_case.expected_valid
