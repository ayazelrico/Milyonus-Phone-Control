"""Entry point for the `mphone` command. Subcommands arrive with P2/P3 (A2.13, A3.01, A3.08)."""

import sys

from mphone_cli import __version__


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args in (["--version"], ["-V"], ["version"]):
        print(f"mphone {__version__}")
        return 0
    print("mphone: no commands yet. Run `mphone --version`.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
