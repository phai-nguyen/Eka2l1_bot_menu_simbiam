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
    raise SystemExit(f"MENUUI17 FIX3: missing source file: {svc}")

svc_text = svc.read_text(encoding="utf-8")
eka2_sig = "BRIDGE_FUNC(std::int32_t, message_ipc_copy,"
eka1_sig = "BRIDGE_FUNC(std::int32_t, message_ipc_copy_eka1,"
eka2_count = svc_text.count(eka2_sig)
eka1_count = svc_text.count(eka1_sig)
eka2_pos = svc_text.find(eka2_sig)
eka1_pos = svc_text.find(eka1_sig)
if eka2_count != 1 or eka1_count != 1 or eka2_pos < 0 or eka1_pos < 0 or eka2_pos >= eka1_pos:
    raise SystemExit(
        "MENUUI17 FIX3: message_ipc_copy source layout changed: "
        f"eka2_count={eka2_count} eka1_count={eka1_count} "
        f"eka2_pos={eka2_pos} eka1_pos={eka1_pos}"
    )

eka2_body = svc_text[eka2_pos:eka1_pos]
eka1_body = svc_text[eka1_pos:]
result_line = (
    "        const std::int32_t result = do_ipc_manipulation(kern, msg->own_thr, "
    "param_ptr_host, *info_host, start_offset);\n"
)
if eka2_body.count(result_line) != 1 or eka1_body.count(result_line) != 0:
    raise SystemExit(
        "MENUUI17 FIX3: EKA2 result-line guard failed: "
        f"eka2={eka2_body.count(result_line)} eka1={eka1_body.count(result_line)}"
    )

ORIGINAL_COMMIT = "4e6835893cb93bfd6a8be3a5aec9c8bd9c9d7296"
try:
    original = subprocess.check_output(
        ["git", "-C", str(repo), "show", f"{ORIGINAL_COMMIT}:apply_menuui17_alfroute1.py"],
        text=True,
    )
except subprocess.CalledProcessError as exc:
    raise SystemExit(f"MENUUI17 FIX3: unable to load frozen original patcher: {exc}")

# The entry block is shared by EKA2 and EKA1. Frozen source contains two copies;
# replace(..., 1) intentionally selects the first one, and the source-order guard
# above proves that first copy belongs to EKA2.
entry_gate_old = "if svc.count(copy_anchor) != 1:"
entry_gate_new = "if svc.count(copy_anchor) != 2:"
if original.count(entry_gate_old) != 1:
    raise SystemExit(
        f"MENUUI17 FIX3: frozen entry gate changed: count={original.count(entry_gate_old)}"
    )
original = original.replace(entry_gate_old, entry_gate_new, 1)

# Run2 proved the old result anchor is too broad after replaying MENUUI16:
# it included msg->unref()/return and had count=0. Anchor only the EKA2-specific
# do_ipc_manipulation line. EKA1 uses info_copy instead of *info_host.
result_anchor_old = '''copy_result_anchor = \'\'\'        const std::int32_t result = do_ipc_manipulation(kern, msg->own_thr, param_ptr_host, *info_host, start_offset);\n        msg->unref();\n\n        return result;\n\'\'\'\n'''
result_anchor_new = '''copy_result_anchor = \'\'\'        const std::int32_t result = do_ipc_manipulation(kern, msg->own_thr, param_ptr_host, *info_host, start_offset);\n\'\'\'\n'''
if original.count(result_anchor_old) != 1:
    raise SystemExit(
        "MENUUI17 FIX3: frozen result-anchor definition changed: "
        f"count={original.count(result_anchor_old)}"
    )
original = original.replace(result_anchor_old, result_anchor_new, 1)

# Since the source tail now remains outside the short replacement anchor, remove
# the duplicated msg->unref()/return from the generated replacement string.
result_tail_old = '''        }\n        msg->unref();\n\n        return result;\n\'\'\'\nsvc = svc.replace(copy_result_anchor, copy_result, 1)\n'''
result_tail_new = '''        }\n\'\'\'\nsvc = svc.replace(copy_result_anchor, copy_result, 1)\n'''
if original.count(result_tail_old) != 1:
    raise SystemExit(
        "MENUUI17 FIX3: frozen result replacement tail changed: "
        f"count={original.count(result_tail_old)}"
    )
original = original.replace(result_tail_old, result_tail_new, 1)

# ALF_PTR_COPY intentionally exists twice in generated source: stage=enter and
# stage=result. All other MENUUI17 marker literals must remain singletons.
marker_gate_old = '''for marker in markers:\n    if svc.count(marker) != 1:\n        raise SystemExit(f"MENUUI17: marker postcondition failed: {marker} count={svc.count(marker)}")\n'''
marker_gate_new = '''for marker in markers:\n    expected_count = 2 if marker == "SYMBIAN-SYSTEMAPPS1 MENUUI17 ALF_PTR_COPY:" else 1\n    if svc.count(marker) != expected_count:\n        raise SystemExit(\n            f"MENUUI17: marker postcondition failed: {marker} "\n            f"count={svc.count(marker)} expected={expected_count}"\n        )\n'''
if original.count(marker_gate_old) != 1:
    raise SystemExit(
        "MENUUI17 FIX3: frozen marker postcondition changed: "
        f"count={original.count(marker_gate_old)}"
    )
original = original.replace(marker_gate_old, marker_gate_new, 1)

# Execute the frozen diagnostic patcher with only validated anchor/postcondition
# corrections. No pointer, focus, IPC, descriptor, timing or completion behavior
# is intentionally changed.
ns = {
    "__name__": "__main__",
    "__file__": str(repo / "apply_menuui17_alfroute1_frozen_fix3.py"),
}
sys.argv = [ns["__file__"], str(upstream)]
exec(compile(original, ns["__file__"], "exec"), ns, ns)
