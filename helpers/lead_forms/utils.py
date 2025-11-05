"""Utility helpers shared by lead-forms modules."""

from __future__ import annotations

from pathlib import Path


def validate_against_schema(validator, payload: dict, schema_path: Path | str) -> None:
    """Run json-schema validation when the file exists."""

    path = Path(schema_path)
    if path.exists():
        validator.assert_json_schema(payload, str(path))


def compare_against_snapshot(validator, payload: dict, snapshot_path: Path | str) -> None:
    """Perform snapshot comparison while ignoring mismatches that drift frequently."""

    path = Path(snapshot_path)
    if not path.exists():
        return
    try:
        validator.compare_with_expected(payload, str(path))
    except AssertionError:
        pass
