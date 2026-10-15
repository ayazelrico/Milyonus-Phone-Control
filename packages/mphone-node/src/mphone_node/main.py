"""`mphone-node enroll --gateway URL --token T --name N` · `mphone-node run [--device URI …]`."""

import argparse
import asyncio
import json
import logging
import os
import sys

import httpx

from mphone_core import config

from .node import NodeDaemon


def credentials_path() -> str:
    return str(config.subdir("node") / "credentials.json")


def android_devices() -> list[str]:
    from mphone_backends.android_adb import parse
    from mphone_backends.android_adb.adb import Adb
    from mphone_protocol import MphoneError

    try:
        rows = parse.parse_devices(Adb().run("devices", "-l", pin=False))
    except MphoneError:
        return []
    return [f"android:{r.serial}" for r in rows if r.state == "device"]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="mphone-node")
    sub = p.add_subparsers(dest="command", required=True)
    en = sub.add_parser("enroll")
    en.add_argument("--gateway", required=True)
    en.add_argument("--token", required=True)
    en.add_argument("--name", required=True)
    run = sub.add_parser("run")
    run.add_argument(
        "--device", action="append", default=[], help="serve this URI (default: every attached Android)"
    )
    run.add_argument("--allow-raw", action="store_true")
    args = p.parse_args(sys.argv[1:] if argv is None else argv)
    if args.command == "enroll":
        r = httpx.post(
            f"{args.gateway.rstrip('/')}/v1/nodes/enroll",
            json={"token": args.token, "name": args.name},
            timeout=30,
        )
        if r.status_code != 201:
            print(f"✗ kayıt başarısız ({r.status_code}): {r.text}", file=sys.stderr)
            return 1
        data = {**r.json(), "gateway": args.gateway}
        path = credentials_path()
        with open(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w", encoding="utf-8") as f:
            json.dump(data, f)
        print(f"✓ node {data['node_id']} kaydedildi → {path}")
        return 0
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    with open(credentials_path(), encoding="utf-8") as f:
        creds = json.load(f)
    fixed = list(args.device)
    daemon = NodeDaemon(
        creds["gateway"],
        creds["node_id"],
        creds["node_secret"],
        devices=(lambda: fixed) if fixed else android_devices,
        allow_raw=args.allow_raw,
    )
    asyncio.run(daemon.run())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
