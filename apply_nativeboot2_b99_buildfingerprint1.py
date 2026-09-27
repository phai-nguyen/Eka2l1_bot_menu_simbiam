#!/usr/bin/env python3
"""Add a log-only runtime identity marker for B99 on H2 no-bypass builds."""
from __future__ import annotations

import sys
from pathlib import Path


MARK = "NATIVEBOOT2-B99-BUILDFINGERPRINT1"
LOG_MARKER = "[NBOOT2][BUILD_ID] build=B99 track=H2_COMPATBOOT1_NOBYPASS1"
ANCHOR = "- (void)startEmulatorWithCompatTarget:(NSInteger)compatTarget {\n"
INSERTION = f'    NSLog(@"{LOG_MARKER}");\n'


def fail(message: str) -> None:
    raise SystemExit(f"{MARK}: FAIL: {message}")


def patch_build_id(source: str) -> str:
    marker_count = source.count(LOG_MARKER)
    anchor_count = source.count(ANCHOR)
    if anchor_count != 1:
        fail(f"emulator-session start anchor: expected one, found {anchor_count}")

    if marker_count == 1:
        if source.count(ANCHOR + INSERTION) != 1:
            fail("existing B99 runtime marker is not immediately after the emulator-session start anchor")
        return source
    if marker_count > 1:
        fail(f"B99 runtime marker appears {marker_count} times")

    patched = source.replace(ANCHOR, ANCHOR + INSERTION, 1)
    if patched.count(LOG_MARKER) != 1:
        fail("post-apply check: B99 runtime marker must appear once")
    return patched


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b99_buildfingerprint1.py <upstream-root>")

    root = Path(sys.argv[1]).resolve() / "src/emu/ios/app/RootViewController.mm"
    if not root.is_file():
        fail(f"missing source file: {root}")

    source = root.read_text(encoding="utf-8")
    patched = patch_build_id(source)
    root.write_text(patched, encoding="utf-8")
    print(f"{MARK}: PASS")
    print(f"runtime_marker={LOG_MARKER}")
    print("scope=log_only_emulator_session_start")


if __name__ == "__main__":
    main()
