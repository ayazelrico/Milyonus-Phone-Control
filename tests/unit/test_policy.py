"""Local policy engine (A3.04): deny / approve / allow, decided before anything reaches the phone."""

from typing import Any

import pytest

from mphone_backends.fake import FakeBackend, from_uri
from mphone_core.clock import VirtualClock
from mphone_core.helpers import Phone
from mphone_core.policy import Decision, Policy, PolicyMiddleware, evaluate
from mphone_core.transport import OpCall
from mphone_protocol import ApprovalDenied, ApprovalRequired, PolicyDenied


def phone(
    scenario: str | dict[str, Any], approver: Any = None, allow: set[str] | None = None
) -> tuple[Phone, PolicyMiddleware]:
    backend = from_uri(scenario) if isinstance(scenario, str) else FakeBackend(scenario)
    mw = PolicyMiddleware(Policy.load(), approver=approver, pre_approved=allow)
    backend.use(mw)
    return Phone(backend, clock=VirtualClock()), mw


def open_chat(p: Phone) -> None:
    p.open_app("WhatsApp")
    p.tap_text("Ayşe Yılmaz")
    p.tap_ui({"resource_id": "entry"})


def test_default_policy_loads_and_is_ordered_by_ids() -> None:
    ids = [r.id for r in Policy.load().rules]
    assert "never-type-into-password-fields" in ids and "outward-send" in ids and "banking-apps" in ids


def test_typing_a_message_is_allowed_sending_needs_approval() -> None:
    asked: list[Decision] = []
    p, _ = phone("whatsapp_like", approver=lambda d, c: asked.append(d) or False)
    open_chat(p)
    p.type_text("Siparişiniz yarın kargoda")  # allowed: typing is not sending
    with pytest.raises(ApprovalDenied):
        p.tap_ui({"resource_id": "send"})
    assert asked and asked[0].rule and asked[0].rule.id == "outward-send"
    assert p.find_text("Gönderildi") == []  # the tap never reached the phone


def test_approved_send_goes_through() -> None:
    p, _ = phone("whatsapp_like", approver=lambda d, c: True)
    open_chat(p)
    p.tap_ui({"resource_id": "send"})
    assert p.find_text("Gönderildi")


def test_without_an_approver_the_agent_is_told_how_to_ask() -> None:
    p, _ = phone("whatsapp_like")
    open_chat(p)
    with pytest.raises(ApprovalRequired) as e:
        p.tap_ui({"resource_id": "send"})
    assert e.value.details["rule"] == "outward-send"
    assert e.value.user_action and "--allow outward-send" in e.value.user_action


def test_pre_approved_rule_passes() -> None:
    p, _ = phone("whatsapp_like", allow={"outward-send"})
    open_chat(p)
    p.tap_ui({"resource_id": "send"})
    assert p.find_text("Gönderildi")


def test_enter_in_a_messaging_app_needs_approval() -> None:
    p, _ = phone("whatsapp_like")
    open_chat(p)
    with pytest.raises(ApprovalRequired):
        p.press("enter")


def test_password_fields_are_never_typed_into() -> None:
    p, _ = phone("whatsapp_like", approver=lambda d, c: True)
    p.open_app("WhatsApp")
    p.tap_ui("Ayarlar")
    pin = p.find_nodes(query="PIN")[0]
    p.tap(pin["x"], pin["y"])
    with pytest.raises(PolicyDenied) as e:
        p.type_text("123456")
    assert e.value.details["rule"] == "never-type-into-password-fields"
    assert "••••••" not in " ".join(p.screen_text())  # nothing was typed


SMS_SCREEN = {
    "start": "s",
    "apps": [{"app_id": "com.example.app", "label": "Uygulama", "screen": "s"}],
    "screens": {
        "s": {
            "app": "com.example.app",
            "elements": [
                {
                    "id": "t",
                    "text": "Telefonunuza gelen doğrulama kodunu girin",
                    "x": 540,
                    "y": 300,
                    "w": 900,
                    "h": 80,
                },
                {"id": "code", "editable": True, "hint": "Kod", "x": 540, "y": 600, "w": 600, "h": 110},
            ],
        }
    },
}


def test_codes_on_a_verification_screen_are_denied() -> None:
    p, _ = phone(SMS_SCREEN)
    p.tap_ui({"query": "Kod"})
    with pytest.raises(PolicyDenied) as e:
        p.type_text("482913")
    assert e.value.details["rule"] == "secret-looking-text"
    p.type_text("Ayşe")  # not code-like: allowed


def test_banking_apps_are_closed() -> None:
    bank = {
        "start": "s",
        "apps": [{"app_id": "com.garanti.cepsubesi", "label": "Garanti", "screen": "s"}],
        "screens": {
            "s": {
                "app": "com.garanti.cepsubesi",
                "elements": [
                    {
                        "id": "b",
                        "text": "Hesaplarım",
                        "x": 540,
                        "y": 600,
                        "w": 400,
                        "h": 100,
                        "clickable": True,
                    }
                ],
            }
        },
    }
    p, _ = phone(bank)
    with pytest.raises(PolicyDenied):
        p.tap_text("Hesaplarım")


def test_target_label_must_match_exactly() -> None:
    policy = Policy.load()
    backend = from_uri("whatsapp_like")
    p = Phone(backend, clock=VirtualClock())
    p.open_app("WhatsApp")
    p.tap_text("Ayşe Yılmaz")
    p.tap_ui({"resource_id": "send"})  # now on the "Gönderildi" screen
    label = p.find_text("Gönderildi")[0]
    call = OpCall("input.tap", {"x": label["x"], "y": label["y"]}, backend)
    assert evaluate(policy, call, lambda op: backend.send(op)).decision == "allow"  # "Gönderildi" ≠ "Gönder"


def test_tap_text_costs_no_extra_screen_read() -> None:
    p, _ = phone("settings_about")
    p.open_app("Ayarlar")
    backend = p.backend
    assert isinstance(backend, FakeBackend)
    reads = lambda: sum(op == "screen.text" for op, _ in backend.calls)  # noqa: E731
    before = reads()
    p.tap_text("Pil")  # reads the screen once to find "Pil"; the policy reuses that read
    assert reads() == before + 1
    p.tap(540, 500)  # the screen may have changed since: the policy must look again
    assert reads() == before + 2


def test_reads_are_not_policed() -> None:
    p, mw = phone("whatsapp_like")
    p.screen()
    p.screenshot()
    assert mw.log == []
