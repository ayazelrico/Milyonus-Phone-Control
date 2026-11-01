"""Policy engine: allow / approve / deny per op, from YAML (A3.04, Plan.md §10.3).

Shared by local mode (this middleware) and, from P5, the gateway. Rules are evaluated together and
the strictest decision wins. Facts that cost a device read — the foreground app, the box under a
tap, the visible text — are fetched lazily, once per op, and only when a rule needs them.
"""

import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Any

import yaml

from mphone_protocol import ApprovalDenied, ApprovalRequired, InvalidArgument, PolicyDenied

from .. import config
from ..textnorm import match
from ..transport import Next, OpCall

STRICTNESS = {"allow": 0, "approve": 1, "deny": 2}
SCREEN_CACHE_S = 1.5
INPUT_OPS = {
    "input.tap",
    "input.press",
    "input.text",
    "input.keys",
    "input.drag",
    "input.scroll",
    "input.clear",
}
Dict = dict[str, Any]


@dataclass(frozen=True)
class Rule:
    id: str
    when: Dict
    decision: str
    message: str = ""
    for_trust_levels: tuple[str, ...] = ()


@dataclass
class Policy:
    rules: list[Rule]
    categories: dict[str, list[str]] = field(default_factory=dict[str, list[str]])
    default: str = "allow"

    @staticmethod
    def parse(data: Dict) -> "Policy":
        rules: list[Rule] = []
        for raw in data.get("rules", []):
            decision = raw.get("decision", "allow")
            if decision not in STRICTNESS:
                raise InvalidArgument(f"policy rule {raw.get('id')!r}: unknown decision {decision!r}")
            rules.append(
                Rule(
                    str(raw["id"]),
                    dict(raw.get("when", {})),
                    decision,
                    raw.get("message", ""),
                    tuple(raw.get("for_trust_levels", ())),
                )
            )
        return Policy(
            rules, dict(data.get("categories", {})), data.get("defaults", {}).get("decision", "allow")
        )

    @staticmethod
    def load(path: Path | None = None) -> "Policy":
        if path is None:
            configured = config.get("policy.file")
            local = Path(configured) if configured else config.home() / "policy.yaml"
            path = local if local.is_file() else None
        text = (
            path.read_text(encoding="utf-8")
            if path
            else (resources.files(__package__) / "default.yaml").read_text(encoding="utf-8")
        )
        return Policy.parse(yaml.safe_load(text) or {})


@dataclass(frozen=True)
class Decision:
    decision: str
    rule: Rule | None
    target: Dict | None = None

    @property
    def message(self) -> str:
        return (self.rule.message if self.rule else "") or self.decision


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list | tuple | set):
        return [*value]  # pyright: ignore[reportUnknownArgumentType]
    return [value]


class Facts:
    """Lazily read what rules ask about, at most once per op."""

    def __init__(self, call: OpCall, read: Callable[[str], Any]) -> None:
        self.call = call
        self._read = read
        self._cache: Dict = {}

    def _get(self, key: str, fn: Callable[[], Any]) -> Any:
        if key not in self._cache:
            try:
                self._cache[key] = fn()
            except Exception:  # a fact we cannot read is unknown, not a crash
                self._cache[key] = None
        return self._cache[key]

    def app(self) -> str | None:
        current = self._get("app", lambda: self._read("apps.current"))
        return str(current["app_id"]) if isinstance(current, dict) else None  # pyright: ignore[reportUnknownArgumentType]

    def screen(self) -> list[Dict]:
        return self._get("screen", lambda: self._read("screen.text")) or []

    def target(self) -> Dict | None:
        """The smallest box under a tap; for typing/keys, the focused editable box."""

        def find() -> Dict | None:
            boxes = self.screen()
            kw = self.call.kw
            if "x" in kw and "y" in kw:
                under = [
                    b
                    for b in boxes
                    if abs(b["x"] - kw["x"]) <= b["w"] / 2 and abs(b["y"] - kw["y"]) <= b["h"] / 2
                ]
                return min(under, key=lambda b: b["w"] * b["h"]) if under else None
            focused = [b for b in boxes if b.get("focused") and b.get("editable")]
            return focused[0] if focused else None

        return self._get("target", find)


def _matches(rule: Rule, facts: Facts, mode: str, categories: dict[str, list[str]]) -> bool:
    w, call = rule.when, facts.call
    if "op" in w and call.op not in _as_list(w["op"]):
        return False
    if "mode" in w and mode not in _as_list(w["mode"]):
        return False
    if "combo_in" in w and str(call.kw.get("combo", "")).lower() not in [
        str(c).lower() for c in _as_list(w["combo_in"])
    ]:
        return False
    if "text_matches" in w:
        text = str(call.kw.get("s", ""))
        if not any(re.search(p, text) for p in _as_list(w["text_matches"])):
            return False
    if "app_in" in w or "app_in_category" in w:
        allowed = set(_as_list(w.get("app_in", [])))
        for cat in _as_list(w.get("app_in_category", [])):
            allowed |= set(categories.get(cat, []))
        if facts.app() not in allowed:
            return False
    if "screen_contains_any" in w:
        texts = [b["text"] for b in facts.screen()]
        if not any(
            match(needle, t) is not None for needle in _as_list(w["screen_contains_any"]) for t in texts
        ):
            return False
    if "target_text_any" in w:
        target = facts.target()
        labels = [target.get("text") or "", target.get("content_desc") or ""] if target else []
        if not any(
            (s := match(n, label, exact=True)) is not None and s <= 2
            for n in _as_list(w["target_text_any"])
            for label in labels
            if label
        ):
            return False
    if "target_field" in w:
        target = facts.target()
        if target is None or any(bool(target.get(k)) != bool(v) for k, v in w["target_field"].items()):
            return False
    return True


def evaluate(
    policy: Policy,
    call: OpCall,
    read: Callable[[str], Any],
    mode: str = "local",
    trust_level: str = "standard",
) -> Decision:
    facts = Facts(call, read)
    best = Decision(policy.default, None)
    for rule in policy.rules:
        if rule.for_trust_levels and trust_level not in rule.for_trust_levels:
            continue
        if STRICTNESS[rule.decision] <= STRICTNESS[best.decision] and best.rule is not None:
            continue  # cannot get stricter than what we already have
        if _matches(rule, facts, mode, policy.categories):
            best = Decision(rule.decision, rule, facts._cache.get("target"))  # pyright: ignore[reportPrivateUsage]
            if best.decision == "deny":
                break
    return best


Approver = Callable[[Decision, OpCall], bool]


class PolicyMiddleware:
    """Deny raises PolicyDenied; approve asks `approver` (or honours a pre-approved rule id) and
    raises ApprovalDenied / ApprovalRequired. Nothing reaches the phone until allowed."""

    def __init__(
        self,
        policy: Policy,
        approver: Approver | None = None,
        mode: str = "local",
        trust_level: str = "standard",
        pre_approved: set[str] | None = None,
    ) -> None:
        self.policy = policy
        self.approver = approver
        self.mode = mode
        self.trust_level = trust_level
        self.pre_approved = pre_approved or set()
        self.log: list[tuple[float, str, str | None, str]] = []
        # The last screen read that went through this chain, reused while nothing has changed the
        # screen since: tap_text() reads the screen right before tapping, so the common path costs
        # no extra read (a tree dump is 2–3 s on Android).
        self._screen: tuple[float, list[Dict]] | None = None

    def _read(self, call: OpCall, op: str) -> Any:
        if op == "screen.text" and self._screen and time.monotonic() - self._screen[0] < SCREEN_CACHE_S:
            return self._screen[1]
        return call.backend.send(op)

    def __call__(self, call: OpCall, nxt: Next) -> Any:
        if call.op == "screen.text":
            result = nxt(call)
            self._screen = (time.monotonic(), result)
            return result
        if call.op not in INPUT_OPS and call.op not in (
            "raw",
            "apps.launch",
            "apps.install",
            "apps.uninstall",
            "files.push",
        ):
            return nxt(call)
        decision = evaluate(self.policy, call, lambda op: self._read(call, op), self.mode, self.trust_level)
        self._screen = None  # this op may change the screen
        rule_id = decision.rule.id if decision.rule else None
        self.log.append((time.time(), call.op, rule_id, decision.decision))
        details = {"rule": rule_id, "op": call.op, "target": (decision.target or {}).get("text")}
        if decision.decision == "deny":
            raise PolicyDenied(decision.message, details=details)
        if decision.decision == "approve":
            if rule_id in self.pre_approved:
                return nxt(call)
            if self.approver is None:
                raise ApprovalRequired(
                    f"{decision.message} (kural: {rule_id})",
                    user_action=f"Kullanıcıya sorun; onaylarsa `--allow {rule_id}` ile yeniden çalıştırın.",
                    details=details,
                )
            if not self.approver(decision, call):
                raise ApprovalDenied(f"onay verilmedi: {decision.message}", details=details)
        return nxt(call)
