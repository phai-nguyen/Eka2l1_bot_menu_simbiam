#!/usr/bin/env python3
from pathlib import Path
import subprocess
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply_menuui17_alfroute1.py <upstream-root>")

repo = Path(__file__).resolve().parent
upstream = Path(sys.argv[1]).resolve()
svc = upstream / "src/emu/kernel/src/svc.cpp"
if not svc.is_file():
    raise SystemExit(f"MENUUI17 FIX1: missing source file: {svc}")

# Build #35104166690 proved the original ALFROUTE1 patcher reaches the frozen
# MENUUI16 authority correctly, but its generic message_ipc_copy anchors occur
# twice in svc.cpp: once in EKA2 message_ipc_copy() and once in the later
# message_ipc_copy_eka1().  The EKA2 function appears first and is the intended
# target.  Keep the original diagnostic patch byte-for-byte except for those two
# anchor-count gates, and assert the source ordering before executing it.
svc_text = svc.read_text(encoding="utf-8")
eka2_sig = "BRIDGE_FUNC(std::int32_t, message_ipc_copy,"
eka1_sig = "BRIDGE_FUNC(std::int32_t, message_ipc_copy_eka1,"
eka2_pos = svc_text.find(eka2_sig)
eka1_pos = svc_text.find(eka1_sig)
if eka2_pos < 0 or eka1_pos < 0 or eka2_pos >= eka1_pos:
    raise SystemExit(
        f"MENUUI17 FIX1: message_ipc_copy source ordering changed: eka2={eka2_pos} eka1={eka1_pos}"
    )

ORIGINAL_COMMIT = "4e6835893cb93bfd6a8be3a5aec9c8bd9c9d7296"
try:
    original = subprocess.check_output(
        ["git", "-C", str(repo), "show", f"{ORIGINAL_COMMIT}:apply_menuui17_alfroute1.py"],
        text=True,
    )
except subprocess.CalledProcessError as exc:
    raise SystemExit(f"MENUUI17 FIX1: unable to load frozen original patcher: {exc}")

replacements = {
    "if svc.count(copy_anchor) != 1:": "if svc.count(copy_anchor) != 2:",
    "if svc.count(copy_result_anchor) != 1:": "if svc.count(copy_result_anchor) != 2:",
}
for old, new in replacements.items():
    if original.count(old) != 1:
        raise SystemExit(f"MENUUI17 FIX1: frozen patcher gate changed: {old!r} count={original.count(old)}")
    original = original.replace(old, new, 1)

# The original patcher uses replace(..., 1), therefore after the ordering gate
# above it patches only EKA2 message_ipc_copy() and leaves the EKA1 variant
# untouched.  Execute the frozen patcher in-process with the normal argv.
ns = {
    "__name__": "__main__",
    "__file__": str(repo / "apply_menuui17_alfroute1_frozen_fix1.py"),
}
sys.argv = [ns["__file__"], str(upstream)]
exec(compile(original, ns["__file__"], "exec"), ns, ns)
