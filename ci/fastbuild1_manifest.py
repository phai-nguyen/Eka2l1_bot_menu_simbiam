#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import NoReturn

DEFAULT_MANIFEST = Path(__file__).with_name("fastbuild1_manifest.txt")


def fail(message: str) -> NoReturn:
    raise SystemExit(f"FASTBUILD1-MANIFEST: {message}")


def parse_manifest(path: Path) -> tuple[list[tuple[str, str]], list[str]]:
    section: str | None = None
    post: list[tuple[str, str]] = []
    regressions: list[str] = []

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line in ("[post_bootstrap]", "[regressions]"):
            section = line[1:-1]
            continue
        if section == "post_bootstrap":
            parts = [part.strip() for part in line.split("|")]
            if len(parts) != 2 or not all(parts):
                fail(f"invalid post_bootstrap row: {line}")
            post.append((parts[0], parts[1]))
        elif section == "regressions":
            regressions.append(line)
        else:
            fail(f"row outside a section: {line}")

    return post, regressions


def validate_manifest(repo_root: Path, manifest: Path = DEFAULT_MANIFEST) -> None:
    post, regressions = parse_manifest(manifest)
    referenced = [name for pair in post for name in pair] + regressions
    for name in referenced:
        target = repo_root / name
        if not target.is_file():
            fail(f"referenced file missing: {name}")


def run_python(script: Path, upstream: Path) -> None:
    subprocess.run(["python3", str(script), str(upstream)], check=True)


def apply_post_bootstrap(
    repo_root: Path,
    upstream: Path,
    manifest: Path = DEFAULT_MANIFEST,
) -> None:
    validate_manifest(repo_root, manifest)
    post, _ = parse_manifest(manifest)
    for apply_script, test_script in post:
        run_python(repo_root / apply_script, upstream)
        run_python(repo_root / test_script, upstream)


def run_regressions(
    repo_root: Path,
    upstream: Path,
    manifest: Path = DEFAULT_MANIFEST,
) -> None:
    validate_manifest(repo_root, manifest)
    _, regressions = parse_manifest(manifest)
    for test_script in regressions:
        run_python(repo_root / test_script, upstream)


def main() -> None:
    if len(sys.argv) < 3:
        fail("usage: fastbuild1_manifest.py <validate|apply|regress> <repo-root> [upstream-root]")

    command = sys.argv[1]
    repo_root = Path(sys.argv[2]).resolve()

    if command == "validate":
        validate_manifest(repo_root)
        print("FASTBUILD1-MANIFEST: VALID")
        return

    if len(sys.argv) != 4:
        fail(f"{command} requires <upstream-root>")
    upstream = Path(sys.argv[3]).resolve()

    if command == "apply":
        apply_post_bootstrap(repo_root, upstream)
        print("FASTBUILD1-MANIFEST: APPLY PASS")
    elif command == "regress":
        run_regressions(repo_root, upstream)
        print("FASTBUILD1-MANIFEST: REGRESSION PASS")
    else:
        fail(f"unknown command: {command}")


if __name__ == "__main__":
    main()
