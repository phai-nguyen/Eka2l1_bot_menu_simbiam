#!/usr/bin/env python3
"""NATIVEBOOT2 B89: advance past the exact B88 PhoneUI fatal-state result."""

from pathlib import Path
import sys


MARK = "NATIVEBOOT2-B89-FATALSTATEBYPASS1"
LOG_MARKER = "[NBOOT2][PHONEUI_FAILSTATE_BYPASS_B89]"


def fail(message):
    raise SystemExit(f"{MARK}: {message}")


def apply(upstream_root):
    """Arm after the exact B88 PhoneUI exit and bypass its fatal state."""
    upstream = Path(upstream_root).resolve()
    svc = upstream / "src/emu/kernel/src/svc.cpp"
    if not svc.is_file():
        fail(f"missing source: {svc}")

    source = svc.read_text(encoding="utf-8")
    if LOG_MARKER in source:
        if source.count(LOG_MARKER) == 2 and source.count(
            "nboot2_b89_phoneui_bypass_seen() = true;"
        ) == 1:
            print(MARK + ": already applied")
            return
        fail("partial B89 application detected")

    for marker in (
        "[NBOOT2][PHONEUI_CONE14_CONTINUE_B88]",
        "[NBOOT2][STARTER_GLOBAL_STATE]",
    ):
        if marker not in source:
            fail(f"required predecessor evidence missing: {marker}")

    thread_sig = "    BRIDGE_FUNC(std::int32_t, thread_kill,"
    if source.count(thread_sig) != 1:
        fail("expected one thread_kill function")
    helper = (
        "    // B89 one-shot handoff from the exact B88 Telephone exit.\n"
        "    static bool &nboot2_b89_phoneui_bypass_seen() {\n"
        "        static bool seen = false;\n"
        "        return seen;\n"
        "    }\n\n"
    )
    source = source.replace(thread_sig, helper + thread_sig, 1)

    arm_anchor = "        if (nboot2_b71_phoneui_cone14) {\n"
    if source.count(arm_anchor) != 1:
        fail("B88 exact Telephone panic gate not found once")
    arm = arm_anchor + (
        "            nboot2_b89_phoneui_bypass_seen() = true;\n"
        "            LOG_WARN(KERNEL,\n"
        f'                "{LOG_MARKER} phase=armed target_uid3=0x{{:08X}} '
        'reason=14 category=CONE",\n'
        "                nboot2_b71_target_uid3);\n"
    )
    source = source.replace(arm_anchor, arm, 1)

    setter_sig = (
        "    BRIDGE_FUNC(std::int32_t, property_find_set_int, "
        "std::int32_t cage, std::int32_t key, std::int32_t value) {"
    )
    start = source.find(setter_sig)
    end = source.find("\n    BRIDGE_FUNC(", start + len(setter_sig))
    if start < 0 or end < 0:
        fail("category/key property setter bounds not found")
    block = source[start:end]
    setter = "const bool res = prop->set_int(value);"
    if block.count(setter) != 1:
        fail("expected B58/B62 integer property setter exactly once")

    logic = (
        "std::int32_t nboot2_b89_effective = value;\n"
        "        kernel::process *nboot2_b89_pr = kern->crr_process();\n"
        "        const std::uint32_t nboot2_b89_uid3 = nboot2_b89_pr\n"
        "            ? static_cast<std::uint32_t>(\n"
        "                std::get<2>(nboot2_b89_pr->get_uid_type())) : 0;\n"
        "        if (nboot2_b89_phoneui_bypass_seen() &&\n"
        "            static_cast<std::uint32_t>(cage) == 0x101F8766U &&\n"
        "            static_cast<std::uint32_t>(key) == 0x00000041U &&\n"
        "            nboot2_b58_before == 101 && value == 116 &&\n"
        "            nboot2_b89_uid3 == 0x100059C9U) {\n"
        "            nboot2_b89_effective = 109;\n"
        "            nboot2_b89_phoneui_bypass_seen() = false;\n"
        "            LOG_WARN(KERNEL,\n"
        f'                "{LOG_MARKER} phase=state category=0x{{:08X}} '
        'key=0x{:08X} before={} requested={} applied={} process={} '
        'uid3=0x{:08X} policy=NORMAL_RF_ON_AFTER_PHONEUI_BYPASS",\n'
        "                static_cast<std::uint32_t>(cage),\n"
        "                static_cast<std::uint32_t>(key), nboot2_b58_before,\n"
        "                value, nboot2_b89_effective,\n"
        "                nboot2_b89_pr ? nboot2_b89_pr->name()\n"
        '                              : std::string("<null>"),\n'
        "                nboot2_b89_uid3);\n"
        "        }\n"
        "        const bool res = prop->set_int(nboot2_b89_effective);"
    )
    block = block.replace(setter, logic, 1)
    if "prop->set_int(value)" in block:
        fail("original unfiltered P&S setter remains")
    if block.count("prop->set_int(nboot2_b89_effective)") != 1:
        fail("effective state setter count mismatch")

    source = source[:start] + block + source[end:]
    svc.write_text(source, encoding="utf-8")
    print(MARK + ": applied")
    print("gate=B88 Telephone UID3 0x100058B3 / CONE / reason 14")
    print("state=SYSSTART P&S 101->116 rewritten to 109 NormalRfOn")
    print("one_shot=true; all other P&S writes and failures unchanged")


def main():
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b89_fatalstatebypass1.py <upstream-root>")
    apply(sys.argv[1])


if __name__ == "__main__":
    main()
