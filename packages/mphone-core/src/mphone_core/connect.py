"""Turn a device URI into a backend (A1.05, Plan.md §8.1.2).

    android:SERIAL | android:usb | android:wifi:NAME   AndroidAdb (P2)
    ios-mirror:                                        IosMirroring (P4)
    ios-wda:UDID                                       IosWda (P8)
    gw://DEVICE_ID?lease=LEASE_ID                      Remote via the gateway (P5)
    fake:SCENARIO | fake:/path/to/scenario.yaml        Fake (tests, demos)

Backends register under the `mphone.backends` entry-point group (scheme → factory taking the
rest of the URI), so this module never imports a backend package.

Resolution when no URI is given: MPHONE_DEVICE, then MPHONE_GATEWAY + MPHONE_LEASE, then the
`default_device` setting. There is NO "first device found" step: a named device that cannot be
reached is an error, never a reason to drive a different phone (CLAUDE.md §6.2).
"""

import os
from collections.abc import Callable
from importlib.metadata import entry_points

from mphone_protocol import DeviceOffline, InvalidArgument

from . import config
from .transport import Backend

Factory = Callable[[str], Backend]
_registered: dict[str, Factory] = {}


def register(scheme: str, factory: Factory) -> None:
    """Register a backend factory in-process (tests, plugins without an entry point)."""
    _registered[scheme] = factory


def schemes() -> dict[str, Factory]:
    found: dict[str, Factory] = {}
    for ep in entry_points(group="mphone.backends"):
        found[ep.name] = ep.load()
    found.update(_registered)
    return found


def split(uri: str) -> tuple[str, str]:
    if uri.startswith("gw://"):
        return "gw", uri[len("gw://") :]
    scheme, sep, rest = uri.partition(":")
    if not sep or not scheme:
        raise InvalidArgument(f"not a device URI: {uri!r} (expected scheme:rest, e.g. fake:settings_about)")
    return scheme, rest


def resolve_uri(uri: str | None = None) -> tuple[str, str]:
    """(uri, where it came from)."""
    if uri:
        return uri, "argument"
    if os.environ.get("MPHONE_DEVICE"):
        return os.environ["MPHONE_DEVICE"], "env:MPHONE_DEVICE"
    gateway, lease = os.environ.get("MPHONE_GATEWAY"), os.environ.get("MPHONE_LEASE")
    if gateway and lease and os.environ.get("MPHONE_DEVICE_ID"):
        return f"gw://{os.environ['MPHONE_DEVICE_ID']}?lease={lease}", "env:MPHONE_GATEWAY"
    configured, source = config.lookup("default_device")
    if configured:
        return str(configured), source
    raise DeviceOffline(
        "no device selected",
        user_action="Bir cihaz seçin: `mphone config set default_device android:SERİ` "
        "veya MPHONE_DEVICE ortam değişkeni.",
    )


def connect(uri: str | None = None) -> Backend:
    """Build the backend for `uri` (or the configured default). Returns a new object each time,
    so one script can hold two devices side by side."""
    chosen, source = resolve_uri(uri)
    scheme, rest = split(chosen)
    factories = schemes()
    factory = factories.get(scheme)
    if factory is None:
        raise InvalidArgument(
            f"no backend for {scheme!r} (from {source}); installed: {', '.join(sorted(factories)) or 'none'}"
        )
    return factory(rest)
