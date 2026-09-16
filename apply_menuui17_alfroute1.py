#!/usr/bin/env python3
from pathlib import Path
import subprocess
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply_menuui17_alfroute1.py <upstream-root>")

repo = Path(__file__).resolve().parent
upstream = Path(sys.argv[1]).resolve()
svc_path = upstream / "src/emu/kernel/src/svc.cpp"
if not svc_path.is_file():
    raise SystemExit(f"MENUUI17 FIX4: missing source file: {svc_path}")

svc_text = svc_path.read_text(encoding="utf-8")
eka2_sig = "BRIDGE_FUNC(std::int32_t, message_ipc_copy,"
eka1_sig = "BRIDGE_FUNC(std::int32_t, message_ipc_copy_eka1,"
eka2_count = svc_text.count(eka2_sig)
eka1_count = svc_text.count(eka1_sig)
eka2_pos = svc_text.find(eka2_sig)
eka1_pos = svc_text.find(eka1_sig)
if eka2_count != 1 or eka1_count != 1 or eka2_pos < 0 or eka1_pos < 0 or eka2_pos >= eka1_pos:
    raise SystemExit(
        "MENUUI17 FIX4: message_ipc_copy source layout changed: "
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
        "MENUUI17 FIX4: EKA2 result-line guard failed: "
        f"eka2={eka2_body.count(result_line)} eka1={eka1_body.count(result_line)}"
    )

ORIGINAL_COMMIT = "4e6835893cb93bfd6a8be3a5aec9c8bd9c9d7296"
try:
    original = subprocess.check_output(
        ["git", "-C", str(repo), "show", f"{ORIGINAL_COMMIT}:apply_menuui17_alfroute1.py"],
        text=True,
    )
except subprocess.CalledProcessError as exc:
    raise SystemExit(f"MENUUI17 FIX4: unable to load frozen original patcher: {exc}")

# The generic entry block exists in both EKA2 message_ipc_copy() and the later
# EKA1 variant. The original uses replace(..., 1); the ordering guard above
# proves that the first copy is the EKA2 function we want to instrument.
entry_gate_old = "if svc.count(copy_anchor) != 1:"
entry_gate_new = "if svc.count(copy_anchor) != 2:"
if original.count(entry_gate_old) != 1:
    raise SystemExit(
        f"MENUUI17 FIX4: frozen entry gate changed: count={original.count(entry_gate_old)}"
    )
original = original.replace(entry_gate_old, entry_gate_new, 1)

# RUN2/RUN3 proved that the old result anchor is too brittle because it couples
# the EKA2 do_ipc_manipulation call to the following unref/return formatting.
# Shorten only the literal payload inside copy_result_anchor. This avoids FIX3's
# escaped-triple-quote meta-match bug while keeping the frozen diagnostic body.
result_anchor_payload_old = (
    result_line
    + "        msg->unref();\n"
    + "\n"
    + "        return result;\n"
)
if original.count(result_anchor_payload_old) != 1:
    raise SystemExit(
        "MENUUI17 FIX4: frozen result-anchor payload changed: "
        f"count={original.count(result_anchor_payload_old)}"
    )
original = original.replace(result_anchor_payload_old, result_line, 1)

# After shortening copy_result_anchor to one line, leave the real source's
# msg->unref()/return tail in place. Remove that tail only from the generated
# replacement block, scoped between copy_result and its svc.replace call.
copy_result_start_token = "copy_result = r'''"
copy_result_end_token = "'''\nsvc = svc.replace(copy_result_anchor, copy_result, 1)"
copy_result_start = original.find(copy_result_start_token)
copy_result_end = original.find(copy_result_end_token, copy_result_start + len(copy_result_start_token))
if copy_result_start < 0 or copy_result_end < 0:
    raise SystemExit(
        "MENUUI17 FIX4: frozen copy_result block layout changed: "
        f"start={copy_result_start} end={copy_result_end}"
    )
copy_result_block = original[copy_result_start:copy_result_end]
replacement_tail = "        }\n        msg->unref();\n\n        return result;\n"
if copy_result_block.count(replacement_tail) != 1:
    raise SystemExit(
        "MENUUI17 FIX4: frozen copy_result tail changed: "
        f"count={copy_result_block.count(replacement_tail)}"
    )
copy_result_block_new = copy_result_block.replace(replacement_tail, "        }\n", 1)
original = original[:copy_result_start] + copy_result_block_new + original[copy_result_end:]

# ALF_PTR_COPY intentionally appears twice in generated source (enter/result).
# The remaining diagnostic markers are singletons.
marker_gate_old = '''for marker in markers:\n    if svc.count(marker) != 1:\n        raise SystemExit(f"MENUUI17: marker postcondition failed: {marker} count={svc.count(marker)}")\n'''
marker_gate_new = '''for marker in markers:\n    expected_count = 2 if marker == "SYMBIAN-SYSTEMAPPS1 MENUUI17 ALF_PTR_COPY:" else 1\n    if svc.count(marker) != expected_count:\n        raise SystemExit(\n            f"MENUUI17: marker postcondition failed: {marker} "\n            f"count={svc.count(marker)} expected={expected_count}"\n        )\n'''
if original.count(marker_gate_old) != 1:
    raise SystemExit(
        "MENUUI17 FIX4: frozen marker postcondition changed: "
        f"count={original.count(marker_gate_old)}"
    )
original = original.replace(marker_gate_old, marker_gate_new, 1)

# Execute the frozen diagnostic patcher with source-matching corrections only.
# No pointer, focus, IPC, descriptor, payload, timing or completion semantics are
# intentionally changed by FIX4.
ns = {
    "__name__": "__main__",
    "__file__": str(repo / "apply_menuui17_alfroute1_frozen_fix4.py"),
}
sys.argv = [ns["__file__"], str(upstream)]
exec(compile(original, ns["__file__"], "exec"), ns, ns)
