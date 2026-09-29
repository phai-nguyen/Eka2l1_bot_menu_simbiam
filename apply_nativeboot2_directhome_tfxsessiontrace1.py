#!/usr/bin/env python3
"""DirectHome-only companion for the unchanged B43 TfxServer session path."""
from pathlib import Path
import sys


MARK = "NATIVEBOOT2-DIRECTHOME-TFXSESSIONTRACE1"
MARKER = "[NBOOT2][DIRECTHOME_TFX_SESSION]"
SVC = "src/emu/kernel/src/svc.cpp"
BEGIN = "    BRIDGE_FUNC(std::int32_t, session_create,"
END = "    BRIDGE_FUNC(std::int32_t, session_create_from_handle,"


def fail(why):
    raise SystemExit(f"{MARK}: {why}")


def once(text, anchor, label):
    count = text.count(anchor)
    if count != 1:
        fail(f"{label}: expected one anchor, found {count}")


def apply_to_svc(source: str) -> str:
    once(source, BEGIN, "session_create entry")
    once(source, END, "session_create exit")
    start = source.index(BEGIN)
    end = source.index(END)
    if end < start:
        fail("invalid session_create bounds")
    session = source[start:end]
    for anchor in ("[NBOOT2][TFX_SESSION]", "b43_tfx_miss.valid = true;",
                   "return epoc::error_not_found;",
                   "return do_create_session_from_server(kern, server, msg_slot, sec, mode);"):
        if anchor == "[NBOOT2][TFX_SESSION]":
            if session.count(anchor) != 3:
                fail("expected B43 request/missing/found logs")
        else:
            once(session, anchor, "B43 " + anchor)
    if MARKER in session:
        if session.count(MARKER) != 2 or any(session.count(f'directhome_log_tfx_session("{phase}"') != 1
                                                  for phase in ("request", "missing", "found")):
            fail("partial or duplicate companion trace")
        return source
    if MARKER in source:
        fail("companion marker outside session_create")

    request = "        auto *b43_cpu = kern->get_cpu();\n"
    miss = "            return epoc::error_not_found;\n"
    found = "        return do_create_session_from_server(kern, server, msg_slot, sec, mode);\n"
    for label, anchor in (("request", request), ("missing", miss), ("found", found)):
        once(session, anchor, label)
    addition = '''        auto *b43_cpu = kern->get_cpu();
        const auto *directhome_tfx_cfg = kern->get_config();
        const bool directhome_tfx = directhome_tfx_cfg && directhome_tfx_cfg->native_phone_boot
            && directhome_tfx_cfg->compat_menu_probe_mode && directhome_tfx_cfg->compat_target_kind == 2
            && server_name == "TfxServer";
        auto directhome_log_tfx_session = [&](const char *phase, bool has_result, std::int32_t result) {
            if (!directhome_tfx) return;
            const std::string result_text = has_result ? std::to_string(result) : std::string("<pending>");
            if (!pr || !b43_thr || b43_thr->owning_process() != pr) {
                LOG_WARN(KERNEL,
                    "[NBOOT2][DIRECTHOME_TFX_SESSION] phase={} context=missing server={} result={} behavior=OBSERVE_ONLY",
                    phase, server_name, result_text);
                return;
            }
            const std::uint32_t uid3 = static_cast<std::uint32_t>(std::get<2>(pr->get_uid_type()));
            LOG_WARN(KERNEL,
                "[NBOOT2][DIRECTHOME_TFX_SESSION] phase={} context=present process={} uid3=0x{:08X} pid={} thread={} tid={} server={} result={} behavior=OBSERVE_ONLY",
                phase, pr->name(), uid3, pr->unique_id(), b43_thr->name(), b43_thr->unique_id(),
                server_name, result_text);
        };
        directhome_log_tfx_session("request", false, 0);
'''
    session = session.replace(request, addition, 1)
    session = session.replace(miss,
        '            directhome_log_tfx_session("missing", true, epoc::error_not_found);\n' + miss, 1)
    session = session.replace(found,
        '        directhome_log_tfx_session("found", false, 0);\n' + found, 1)
    return source[:start] + session + source[end:]


def apply(root: Path) -> bool:
    path = root / SVC
    if not path.is_file():
        fail("missing source " + SVC)
    original = path.read_text(encoding="utf-8")
    result = apply_to_svc(original)
    if result != original:
        path.write_text(result, encoding="utf-8")
    return result != original


def main():
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_directhome_tfxsessiontrace1.py <upstream-root>")
    print(f"{MARK}: {'applied' if apply(Path(sys.argv[1]).resolve()) else 'already applied'}")
    print("scope=OBSERVE_ONLY; missing_result=KErrNotFound_PRESERVED")


if __name__ == "__main__":
    main()
