"""Backends against the contract (A1.14).

1. Every op/keyword a helper sends exists in the schema, and every backend slot names exactly the
   schema's arguments — send() passes the full validated set, so a missing parameter is a
   TypeError the first time an agent calls it, and an extra one is a default nobody can reach.
2. What the fake returns validates against each op's result schema.
"""

import ast
import inspect
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from mphone_backends.fake import FakeBackend, from_uri
from mphone_core.clock import VirtualClock
from mphone_core.helpers import Phone
from mphone_core.transport import Backend, slot_name
from mphone_protocol import OP_NAMES, OP_SPECS, result_schema

ROOT = Path(__file__).resolve().parents[2]
HELPERS = ROOT / "packages/mphone-core/src/mphone_core/helpers.py"
BACKENDS: list[type[Backend]] = [FakeBackend]  # android_adb joins in P2, ios_mirroring in P4


def sent_by_helpers() -> dict[str, set[str]]:
    """{op: keywords} for every send("op", kw=…) / self.send("op", …) in helpers.py."""
    sent: dict[str, set[str]] = {}
    for node in ast.walk(ast.parse(HELPERS.read_text(encoding="utf-8"))):
        if not isinstance(node, ast.Call) or not node.args or not isinstance(node.args[0], ast.Constant):
            continue
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
        if name == "send" and isinstance(node.args[0].value, str):
            sent.setdefault(node.args[0].value, set()).update(k.arg for k in node.keywords if k.arg)
    return sent


def schema_args(op: str) -> set[str]:
    return set(OP_SPECS[op].args_model.model_fields)


def test_helpers_send_known_ops_with_known_keywords() -> None:
    sent = sent_by_helpers()
    assert "input.scroll" in sent and "dx" in sent["input.scroll"]
    for op, keywords in sent.items():
        assert op in OP_SPECS, f"helpers send unknown op {op!r}"
        assert keywords <= schema_args(op), f"{op}: helpers send {keywords - schema_args(op)} not in schema"


@pytest.mark.parametrize("backend", BACKENDS, ids=lambda b: b.name)
def test_slot_signatures_match_schema(backend: type[Backend]) -> None:
    problems: list[str] = []
    for op in OP_NAMES:
        method = getattr(backend, slot_name(op), None)
        if method is None:
            continue  # Unsupported is an honest answer
        params = [p for p in inspect.signature(method).parameters if p != "self"]
        if set(params) != schema_args(op):
            problems.append(f"{op}: slot {sorted(params)} vs schema {sorted(schema_args(op))}")
    assert not problems, "\n".join(problems)


def test_fake_implements_every_op() -> None:
    assert from_uri("settings_about").ops() == list(OP_NAMES)


def _validate(op: str, value: Any) -> None:
    errors = list(Draft202012Validator(result_schema(op)).iter_errors(value))
    assert not errors, f"{op} returned {value!r}: {errors[0].message}"


def test_fake_results_match_result_schemas(tmp_path: Path) -> None:
    b = from_uri("whatsapp_like")
    p = Phone(b, clock=VirtualClock())
    calls: list[tuple[str, dict[str, Any]]] = [
        ("device.require", {}),
        ("device.state", {}),
        ("device.detail", {}),
        ("device.info", {}),
        ("screen.bounds", {}),
        ("screen.capture", {"path": str(tmp_path / "a.png")}),
        ("apps.launch", {"name": "WhatsApp"}),
        ("apps.current", {}),
        ("apps.list", {"include_system": True}),
        ("screen.text", {}),
        ("screen.text_pixels", {}),
        ("tree", {}),
        ("ui.find", {"selector": {"query": "Ayşe"}}),
        ("screen.stream.start", {}),
        ("input.tap", {"x": 540, "y": 500}),
        ("input.text", {"s": "Merhaba"}),
        ("input.clear", {}),
        ("input.keys", {"combo": "back"}),
        ("input.scroll", {"x": 540, "y": 1000, "dy": 300}),
        ("input.drag", {"x1": 540, "y1": 1500, "x2": 540, "y2": 900}),
        ("input.press", {"x": 1, "y": 1}),
        ("nav.home", {}),
        ("nav.back", {}),
        ("nav.recents", {}),
        ("nav.notifications", {}),
        ("clipboard.set", {"text": "x"}),
        ("clipboard.get", {}),
        ("notifications.list", {}),
        ("focus.probe", {}),
        ("focus.diff", {"before": [True], "after": [True]}),
        ("device.wake", {}),
        ("device.keep_awake", {"on": True}),
        ("raw", {"cmd": "id"}),
        ("apps.install", {"path": str(tmp_path / "com.example.app.apk")}),
        ("apps.uninstall", {"app_id": "com.example.app"}),
        ("apps.stop", {"app_id": "com.whatsapp.w4b"}),
    ]
    (tmp_path / "f.txt").write_text("veri", encoding="utf-8")
    calls += [
        ("files.push", {"dest": "/sdcard/f.txt", "path": str(tmp_path / "f.txt")}),
        ("files.pull", {"path": "/sdcard/f.txt"}),
    ]
    stream = p.send("screen.stream.start")["stream_id"]
    calls.append(("screen.stream.stop", {"stream_id": stream}))
    covered = {op for op, _ in calls} | {"screen.stream.start"}
    assert covered == set(OP_NAMES), f"not exercised: {set(OP_NAMES) - covered}"
    for op, kw in calls:
        _validate(op, p.send(op, **kw))
