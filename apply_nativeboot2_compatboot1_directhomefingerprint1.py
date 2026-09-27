#!/usr/bin/env python3
"""Replace the intermediate B99 marker with the Direct Home build identity."""
from __future__ import annotations

import sys
from pathlib import Path


MARK = "NATIVEBOOT2-COMPATBOOT1-DIRECTHOMEFINGERPRINT1"
B99_MARKER = "[NBOOT2][BUILD_ID] build=B99 track=H2_COMPATBOOT1_NOBYPASS1"
DIRECTHOME_MARKER = (
    "[NBOOT2][BUILD_ID] build=COMPATBOOT1_DIRECTHOME1 "
    "track=H2_COMPATBOOT1_DIRECTHOME1"
)
ANCHOR = "- (void)startEmulatorWithCompatTarget:(NSInteger)compatTarget {\n"
B99_INSERTION = f'    NSLog(@"{B99_MARKER}");\n'
DIRECTHOME_INSERTION = f'    NSLog(@"{DIRECTHOME_MARKER}");\n'


def fail(message: str) -> None:
    raise SystemExit(f"{MARK}: FAIL: {message}")


def patch_build_id(source: str) -> str:
    anchor_count = source.count(ANCHOR)
    if anchor_count != 1:
        fail(f"emulator-session start anchor: expected one, found {anchor_count}")

    directhome_count = source.count(DIRECTHOME_MARKER)
    b99_count = source.count(B99_MARKER)
    if directhome_count == 1:
        if b99_count != 0:
            fail(f"intermediate B99 marker remains {b99_count} time(s)")
        if source.count(ANCHOR + DIRECTHOME_INSERTION) != 1:
            fail("Direct Home runtime marker is not immediately after the session-start anchor")
        return source
    if directhome_count > 1:
        fail(f"Direct Home runtime marker appears {directhome_count} times")
    if b99_count != 1:
        fail(f"intermediate B99 runtime marker: expected one, found {b99_count}")
    if source.count(ANCHOR + B99_INSERTION) != 1:
        fail("intermediate B99 marker is not immediately after the session-start anchor")

    patched = source.replace(ANCHOR + B99_INSERTION, ANCHOR + DIRECTHOME_INSERTION, 1)
    if patched.count(DIRECTHOME_MARKER) != 1:
        fail("post-apply check: Direct Home runtime marker must appear once")
    if patched.count(B99_MARKER) != 0:
        fail("post-apply check: intermediate B99 marker must be absent")
    return patched


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_compatboot1_directhomefingerprint1.py <upstream-root>")

    root = Path(sys.argv[1]).resolve() / "src/emu/ios/app/RootViewController.mm"
    if not root.is_file():
        fail(f"missing source file: {root}")

    source = root.read_text(encoding="utf-8")
    patched = patch_build_id(source)
    root.write_text(patched, encoding="utf-8")
    print(f"{MARK}: PASS")
    print(f"runtime_marker={DIRECTHOME_MARKER}")
    print("scope=log_only_emulator_session_start")


if __name__ == "__main__":
    main()
