"""Set one version across every workspace package (A0.10).

    uv run tools/bump_version.py 0.2.0
    uv run tools/bump_version.py --check      # all packages agree?

Packages are versioned together so a node, gateway and CLI of the same release always
speak the same protocol build.
"""

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.]+)?$")
PYPROJECT_RE = re.compile(r'^(version = ")([^"]+)(")', re.MULTILINE)
INIT_RE = re.compile(r'^(__version__ = ")([^"]+)(")', re.MULTILINE)


def targets() -> list[tuple[Path, re.Pattern[str]]]:
    found = [(ROOT / "pyproject.toml", PYPROJECT_RE)]
    for pkg in sorted((ROOT / "packages").iterdir()):
        if not (pkg / "pyproject.toml").is_file():
            continue
        found.append((pkg / "pyproject.toml", PYPROJECT_RE))
        module = pkg.name.replace("-", "_")
        found.append((pkg / "src" / module / "__init__.py", INIT_RE))
    return found


def current(path: Path, pattern: re.Pattern[str]) -> str:
    match = pattern.search(path.read_text(encoding="utf-8"))
    if match is None:
        raise SystemExit(f"no version line in {path.relative_to(ROOT)}")
    return match.group(2)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("version", nargs="?")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    if args.check or args.version is None:
        versions = {str(p.relative_to(ROOT)): current(p, pat) for p, pat in targets()}
        distinct = set(versions.values())
        if len(distinct) == 1:
            print(f"all packages at {distinct.pop()}")
            return 0
        for path, version in versions.items():
            print(f"{version:>12}  {path}")
        return 1

    if not SEMVER.match(args.version):
        print(f"not a semver version: {args.version!r}", file=sys.stderr)
        return 2
    for path, pattern in targets():
        text = path.read_text(encoding="utf-8")
        path.write_text(pattern.sub(rf"\g<1>{args.version}\g<3>", text, count=1), encoding="utf-8")
    print(f"set {len(targets())} files to {args.version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
