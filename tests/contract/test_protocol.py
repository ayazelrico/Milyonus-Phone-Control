"""The protocol package matches its schema and its vectors (A1.01–A1.03)."""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from mphone_protocol import OP_NAMES, OP_SPECS, SCHEMA, ErrorInfo, MphoneError, OpRequest, OpResult

ROOT = Path(__file__).resolve().parents[2]
VECTORS = json.loads((ROOT / "tests/fixtures/protocol_vectors/requests.json").read_text(encoding="utf-8"))
ENVELOPES = json.loads((ROOT / "tests/fixtures/protocol_vectors/envelopes.json").read_text(encoding="utf-8"))


def test_schema_is_valid_json_schema() -> None:
    Draft202012Validator.check_schema(SCHEMA)


def test_generated_files_are_fresh() -> None:
    proc = subprocess.run(
        [sys.executable, str(ROOT / "tools/gen_protocol.py"), "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr


def test_every_op_has_vectors() -> None:
    assert set(VECTORS) - {"_doc"} == set(OP_NAMES)


@pytest.mark.parametrize("op", OP_NAMES)
def test_vectors(op: str) -> None:
    model = OP_SPECS[op].args_model
    for kw in VECTORS[op]["valid"]:
        model.model_validate(kw)
    for kw in VECTORS[op]["invalid"]:
        with pytest.raises(ValidationError):
            model.model_validate(kw)


def test_envelopes() -> None:
    for raw in ENVELOPES["valid_requests"]:
        OpRequest.model_validate(raw)
    for raw in ENVELOPES["invalid_requests"]:
        with pytest.raises(ValidationError):
            OpRequest.model_validate(raw)
    for raw in ENVELOPES["valid_results"]:
        OpResult.model_validate(raw)
    for raw in ENVELOPES["invalid_results"]:
        with pytest.raises(ValidationError):
            OpResult.model_validate(raw)


def test_errors_roundtrip_through_the_wire() -> None:
    raw: dict[str, Any] = ENVELOPES["valid_results"][1]["error"]
    err = MphoneError.from_info(ErrorInfo.model_validate(raw))
    assert type(err).__name__ == "DeviceLocked"
    assert err.to_info().model_dump() == ErrorInfo.model_validate(raw).model_dump()
    assert isinstance(err, RuntimeError)
