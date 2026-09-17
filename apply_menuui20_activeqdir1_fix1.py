#!/usr/bin/env python3
from pathlib import Path
import subprocess
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply_menuui20_activeqdir1_fix1.py <upstream-root>")

repo = Path(__file__).resolve().parent
upstream = Path(sys.argv[1]).resolve()

ORIGINAL_COMMIT = "8210c4ee7558ccba37c1f1561ecc6bd04c0e1f3c"
try:
    original = subprocess.check_output(
        ["git", "-C", str(repo), "show", f"{ORIGINAL_COMMIT}:apply_menuui20_activeqdir1.py"],
        text=True,
    )
except subprocess.CalledProcessError as exc:
    raise SystemExit(f"MENUUI20 FIX1: unable to load frozen original patcher: {exc}")

old = '    "SYMBIAN-SYSTEMAPPS1 MENUUI20 ACTIVEQ_DIR:": 1,\n'
new = '    "SYMBIAN-SYSTEMAPPS1 MENUUI20 ACTIVEQ_DIR:": 3,\n'
if original.count(old) != 1:
    raise SystemExit(
        "MENUUI20 FIX1: frozen ACTIVEQ_DIR marker gate changed: "
        f"count={original.count(old)}"
    )
original = original.replace(old, new, 1)

# The three source literals are intentional:
# 1) per-direction walk summary (called for forward/backward at runtime),
# 2) scheduler-invalid fallback, and
# 3) backward-focused compare summary.
# Only the source postcondition is corrected; runtime queue/AO semantics remain untouched.
ns = {
    "__name__": "__main__",
    "__file__": str(repo / "apply_menuui20_activeqdir1_frozen_fix1.py"),
}
sys.argv = [ns["__file__"], str(upstream)]
exec(compile(original, ns["__file__"], "exec"), ns, ns)
