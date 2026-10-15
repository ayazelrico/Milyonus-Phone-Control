"""`mphone-gateway serve | admin create-agent NAME | admin enrollment-token`."""

import argparse
import asyncio
import sys

from . import auth
from .app import create_app
from .db import Database
from .settings import Settings


async def _admin(args: argparse.Namespace) -> int:
    db = Database(Settings().db_url())
    await db.create_all()
    async with db.sessions() as s:
        if args.admin_command == "create-agent":
            agent, key = await auth.create_agent(s, args.name, trust_level=args.trust, allowed_tags=args.tag)
            print(f"agent: {agent.id}\napi key (bir kez gösterilir): {key}")
        else:
            token = await auth.create_enrollment_token(s, args.minutes)
            print(
                f"enrollment token ({args.minutes} dk, tek kullanımlık): {token}\n"
                f"node'da: mphone-node enroll --gateway URL --token {token} --name AD"
            )
    await db.dispose()
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="mphone-gateway")
    sub = p.add_subparsers(dest="command", required=True)
    serve = sub.add_parser("serve")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8080)
    sub.add_parser("migrate", help="apply database migrations (production)")
    admin = sub.add_parser("admin")
    asub = admin.add_subparsers(dest="admin_command", required=True)
    ca = asub.add_parser("create-agent")
    ca.add_argument("name")
    ca.add_argument("--trust", default="standard", choices=["low", "standard", "high"])
    ca.add_argument("--tag", action="append", default=[], help="restrict the agent to devices with this tag")
    et = asub.add_parser("enrollment-token")
    et.add_argument("--minutes", type=int, default=15)
    args = p.parse_args(sys.argv[1:] if argv is None else argv)
    if args.command == "admin":
        return asyncio.run(_admin(args))
    if args.command == "migrate":
        from .migrate import upgrade

        upgrade()
        print("✓ şema güncel")
        return 0
    import uvicorn

    uvicorn.run(create_app(), host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
