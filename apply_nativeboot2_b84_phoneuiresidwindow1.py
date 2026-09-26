#!/usr/bin/env python3
"""NATIVEBOOT2 B84 PHONEUIRESIDWINDOW1.

At the already-proven Telephone/CONE 14 boundary, report every register and
bounded stack occurrence of resource ID 0x1099B02D plus a small read-only
stack window.  This is diagnostic-only and does not register a resource or
change boot, panic, CPU, or guest-memory state.
"""
from pathlib import Path
import sys

MARK = "NATIVEBOOT2-B84-PHONEUIRESIDWINDOW1"


def fail(message):
    raise SystemExit(f"{MARK}: {message}")


def main():
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b84_phoneuiresidwindow1.py <upstream-root>")

    upstream = Path(sys.argv[1]).resolve()
    svc_path = upstream / "src/emu/kernel/src/svc.cpp"
    if not svc_path.is_file():
        fail(f"missing source: {svc_path}")

    source = svc_path.read_text(encoding="utf-8")
    markers = (
        "[NBOOT2][PHONEUI_RESID_SOURCE]",
        "[NBOOT2][PHONEUI_RESID_WINDOW]",
        "[NBOOT2][PHONEUI_RESID_SUMMARY]",
    )
    present = [marker for marker in markers if marker in source]
    if len(present) == len(markers):
        print(MARK + ": already applied")
        return
    if present:
        fail("partial B84 application detected: " + ", ".join(present))

    for token in (
        "[NBOOT2][CONE14_PHONEUI]",
        "[NBOOT2][CONE14_SUMMARY]",
        "nboot2_b71_phoneui_cone14",
        "const std::uint32_t sp=cpu->get_reg(13);",
    ):
        if token not in source:
            fail(f"B71 diagnostic gate missing: {token}")

    anchor = '''            LOG_WARN(KERNEL,
                "[NBOOT2][CONE14_SUMMARY] meaning=NoResourceFileForId "
'''
    if source.count(anchor) != 1:
        fail(f"CONE14 summary anchor expected once, found {source.count(anchor)}")

    diagnostic = r'''            // B84 PHONEUIRESIDWINDOW1: observe only the exact
            // resource ID already present at the proven Telephone/CONE14
            // boundary. Guest registers, memory, panic and resource state are
            // never modified.
            constexpr std::uint32_t nboot2_b84_resource_id=0x1099B02DU;
            constexpr std::uint32_t nboot2_b84_stack_words=128U;
            constexpr std::int32_t nboot2_b84_window_radius=8;
            std::uint32_t nboot2_b84_register_hits=0;
            std::uint32_t nboot2_b84_stack_hits=0;

            for (std::uint32_t reg=0;reg<=14U;++reg) {
                const std::uint32_t value=cpu->get_reg(reg);
                if (value==nboot2_b84_resource_id) {
                    ++nboot2_b84_register_hits;
                    LOG_WARN(KERNEL,
                        "[NBOOT2][PHONEUI_RESID_SOURCE] source=REGISTER "
                        "index={} value=0x{:08X} owner=callhandlingui.r01 "
                        "behavior=OBSERVE_ONLY",
                        reg,value);
                }
            }

            for (std::uint32_t index=0;
                 index<nboot2_b84_stack_words;++index) {
                const std::uint64_t slot64=
                    static_cast<std::uint64_t>(sp)+
                    static_cast<std::uint64_t>(index)*sizeof(std::uint32_t);
                if (slot64>0xFFFFFFFFULL) {
                    break;
                }
                const std::uint32_t slot_addr=
                    static_cast<std::uint32_t>(slot64);
                const std::uint32_t *slot=
                    eka2l1::ptr<std::uint32_t>(slot_addr).get(caller_pr);
                if (!slot) {
                    break;
                }
                if (*slot!=nboot2_b84_resource_id) {
                    continue;
                }

                ++nboot2_b84_stack_hits;
                LOG_WARN(KERNEL,
                    "[NBOOT2][PHONEUI_RESID_SOURCE] source=STACK "
                    "index={} address=0x{:08X} value=0x{:08X} "
                    "owner=callhandlingui.r01 behavior=OBSERVE_ONLY",
                    index,slot_addr,*slot);

                for (std::int32_t delta=-nboot2_b84_window_radius;
                     delta<=nboot2_b84_window_radius;++delta) {
                    const std::int64_t window64=
                        static_cast<std::int64_t>(slot_addr)+
                        static_cast<std::int64_t>(delta)*
                            static_cast<std::int64_t>(sizeof(std::uint32_t));
                    if ((window64<0) || (window64>0xFFFFFFFFLL)) {
                        continue;
                    }
                    const std::uint32_t address=
                        static_cast<std::uint32_t>(window64);
                    const std::uint32_t *word=
                        eka2l1::ptr<std::uint32_t>(address).get(caller_pr);
                    if (!word) {
                        LOG_WARN(KERNEL,
                            "[NBOOT2][PHONEUI_RESID_WINDOW] hit_index={} "
                            "delta={} address=0x{:08X} mapped=0 "
                            "behavior=OBSERVE_ONLY",
                            index,delta,address);
                        continue;
                    }
                    LOG_WARN(KERNEL,
                        "[NBOOT2][PHONEUI_RESID_WINDOW] hit_index={} "
                        "delta={} address=0x{:08X} value=0x{:08X} mapped=1 "
                        "behavior=OBSERVE_ONLY",
                        index,delta,address,*word);
                }
            }

            LOG_WARN(KERNEL,
                "[NBOOT2][PHONEUI_RESID_SUMMARY] resource_id=0x{:08X} "
                "register_hits={} stack_hits={} stack_words={} radius={} "
                "resource_registration=UNCHANGED boot_behavior=UNCHANGED "
                "behavior=OBSERVE_ONLY",
                nboot2_b84_resource_id,nboot2_b84_register_hits,
                nboot2_b84_stack_hits,nboot2_b84_stack_words,
                nboot2_b84_window_radius);

'''
    source = source.replace(anchor, diagnostic + anchor, 1)
    svc_path.write_text(source, encoding="utf-8")

    print(MARK + ": applied")
    print("scope=TELEPHONE_CONE14_EXACT_RESOURCE_ID_WINDOW")
    print("resource_id=0x1099B02D")
    print("resource_registration=UNCHANGED")
    print("boot_behavior=UNCHANGED")


if __name__ == "__main__":
    main()
