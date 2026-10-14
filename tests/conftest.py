"""Shared fixtures. Every test gets its own MPHONE_HOME, so nothing touches ~/.mphone."""

from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from mphone_backends.fake import FakeBackend, from_uri
from mphone_core import helpers
from mphone_core.clock import VirtualClock
from mphone_core.helpers import Phone


@pytest.fixture(autouse=True)
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    home = tmp_path / "mphone-home"
    monkeypatch.setenv("MPHONE_HOME", str(home))
    for var in ("MPHONE_DEVICE", "MPHONE_GATEWAY", "MPHONE_LEASE", "MPHONE_AGENT_WORKSPACE"):
        monkeypatch.delenv(var, raising=False)
    helpers._default = None  # pyright: ignore[reportPrivateUsage]
    yield home
    helpers._default = None  # pyright: ignore[reportPrivateUsage]


FakePhone = Callable[[str], Phone]


@pytest.fixture
def fake_phone() -> FakePhone:
    """fake_phone("settings_about") → a Phone on a fresh fake, with a virtual clock and a
    human handler that refuses, so no test ever blocks on input()."""

    def make(name: str) -> Phone:
        def refuse(kind: str, text: str, timeout: float) -> bool:
            return False

        return Phone(from_uri(name), clock=VirtualClock(), human=refuse)

    return make


def backend_of(phone: Phone) -> FakeBackend:
    assert isinstance(phone.backend, FakeBackend)
    return phone.backend
