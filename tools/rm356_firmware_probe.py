#!/usr/bin/env python3
"""Inventory and compare extracted Nokia 5800 RM-356 firmware trees.

This is a research tool only. It does not patch firmware or EKA2L1.

Examples:
  python3 tools/rm356_firmware_probe.py APAC52=/path/fw52 V60=/path/fw60
  python3 tools/rm356_firmware_probe --json report.json APAC52=/path/fw52
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

CENREP_REL = "private/10202be9/102818e8.txt"
EXACT_NAMES = {
    "aknskinsrv.exe",
    "aknskinsrv.dll",
    "tfxsrvplugin.dll",
    "akntransitionutils.dll",
    "aknlistloadertfx.dll",
}
ECOM_UIDS = ("10282dbd", "10282dbc")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def norm_rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix().lower()


def decode_text(path: Path) -> str:
    raw = path.read_bytes()
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return raw.decode("utf-16")
    for enc in ("utf-8-sig", "utf-16-le", "latin-1"):
        try:
            text = raw.decode(enc)
            # Reject a false UTF-16 decode of ordinary 8-bit ASCII.
            if enc == "utf-16-le" and "\x00" not in raw.decode("latin-1", errors="ignore"):
                continue
            return text
        except UnicodeDecodeError:
            pass
    return raw.decode("latin-1", errors="replace")


def parse_key9(path: Path) -> dict[str, Any]:
    text = decode_text(path)
    # Typical Symbian CenRep text line:
    # 0x00000009 int 0x7fffffff 0
    pat = re.compile(
        r"^\s*0x0*9\b\s+(?:int|integer)\s+(0x[0-9a-fA-F]+|-?\d+)\b",
        re.IGNORECASE,
    )
    for lineno, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line.split("#", 1)[0].strip()
        m = pat.search(line)
        if not m:
            continue
        token = m.group(1)
        value = int(token, 0)
        if value < 0:
            value_u32 = value & 0xFFFFFFFF
        else:
            value_u32 = value
        if value_u32 == 0x7FFFFFFF:
            state = "KMaxTInt/theme-effects-disabled"
        elif value_u32 == 0x8:
            state = "enabled-default"
        elif value_u32 == 0:
            state = "automatic-or-zero"
        else:
            state = "non-KMaxTInt"
        return {
            "found": True,
            "line": lineno,
            "token": token,
            "value": value,
            "value_u32": value_u32,
            "hex_u32": f"0x{value_u32:08X}",
            "classification": state,
            "raw": raw_line.strip(),
        }
    return {"found": False, "classification": "key-0x9-not-found"}


def classify(path: Path, root: Path) -> str | None:
    rel = norm_rel(path, root)
    name = path.name.lower()
    if rel.endswith(CENREP_REL):
        return "themes_cenrep_102818e8"
    if name in EXACT_NAMES:
        return name
    if name.startswith("alfredserver"):
        return "alfredserver*"
    if any(uid in rel for uid in ECOM_UIDS):
        return "ecom_tfx_uid_registration"
    if (
        ("alf" in name or "tfx" in name or "transition" in name)
        and path.suffix.lower() in {".rsc", ".rss", ".spi", ".dll", ".exe"}
    ):
        return "alf_tfx_related"
    return None


def scan_root(label: str, root: Path) -> dict[str, Any]:
    if not root.is_dir():
        raise ValueError(f"{label}: not a directory: {root}")
    hits: dict[str, list[dict[str, Any]]] = {}
    files_seen = 0
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        files_seen += 1
        kind = classify(path, root)
        if not kind:
            continue
        entry = {
            "path": path.relative_to(root).as_posix(),
            "size": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        if kind == "themes_cenrep_102818e8":
            entry["key_0x9"] = parse_key9(path)
        hits.setdefault(kind, []).append(entry)
    for items in hits.values():
        items.sort(key=lambda x: x["path"].lower())
    return {
        "label": label,
        "root": str(root),
        "files_seen": files_seen,
        "hits": hits,
    }


def compare(scans: list[dict[str, Any]]) -> dict[str, Any]:
    by_kind: dict[str, dict[str, list[str]]] = {}
    for scan in scans:
        label = scan["label"]
        for kind, items in scan["hits"].items():
            by_kind.setdefault(kind, {})[label] = [x["sha256"] for x in items]
    result: dict[str, Any] = {}
    for kind, labels in sorted(by_kind.items()):
        present = sorted(labels)
        digest_sets = {label: tuple(v) for label, v in labels.items()}
        same = len(set(digest_sets.values())) == 1 and len(present) == len(scans)
        result[kind] = {
            "present_in": present,
            "present_in_all": len(present) == len(scans),
            "identical_sha256_sets": same,
        }
    return result


def print_report(report: dict[str, Any]) -> None:
    print("RM-356 firmware probe")
    print("=" * 72)
    for scan in report["firmwares"]:
        print(f"\n[{scan['label']}] root={scan['root']} files={scan['files_seen']}")
        if not scan["hits"]:
            print("  no target components found")
            continue
        for kind, items in sorted(scan["hits"].items()):
            print(f"  {kind}:")
            for item in items:
                print(f"    {item['path']}  size={item['size']}  sha256={item['sha256']}")
                if "key_0x9" in item:
                    k = item["key_0x9"]
                    print(
                        "      key0x9="
                        + (f"{k.get('hex_u32')} {k['classification']}" if k["found"]
                           else k["classification"])
                    )
    if len(report["firmwares"]) > 1:
        print("\n[comparison]")
        for kind, item in report["comparison"].items():
            print(
                f"  {kind}: present={','.join(item['present_in'])} "
                f"all={int(item['present_in_all'])} "
                f"same_hashes={int(item['identical_sha256_sets'])}"
            )


def parse_spec(spec: str) -> tuple[str, Path]:
    if "=" not in spec:
        raise argparse.ArgumentTypeError("firmware must be LABEL=/extracted/root")
    label, value = spec.split("=", 1)
    label = label.strip()
    if not label or not value:
        raise argparse.ArgumentTypeError("firmware must be LABEL=/extracted/root")
    return label, Path(value).expanduser().resolve()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("firmware", nargs="+", type=parse_spec, help="LABEL=/extracted/root")
    ap.add_argument("--json", dest="json_path", type=Path, help="write machine-readable report")
    args = ap.parse_args()

    labels: set[str] = set()
    scans = []
    for label, root in args.firmware:
        if label in labels:
            ap.error(f"duplicate label: {label}")
        labels.add(label)
        scans.append(scan_root(label, root))

    report = {
        "schema": 1,
        "purpose": "RM-356 AknSkin/TFX firmware comparison",
        "firmwares": scans,
        "comparison": compare(scans),
    }
    print_report(report)
    if args.json_path:
        args.json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
