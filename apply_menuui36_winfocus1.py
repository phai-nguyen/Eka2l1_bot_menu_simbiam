#!/usr/bin/env python3
"""MENUUI36 WINFOCUS1: make WindowGroup focus eligibility persistent.

V35 device evidence:
- PenInput opcode 510 now completes asynchronously without deadlock.
- The injected EKeyDown is nevertheless delivered to peninputserver's
  WindowGroup (focus_id=62 / client_thread=1302), then peninputserver crashes.
- Nokia PenInput creates root/animation groups and explicitly calls
  EnableReceiptOfFocus(EFalse); both animation setup paths also call
  AutoForeground(EFalse).

EKA2L1 currently stores ReceiveFocus in the generic window flags and leaves
AutoForeground unimplemented. The observed screen focus violates the explicit
ReceiveFocus(false) request.

This patch:
1. Gives WindowGroup a dedicated receives_focus_ state (default false) and
   auto_foreground_ state (default true, matching Nokia WSERV).
2. set_receive_focus() updates both dedicated state and legacy flag.
3. can_receive_focus() uses the dedicated state, so unrelated generic window
   flag changes cannot make a non-focusable overlay eligible again.
4. Implements EWsWinOpAutoForeground (0x26) state storage.
5. Adds a key-shipper invariant: if screen::focus ever points to a group that
   cannot receive focus, recompute focus before delivering a key.
No process name, UID, group ID, scancode, or editor is hardcoded.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK="MENUUI36 WINFOCUS1"

def fail(msg):
    raise SystemExit(f"{MARK}: {msg}")

def replace_once(text, old, new, name):
    n=text.count(old)
    if n!=1:
        fail(f"{name}: expected one anchor, found {n}")
    return text.replace(old,new,1)

def main():
    if len(sys.argv)!=2:
        fail("usage: apply_menuui36_winfocus1.py <upstream-root>")
    up=Path(sys.argv[1]).resolve()
    wgh=up/"src/emu/services/include/services/window/classes/wingroup.h"
    wgc=up/"src/emu/services/src/window/classes/wingroup.cpp"
    io=up/"src/emu/services/src/window/io.cpp"
    win=up/"src/emu/services/src/window/window.cpp"
    anim=up/"src/emu/services/src/window/classes/plugins/animdll.cpp"
    key=up/"src/emu/services/src/audio/keysound/keysound.cpp"
    for p in (wgh,wgc,io,win,anim,key):
        if not p.is_file():
            fail(f"missing baseline file: {p}")
    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")
    if "SYMBIAN-SYSTEMAPPS1 MENUUI35 SIMULATE_EVENT:" not in anim.read_text(encoding="utf-8"):
        fail("MENUUI35 baseline missing")
    if "SYMBIAN-SYSTEMAPPS1 MENUUI33 KEYSOUND13:" not in key.read_text(encoding="utf-8"):
        fail("MENUUI33 baseline missing")
    if "SYMBIAN-SYSTEMAPPS1 MENUUI31 PENINPUT_RAW:" not in win.read_text(encoding="utf-8"):
        fail("MENUUI31 baseline missing")

    h=wgh.read_text(encoding="utf-8")
    if "SYMBIAN-SYSTEMAPPS1 MENUUI36" in h:
        print("MENUUI36 already present")
        return

    # V35 cache comes from an older EKA2L1 tree whose field layout differs
    # from current upstream. Patch the two inline methods by signature instead
    # of anchoring the surrounding data members.
    def inline_span(text, signature):
        start=text.find(signature)
        if start < 0:
            fail(f"inline signature missing: {signature}")
        brace=text.find("{",start)
        if brace < 0:
            fail(f"inline opening brace missing: {signature}")
        depth=0
        for i in range(brace,len(text)):
            if text[i]=="{":
                depth+=1
            elif text[i]=="}":
                depth-=1
                if depth==0:
                    return start,i+1
        fail(f"unterminated inline function: {signature}")

    can_sig="        bool can_receive_focus()"
    can_start,can_end=inline_span(h,can_sig)
    if "receives_focus_" not in h[:can_start]:
        h=h[:can_start]+"""        // MENUUI36: focus eligibility is WindowGroup state in real WSERV.
        // Keep it separate from generic window flags so visibility/fade/etc.
        // can never resurrect keyboard focus for a non-focusable overlay.
        bool receives_focus_{ false };
        bool auto_foreground_{ true };

"""+h[can_start:]

    can_start,can_end=inline_span(h,can_sig)
    h=h[:can_start]+"""        bool can_receive_focus() const {
            return receives_focus_;
        }"""+h[can_end:]

    set_sig="        void set_receive_focus(const bool val)"
    set_start,set_end=inline_span(h,set_sig)
    h=h[:set_start]+"""        void set_receive_focus(const bool val) {
            receives_focus_ = val;
            flags &= ~flag_focus_receiveable;
            if (val) {
                flags |= flag_focus_receiveable;
            }
        }

        bool auto_foreground() const {
            return auto_foreground_;
        }

        void set_auto_foreground(const bool val) {
            auto_foreground_ = val;
        }"""+h[set_end:]
    wgh.write_text(h,encoding="utf-8")

    c=wgc.read_text(encoding="utf-8")
    recv_sig="    void window_group::receive_focus(service::ipc_context &context, ws_cmd &cmd)"
    recv_start,recv_end=inline_span(c,recv_sig)
    recv_new="""    void window_group::receive_focus(service::ipc_context &context, ws_cmd &cmd) {
        const bool requested = (*reinterpret_cast<std::uint32_t *>(cmd.data_ptr) != 0);
        const std::uint32_t focus_before = (scr && scr->focus) ? scr->focus->id : 0;

        set_receive_focus(requested);

        if (requested) {
            LOG_TRACE(SERVICE_WINDOW, "Request group {} to enable keyboard focus", common::ucs2_to_utf8(name));
        } else {
            LOG_TRACE(SERVICE_WINDOW, "Request group {} to disable keyboard focus", common::ucs2_to_utf8(name));
        }

        epoc::window_group *resolved = scr->update_focus(&client->get_ws(), nullptr);
        const std::uint32_t focus_after = (scr && scr->focus) ? scr->focus->id : 0;

        LOG_WARN(SERVICE_WINDOW,
            "SYMBIAN-SYSTEMAPPS1 MENUUI36 WG_FOCUS: group_id={} requested={} eligible={} focus_before={} focus_after={} resolved={}",
            id, requested ? 1 : 0, can_receive_focus() ? 1 : 0,
            focus_before, focus_after, resolved ? resolved->id : 0);

        context.complete(epoc::error_none);
    }"""
    c=c[:recv_start]+recv_new+c[recv_end:]

    exec_sig="    bool window_group::execute_command(service::ipc_context &ctx, ws_cmd &cmd)"
    exec_start,exec_end=inline_span(c,exec_sig)
    exec_body=c[exec_start:exec_end]
    if "case EWsWinOpAutoForeground:" not in exec_body:
        default_pos=exec_body.rfind("        default:")
        if default_pos < 0:
            fail("window_group execute_command default case missing")
        auto_case="""        case EWsWinOpAutoForeground: {
            const bool enabled = (*reinterpret_cast<std::uint32_t *>(cmd.data_ptr) != 0);
            set_auto_foreground(enabled);
            LOG_WARN(SERVICE_WINDOW,
                "SYMBIAN-SYSTEMAPPS1 MENUUI36 AUTO_FOREGROUND: group_id={} enabled={} focus_id={}",
                id, enabled ? 1 : 0, (scr && scr->focus) ? scr->focus->id : 0);
            ctx.complete(epoc::error_none);
            break;
        }

"""
        exec_body=exec_body[:default_pos]+auto_case+exec_body[default_pos:]
        c=c[:exec_start]+exec_body+c[exec_end:]
    wgc.write_text(c,encoding="utf-8")

    ic=io.read_text(encoding="utf-8")
    ship_sig="    void window_key_shipper::start_shipping()"
    ship_start,ship_end=inline_span(ic,ship_sig)
    focus_start=ic.find("        epoc::window_group *focus = serv_->get_focus();",ship_start,ship_end)
    if focus_start < 0:
        fail("key shipper focus declaration missing")
    rotation_anchor="        int ui_rotation = focus->scr->ui_rotation;"
    rotation_pos=ic.find(rotation_anchor,focus_start,ship_end)
    if rotation_pos < 0:
        fail("key shipper rotation anchor missing")
    old=ic[focus_start:rotation_pos+len(rotation_anchor)]
    new="""        epoc::window_group *focus = serv_->get_focus();

        // MENUUI36 invariant: key events must never be delivered to a
        // WindowGroup that explicitly disabled receipt of keyboard focus.
        // Re-resolve from z-order if an old/stale screen::focus pointer violates
        // the WindowGroup contract.
        if (focus && !focus->can_receive_focus()) {
            const std::uint32_t stale_id = focus->id;
            epoc::screen *focus_screen = focus->scr;
            epoc::window_group *resolved = focus_screen
                ? focus_screen->update_focus(serv_, nullptr)
                : nullptr;
            focus = serv_->get_focus();

            LOG_WARN(SERVICE_WINDOW,
                "SYMBIAN-SYSTEMAPPS1 MENUUI36 KEY_FOCUS_REPAIR: stale_id={} resolved={} final={} final_eligible={}",
                stale_id, resolved ? resolved->id : 0, focus ? focus->id : 0,
                (focus && focus->can_receive_focus()) ? 1 : 0);
        }

        if (!focus || !focus->can_receive_focus()) {
            LOG_WARN(SERVICE_WINDOW,
                "SYMBIAN-SYSTEMAPPS1 MENUUI36 KEY_FOCUS_DROP: focus={} eligible={}",
                focus ? focus->id : 0, (focus && focus->can_receive_focus()) ? 1 : 0);
            evts_.clear();
            return;
        }

        LOG_WARN(SERVICE_WINDOW,
            "SYMBIAN-SYSTEMAPPS1 MENUUI36 KEY_FOCUS_TARGET: focus_id={} client_thread={} event_count={}",
            focus->id,
            focus->client && focus->client->get_client()
                ? focus->client->get_client()->unique_id()
                : 0,
            evts_.size());

        int ui_rotation = focus->scr->ui_rotation;
"""
    ic=replace_once(ic,old,new,"key focus invariant")
    io.write_text(ic,encoding="utf-8")

    final_h=wgh.read_text(encoding="utf-8")
    final_c=wgc.read_text(encoding="utf-8")
    final_i=io.read_text(encoding="utf-8")
    gates=(
        (final_h,"bool receives_focus_{ false }"),
        (final_h,"bool auto_foreground_{ true }"),
        (final_h,"return receives_focus_"),
        (final_c,"SYMBIAN-SYSTEMAPPS1 MENUUI36 WG_FOCUS:"),
        (final_c,"case EWsWinOpAutoForeground"),
        (final_c,"SYMBIAN-SYSTEMAPPS1 MENUUI36 AUTO_FOREGROUND:"),
        (final_i,"SYMBIAN-SYSTEMAPPS1 MENUUI36 KEY_FOCUS_REPAIR:"),
        (final_i,"SYMBIAN-SYSTEMAPPS1 MENUUI36 KEY_FOCUS_TARGET:"),
    )
    for body,gate in gates:
        if gate not in body:
            fail(f"gate missing: {gate}")

    print("MENUUI36 WINFOCUS1 applied")
    print("WindowGroup_receive_focus=DEDICATED_STATE")
    print("EWsWinOpAutoForeground_0x26=IMPLEMENTED")
    print("key_shipper_nonfocusable_target=REPAIRED_OR_DROPPED")
    print("hardcoded_process_uid_group_scancode=NONE")
    print("MENUUI35/MENUUI34/MENUUI33/MENUUI32/MENUUI31/MENUUI30/prior=PRESERVED")

if __name__=="__main__":
    main()
