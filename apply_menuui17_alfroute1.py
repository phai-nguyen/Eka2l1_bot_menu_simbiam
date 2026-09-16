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
    raise SystemExit(f"MENUUI17 FIX2: missing source file: {svc}")

# Build #35104166690 proved the original ALFROUTE1 patcher reaches the frozen
# MENUUI16 authority correctly, but its generic message_ipc_copy anchors occur
# twice in svc.cpp: once in EKA2 message_ipc_copy() and once in the later
# message_ipc_copy_eka1(). The EKA2 function appears first and is the intended
# target. The original patcher uses replace(..., 1), so changing the two anchor
# count gates from 1 to 2 safely selects the first (EKA2) occurrence after the
# ordering/count checks below.
svc_text = svc.read_text(encoding="utf-8")
eka2_sig = "BRIDGE_FUNC(std::int32_t, message_ipc_copy,"
eka1_sig = "BRIDGE_FUNC(std::int32_t, message_ipc_copy_eka1,"
eka2_count = svc_text.count(eka2_sig)
eka1_count = svc_text.count(eka1_sig)
eka2_pos = svc_text.find(eka2_sig)
eka1_pos = svc_text.find(eka1_sig)
if eka2_count != 1 or eka1_count != 1 or eka2_pos >= eka1_pos:
    raise SystemExit(
        "MENUUI17 FIX2: message_ipc_copy source layout changed: "
        f"eka2_count={eka2_count} eka1_count={eka1_count} "
        f"eka2_pos={eka2_pos} eka1_pos={eka1_pos}"
    )

ORIGINAL_COMMIT = "4e6835893cb93bfd6a8be3a5aec9c8bd9c9d7296"
try:
    original = subprocess.check_output(
        ["git", "-C", str(repo), "show", f"{ORIGINAL_COMMIT}:apply_menuui17_alfroute1.py"],
        text=True,
    )
except subprocess.CalledProcessError as exc:
    raise SystemExit(f"MENUUI17 FIX2: unable to load frozen original patcher: {exc}")

replacements = {
    "if svc.count(copy_anchor) != 1:": "if svc.count(copy_anchor) != 2:",
    "if svc.count(copy_result_anchor) != 1:": "if svc.count(copy_result_anchor) != 2:",
}
for old, new in replacements.items():
    if original.count(old) != 1:
        raise SystemExit(
            f"MENUUI17 FIX2: frozen patcher anchor gate changed: {old!r} "
            f"count={original.count(old)}"
        )
    original = original.replace(old, new, 1)

# The original diagnostic intentionally emits ALF_PTR_COPY twice: once at
# stage=enter and once at stage=result. Its generic postcondition incorrectly
# required every marker literal to appear exactly once, so it would fail after
# the anchor fix even though the generated source was correct.
marker_gate_old = '''for marker in markers:\n    if svc.count(marker) != 1:\n        raise SystemExit(f"MENUUI17: marker postcondition failed: {marker} count={svc.count(marker)}")\n'''
marker_gate_new = '''for marker in markers:\n    expected_count = 2 if marker == "SYMBIAN-SYSTEMAPPS1 MENUUI17 ALF_PTR_COPY:" else 1\n    if svc.count(marker) != expected_count:\n        raise SystemExit(\n            f"MENUUI17: marker postcondition failed: {marker} "\n            f"count={svc.count(marker)} expected={expected_count}"\n        )\n'''
if original.count(marker_gate_old) != 1:
    raise SystemExit(
        "MENUUI17 FIX2: frozen marker postcondition changed: "
        f"count={original.count(marker_gate_old)}"
    )
original = original.replace(marker_gate_old, marker_gate_new, 1)

# Execute the frozen diagnostic patcher in-process with only the three validated
# gate corrections above. No touch, IPC, focus, timing, payload or completion
# behavior is changed by this wrapper.
ns = {
    "__name__": "__main__",
    "__file__": str(repo / "apply_menuui17_alfroute1_frozen_fix2.py"),
}
sys.argv = [ns["__file__"], str(upstream)]
exec(compile(original, ns["__file__"], "exec"), ns, ns)
