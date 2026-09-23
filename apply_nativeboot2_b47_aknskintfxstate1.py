#!/usr/bin/env python3
"""RED scaffold for NATIVEBOOT2 B47 AKNSKINTFXSTATE1.

Intentionally makes no source change. It exists only so FASTBUILD1 can execute
the B47 contract as a normal apply|test pair before the implementation lands.
"""
from pathlib import Path
import sys
MARK="NATIVEBOOT2-B47-AKNSKINTFXSTATE1-RED"

def main():
    if len(sys.argv)!=2:
        raise SystemExit(f"{MARK}: usage: apply_nativeboot2_b47_aknskintfxstate1.py <upstream-root>")
    up=Path(sys.argv[1]).resolve()
    for p in (
        up/"src/emu/services/src/centralrepo/repo.cpp",
        up/"src/emu/kernel/src/svc.cpp",
        up/"src/emu/services/src/init.cpp",
    ):
        if not p.is_file():
            raise SystemExit(f"{MARK}: missing source: {p}")
    print(f"{MARK}: no-op scaffold")

if __name__=="__main__":
    main()
