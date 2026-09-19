#!/usr/bin/env python3
"""MENUUI30 STOCKFEP1: restore Nokia stock Avkon FEP on iOS.

MENUUI29 device evidence proves Msg. editor connects to peninputserver but never
sends SetUiLayoutId/ActivateLayout. Upstream iOS EKA2L1 installs
avkonfep_general.dll over Z:\\sys\\bin\\avkonfep.dll for epoc93fp1+.
That DLL is CHostBridgedImeFEP, whose own README says it overrides the default
FEP because native touch IME is broken/outdated on emulator.

For the real-Nokia VKB path we must stop replacing the firmware FEP. The iOS
installer already preserves the original as avkonfep.dll.bak on first patch.
This change:
- removes avkonfep_general.dll from the iOS mandatory ROM-copy list;
- restores avkonfep.dll from avkonfep.dll.bak when the backup exists;
- leaves goommonitor and all other HLE patch resources untouched;
- preserves MENUUI29 trace + MENUUI28 PenInput bridge and all prior lineage.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK="MENUUI30 STOCKFEP1"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: {msg}")

def replace_once(text: str, old: str, new: str, name: str) -> str:
    n=text.count(old)
    if n != 1:
        fail(f"{name}: expected one anchor, found {n}")
    return text.replace(old,new,1)

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_menuui30_stockfep1.py <upstream-root>")
    up=Path(sys.argv[1]).resolve()
    ios=up/"src/emu/ios/Bridge/IosEmulator.mm"
    svc=up/"src/emu/kernel/src/svc.cpp"
    anim=up/"src/emu/services/src/window/classes/plugins/animdll.cpp"
    if not ios.is_file():
        fail(f"missing {ios}")
    if "SYMBIAN-SYSTEMAPPS1 MENUUI29 PENINPUT_IPC:" not in svc.read_text(encoding="utf-8"):
        fail("MENUUI29 baseline missing")
    if "SYMBIAN-SYSTEMAPPS1 MENUUI28 PENINPUT_ANIM:" not in anim.read_text(encoding="utf-8"):
        fail("MENUUI28 baseline missing")
    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    text=ios.read_text(encoding="utf-8")
    if "SYMBIAN-SYSTEMAPPS1 MENUUI30 STOCK_FEP:" in text:
        print("MENUUI30 already present")
        return

    old='''        const std::vector<std::tuple<std::u16string, std::string, epocver>> dlls_need_to_copy = {
            { u"Z:\\\\sys\\\\bin\\\\goommonitor.dll", "goommonitor_general.dll", epocver::epoc94 },
            { u"Z:\\\\sys\\\\bin\\\\avkonfep.dll", "avkonfep_general.dll", epocver::epoc93fp1 }
        };
'''
    new='''        const std::vector<std::tuple<std::u16string, std::string, epocver>> dlls_need_to_copy = {
            { u"Z:\\\\sys\\\\bin\\\\goommonitor.dll", "goommonitor_general.dll", epocver::epoc94 }
        };
'''
    text=replace_once(text,old,new,"remove mandatory Avkon FEP override")

    old='''            common::copy_file(source, dest, true);
        }
    }
}
'''
    new='''            common::copy_file(source, dest, true);
        }

        // MENUUI30 STOCKFEP1: EKA2L1's iOS frontend used to replace the
        // firmware Avkon FEP with HostBridgedImeFEP. The real Nokia touch
        // keyboard path needs the firmware FEP, while the original copy is
        // already preserved by the old installer as avkonfep.dll.bak.
        const auto stock_fep_raw = io->get_raw_path(u"Z:\\\\sys\\\\bin\\\\avkonfep.dll");
        if (stock_fep_raw.has_value()) {
            const std::string stock_fep = common::ucs2_to_utf8(stock_fep_raw.value());
            const std::string stock_fep_backup = stock_fep + ".bak";
            if (common::exists(stock_fep_backup)) {
                const bool restored = common::copy_file(stock_fep_backup, stock_fep, true);
                LOG_WARN(eka2l1::FRONTEND_CMDLINE,
                    "SYMBIAN-SYSTEMAPPS1 MENUUI30 STOCK_FEP: result={} source='{}' dest='{}'",
                    restored ? "restored" : "copy_failed", stock_fep_backup, stock_fep);
            } else {
                LOG_WARN(eka2l1::FRONTEND_CMDLINE,
                    "SYMBIAN-SYSTEMAPPS1 MENUUI30 STOCK_FEP: result=no_backup_keep_current dest='{}'",
                    stock_fep);
            }
        } else {
            LOG_WARN(eka2l1::FRONTEND_CMDLINE,
                "SYMBIAN-SYSTEMAPPS1 MENUUI30 STOCK_FEP: result=no_raw_path");
        }
    }
}
'''
    text=replace_once(text,old,new,"stock FEP restore block")
    ios.write_text(text,encoding="utf-8")

    final=ios.read_text(encoding="utf-8")
    if '"avkonfep_general.dll", epocver::epoc93fp1' in final:
        fail("Avkon FEP override still in mandatory copy list")
    for gate in (
        "SYMBIAN-SYSTEMAPPS1 MENUUI30 STOCK_FEP:",
        'stock_fep + ".bak"',
        'common::copy_file(stock_fep_backup, stock_fep, true)',
        'goommonitor_general.dll',
    ):
        if gate not in final:
            fail(f"missing gate: {gate}")

    print("MENUUI30 STOCKFEP1 applied")
    print("avkonfep_override=DISABLED_ON_IOS")
    print("stock_avkonfep_backup=RESTORED_IF_PRESENT")
    print("goommonitor=UNCHANGED")
    print("MENUUI29/MENUUI28/prior=Preserved")

if __name__=="__main__":
    main()
