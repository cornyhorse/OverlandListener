#!/usr/bin/env python3
"""Bump the project version across all files that reference it.

Usage:
    python scripts/bump_version.py 1.2.0
    python scripts/bump_version.py minor          # 1.0.0 -> 1.1.0
    python scripts/bump_version.py patch          # 1.0.0 -> 1.0.1
    python scripts/bump_version.py major          # 1.0.0 -> 2.0.0
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP_PY = ROOT / "src" / "app.py"
DOCKERFILE = ROOT / "Dockerfile"
DOCKER_COMPOSE = ROOT / "docker-compose.yaml"

VERSION_RE = re.compile(r"(\d+)\.(\d+)\.(\d+)")


def read_current_version() -> str:
    """Read __version__ from src/app.py."""
    text = APP_PY.read_text()
    m = re.search(r'^__version__\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not m:
        raise RuntimeError("Cannot find __version__ in src/app.py")
    return m.group(1)


def compute_new_version(current: str, arg: str) -> str:
    """Return the new version string."""
    m = VERSION_RE.fullmatch(current)
    if not m:
        raise RuntimeError(f"Current version {current!r} is not semver")
    major, minor, patch = int(m.group(1)), int(m.group(2)), int(m.group(3))

    if arg == "major":
        return f"{major + 1}.0.0"
    elif arg == "minor":
        return f"{major}.{minor + 1}.0"
    elif arg == "patch":
        return f"{major}.{minor}.{patch + 1}"
    elif VERSION_RE.fullmatch(arg):
        return arg
    else:
        raise RuntimeError(f"Invalid version argument: {arg!r}")


def replace_in_file(path: Path, old: str, new: str) -> bool:
    """Replace all occurrences of old with new in a file. Returns True if changed."""
    text = path.read_text()
    if old not in text:
        return False
    path.write_text(text.replace(old, new))
    return True


def main() -> None:
    if len(sys.argv) != 2:
        print(__doc__.strip())
        sys.exit(1)

    current = read_current_version()
    new = compute_new_version(current, sys.argv[1])

    if current == new:
        print(f"Already at {current}")
        sys.exit(0)

    print(f"Bumping {current} → {new}")

    files_changed = []
    for path in [APP_PY, DOCKERFILE, DOCKER_COMPOSE]:
        if replace_in_file(path, current, new):
            files_changed.append(str(path.relative_to(ROOT)))

    if files_changed:
        print(f"Updated: {', '.join(files_changed)}")
    else:
        print("Warning: no files were updated")

    print(f"\nNew version: {new}")
    print("Remember to update CHANGELOG.md before tagging the release.")


if __name__ == "__main__":
    main()
