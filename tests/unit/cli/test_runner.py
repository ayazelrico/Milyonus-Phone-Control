"""`mphone run` / phone_exec runner, audit masking and the local lease (A3.01–A3.03)."""

import json
from pathlib import Path

import pytest

from mphone_cli.runner import TIMEOUT_EXIT, lint, run_script, scrubbed_env
from mphone_core import config
from mphone_core.audit import mask
from mphone_core.locallease import LocalLease
from mphone_protocol import LeaseConflict

HEADER = "# task: Android sürümünü oku\n# step: Ayarlar\n"


def test_runs_with_helpers_preloaded() -> None:
    r = run_script(HEADER + 'open_app("Ayarlar"); print(current_app())', "fake:settings_about")
    assert r.ok, r.stderr
    assert r.stdout.strip() == "com.android.settings"
    assert r.warnings == []
    run_dir = config.home() / "runs" / r.run_id
    assert (run_dir / "script.py").read_text(encoding="utf-8").startswith("# task:")
    ops = [json.loads(line) for line in (run_dir / "ops.jsonl").read_text(encoding="utf-8").splitlines()]
    launch = next(o for o in ops if o["op"] == "apps.launch")
    assert launch["task"] == "Android sürümünü oku" and launch["ok"] is True
    assert json.loads((run_dir / "result.json").read_text(encoding="utf-8"))["exit_code"] == 0


@pytest.mark.parametrize(
    ("code", "exit_code", "needle"),
    [
        ("tap(1, 1)", 2, "[DEVICE_LOCKED]"),
        ("raise ValueError('kendi hatam')", 1, "ValueError: kendi hatam"),
        ("tap_text('Yok böyle bir şey')", 1, "[NOT_FOUND]"),
    ],
)
def test_errors_map_to_exit_codes(code: str, exit_code: int, needle: str) -> None:
    device = "fake:locked_phone" if "tap(1" in code else "fake:settings_about"
    r = run_script(HEADER + code, device)
    assert r.exit_code == exit_code
    assert needle in r.stderr


def test_not_found_shows_what_is_visible() -> None:
    r = run_script(HEADER + "open_app('Ayarlar'); tap_text('Bluetooth')", "fake:settings_about")
    assert "görünen:" in r.stderr and "Ağ ve internet" in r.stderr


def test_timeout_kills_the_script() -> None:
    r = run_script(HEADER + "import time\ntime.sleep(60)", "fake:settings_about", timeout=5)
    assert r.timed_out and r.exit_code == TIMEOUT_EXIT
    assert r.duration_s < 20


def test_secrets_never_reach_the_script(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MILYONUS_API_KEY", "sk-should-not-leak")
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_x")
    monkeypatch.setenv("HARMLESS", "ok")
    r = run_script(
        HEADER
        + "import os; print(sorted(k for k in os.environ if k in ('MILYONUS_API_KEY','GITHUB_TOKEN','HARMLESS')))",
        "fake:settings_about",
    )
    assert r.stdout.strip() == "['HARMLESS']"
    assert scrubbed_env({"A_PASSWORD": "x", "B": "y"}) == {"B": "y"}


def test_output_is_capped_to_its_tail() -> None:
    r = run_script(HEADER + "print('x' * 200_000); print('SON')", "fake:settings_about")
    assert len(r.stdout) < 60_000 and r.stdout.rstrip().endswith("SON") and "kesildi" in r.stdout


def test_screenshots_are_reported() -> None:
    r = run_script(HEADER + "screenshot()", "fake:settings_about")
    assert len(r.images) == 1 and Path(r.images[0]).is_file()


def test_lint() -> None:
    assert lint("tap(1,1)") and lint(HEADER + "x") == []


def test_audit_masks_typed_text() -> None:
    masked = mask("input.text", {"s": "123456", "mode": "auto", "delay": 0.03})
    assert masked["s"] == {"len": 6, "sha256": masked["s"]["sha256"]} and "123456" not in json.dumps(masked)
    assert mask("input.tap", {"x": 1, "y": 2}) == {"x": 1, "y": 2}


def test_typing_into_a_pin_field_is_refused_and_never_written() -> None:
    script = HEADER + "open_app('WhatsApp'); tap_ui('Ayarlar')\n"
    script += "b = find_nodes(query='PIN')[0]; tap(b['x'], b['y']); type_text('987654')"
    r = run_script(script, "fake:whatsapp_like")
    assert r.exit_code == 3 and "[POLICY_DENIED]" in r.stderr
    for path in [*(config.home() / "audit").glob("*.jsonl"), config.home() / "runs" / r.run_id / "ops.jsonl"]:
        assert "987654" not in path.read_text(encoding="utf-8")


def test_allowed_text_is_masked_in_the_audit() -> None:
    script = (
        HEADER
        + "open_app('WhatsApp'); tap_ui('Ara'); tap_ui({'resource_id': 'search_input'}); type_text('gizli-not-42')"
    )
    r = run_script(script, "fake:whatsapp_like")
    assert r.ok, r.stderr
    ops = (config.home() / "runs" / r.run_id / "ops.jsonl").read_text(encoding="utf-8")
    assert '"op": "input.text"' in ops and "gizli-not-42" not in ops and '"len": 12' in ops


def test_local_lease_conflict_names_the_holder() -> None:
    first = LocalLease("fake:settings_about", owner="agent-a", purpose="müşteri yanıtı").acquire()
    try:
        with pytest.raises(LeaseConflict) as e:
            LocalLease("fake:settings_about", owner="agent-b").acquire()
        assert "agent-a" in e.value.message and "müşteri yanıtı" in e.value.message
        with pytest.raises(LeaseConflict):
            run_script(HEADER + "print(1)", "fake:settings_about")
    finally:
        first.release()
    with LocalLease("fake:settings_about", owner="agent-b"):
        pass  # free again once released


SEND = (
    HEADER
    + """open_app("WhatsApp"); tap_text("Ayşe Yılmaz"); tap_ui({"resource_id": "entry"})
type_text("Siparişiniz yarın kargoda")
tap_ui({"resource_id": "send"})
print("gönderildi" if find_text("Gönderildi") else "yok")
"""
)


def test_outward_send_needs_the_users_explicit_allow() -> None:
    blocked = run_script(SEND, "fake:whatsapp_like")
    assert blocked.exit_code == 3 and "[APPROVAL_REQUIRED]" in blocked.stderr
    assert "--allow outward-send" in blocked.stderr
    allowed = run_script(SEND, "fake:whatsapp_like", allow=["outward-send"])
    assert allowed.ok and allowed.stdout.strip() == "gönderildi"


def test_refused_ops_are_audited() -> None:
    r = run_script(SEND, "fake:whatsapp_like")
    ops = (config.home() / "runs" / r.run_id / "ops.jsonl").read_text(encoding="utf-8")
    assert '"error_code": "APPROVAL_REQUIRED"' in ops
