"""A phone behind the gateway (A5.16, Plan.md §8.2.5): `gw://DEVICE_ID?lease=LEASE_ID`.

Same helpers, same errors as a local phone: every op becomes POST /v1/devices/{id}/ops on the
gateway and the gateway's OpResult turns back into the protocol exception a local backend would
have raised. The gateway URL and API key come from MPHONE_GATEWAY / MPHONE_API_KEY (or config
`gateway.url`); the key is never written to disk by this module.
"""

import os
import time
from typing import Any
from urllib.parse import parse_qs, urlsplit

import httpx

from mphone_core import config
from mphone_core.transport import Backend, OpCall
from mphone_protocol import DeviceOffline, ErrorInfo, InvalidArgument, MphoneError, NeedsUser

RATE_LIMIT_RETRIES = 3  # the gateway says how long to wait; waiting is better than failing the agent


class RemoteBackend(Backend):
    name = "remote"
    platform = "android"  # reported per device by the gateway; see device()

    def __init__(
        self,
        device_id: str,
        lease_id: str | None,
        gateway: str,
        api_key: str,
        client: httpx.Client | None = None,
        allow: list[str] | None = None,
    ) -> None:
        super().__init__()
        self.device_id = device_id
        self.lease_id = lease_id
        self.allow = list(allow or [])
        self.http = client or httpx.Client(
            base_url=gateway.rstrip("/"), timeout=90, headers={"Authorization": f"Bearer {api_key}"}
        )
        self._device: dict[str, Any] | None = None

    def _error(self, response: httpx.Response) -> MphoneError:
        try:
            info = response.json().get("error")
        except ValueError:
            info = None
        if isinstance(info, dict):
            return MphoneError.from_info(ErrorInfo.model_validate(info))
        if response.status_code in (401, 403):
            return NeedsUser(
                f"the gateway refused the API key ({response.status_code})",
                user_action="MPHONE_API_KEY'i kontrol edin (mphone-gateway admin create-agent).",
            )
        return DeviceOffline(f"the gateway answered {response.status_code}: {response.text[:200]}")

    def device(self) -> dict[str, Any]:
        if self._device is None:
            try:
                r = self.http.get(f"/v1/devices/{self.device_id}")
            except httpx.HTTPError as e:
                raise DeviceOffline(f"cannot reach the gateway: {e}") from None
            if r.status_code != 200:
                raise self._error(r)
            self._device = r.json()
        device: dict[str, Any] = self._device or {}
        return device

    def supports(self, op: str) -> bool:
        return op in self.device().get("ops", [])

    def ops(self) -> list[str]:
        return list(self.device().get("ops", []))

    def _invoke(self, call: OpCall, attempt: int = 0) -> Any:
        kw = dict(call.kw)
        if call.op == "screen.capture":
            kw["path"] = None  # where to save is this machine's business, not the node's
        try:
            r = self.http.post(
                f"/v1/devices/{self.device_id}/ops",
                json={"op": call.op, "kw": kw, "lease_id": self.lease_id, "allow": self.allow},
            )
        except httpx.HTTPError as e:
            raise DeviceOffline(f"cannot reach the gateway: {e}") from None
        if r.status_code != 200:
            raise self._error(r)
        body = r.json()
        if not body.get("ok"):
            error = MphoneError.from_info(ErrorInfo.model_validate(body.get("error")))
            if error.code == "RATE_LIMITED" and attempt < RATE_LIMIT_RETRIES:
                time.sleep(int(error.details.get("retry_after_ms", 200)) / 1000)
                return self._invoke(call, attempt + 1)
            raise error
        result = body.get("result")
        if call.op == "screen.capture" and isinstance(result, dict) and call.kw.get("path"):
            import base64
            from pathlib import Path

            Path(call.kw["path"]).write_bytes(base64.b64decode(result["data_b64"]))
            result = {**result, "path": call.kw["path"], "data_b64": None}
        return result

    def close(self) -> None:
        self.http.close()


def from_uri(rest: str) -> RemoteBackend:
    """gw://DEVICE_ID?lease=LEASE_ID[&url=https://gateway]"""
    parts = urlsplit("gw://" + rest)
    query = {k: v[0] for k, v in parse_qs(parts.query).items()}
    gateway = query.get("url") or os.environ.get("MPHONE_GATEWAY") or config.get("gateway.url")
    # A lease credential (Plan.md §8.5) is what scripts get; an agent key works for direct use.
    key = os.environ.get("MPHONE_LEASE_CREDENTIAL") or os.environ.get("MPHONE_API_KEY")
    if not gateway or not key:
        raise InvalidArgument(
            "gw:// needs MPHONE_GATEWAY (or gateway.url) and MPHONE_LEASE_CREDENTIAL or MPHONE_API_KEY"
        )
    allow = [r for r in os.environ.get("MPHONE_ALLOW", "").split(",") if r]
    return RemoteBackend(parts.netloc, query.get("lease"), str(gateway), key, allow=allow)
