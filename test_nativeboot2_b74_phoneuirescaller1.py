#!/usr/bin/env python3
"""Contract for NATIVEBOOT2 B74 PHONEUIRESCALLER1."""
from pathlib import Path
import sys

MARK="NATIVEBOOT2-B74-PHONEUIRESCALLER1-TEST"

def fail(msg):
    raise SystemExit(f"{MARK}: FAIL: {msg}")

def need(text,needle,where):
    if needle not in text:
        fail(f"missing in {where}: {needle}")

def main():
    if len(sys.argv)!=2:
        fail("usage: test_nativeboot2_b74_phoneuirescaller1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    fs=(up/"src/emu/services/src/fs/fs.cpp").read_text(encoding="utf-8")
    files=(up/"src/emu/services/src/fs/files.cpp").read_text(encoding="utf-8")
    sv=(up/"src/emu/kernel/src/svc.cpp").read_text(encoding="utf-8")

    for marker in (
        "[NBOOT2][PHONEUI_RES_CALLER]",
        "[NBOOT2][PHONEUI_RES_FRAME]",
        "[NBOOT2][PHONEUI_RES_ID]",
        "[NBOOT2][PHONEUI_RES_CONTEXT_DONE]",
    ):
        need(fs,marker,"fs.cpp")

    need(fs,'u"z:\\resource\\apps\\phoneui.r01"',"PhoneUI path")
    need(fs,'u"z:\\resource\\apps\\callhandlingui.r01"',"CallHandlingUI path")
    need(fs,"0x1099B02DU","CallHandlingUI resource id")
    need(fs,"0x80ED8DA8U","PhoneUIUtils runtime range")
    need(fs,"0x806E8E68U","CONE runtime range")
    need(fs,"nboot2_b74_words=96","bounded stack scan")
    need(fs,"get_thread_context()","saved guest context")

    # Preserve the evidence chain.
    need(fs,"[NBOOT2][PHONEUI_FS_FLOW]","B73")
    need(files,"[NBOOT2][PHONEUI_RSC_OPEN]","B73")
    need(files,"[NBOOT2][PHONEUI_RSC_READ]","B72")
    need(sv,"[NBOOT2][CONE14_PHONEUI]","B71")

    # B74 must not change guest or FileServer behavior.
    b=fs.find("// B74: capture the saved Telephone guest context")
    e=fs.find("switch (ctx->msg->function & 0xFF)",b)
    if b<0 or e<0:
        fail("cannot isolate B74 diagnostic")
    block=fs[b:e]
    for forbidden in (
        "ctx->complete(",
        "ctx->write_",
        "set_int(",
        "requested=102",
        "ESimUsable",
        "reason = 0",
        "kill(",
    ):
        if forbidden in block:
            fail("behavior-changing token: "+forbidden)

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    print(MARK+": PASS")
    print("scope=TELEPHONE_RESOURCE_CALLER_CONTEXT_DIAGNOSTIC")
    print("targets=PHONEUI_R01_AND_CALLHANDLINGUI_R01")
    print("resource_registration=UNCHANGED")
    print("panic_behavior=UNCHANGED")
    print("state_injection=NONE")
    print("sim_injection=NONE")

if __name__=="__main__":
    main()
