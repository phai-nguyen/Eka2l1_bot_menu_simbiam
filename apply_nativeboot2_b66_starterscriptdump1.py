#!/usr/bin/env python3
r"""NATIVEBOOT2 B66 STARTERSCRIPTDUMP1.

B65 DEVICE1 proves the only SYSSTART rendezvous armed after state 101 is
profilesettingsmonitor and it completes with reason 0. Therefore the
StartingCriticalApps=101 stall is not explained by that process wait.

The installed RM-356 firmware contains the real classic S60 Starter files:
  Z:\private\100059C9\ScriptInit.txt
  Z:\private\100059C9\script0.txt
  Z:\private\100059C9\script1.txt
and runtime also opens:
  C:\private\100059C9\plg_script*.txt

B66 is diagnostic-only. When EFsrv opens one of those exact Starter paths,
B66 opens a separate read-only VFS handle and logs the raw contents in an
escaped, chunked form. The guest's actual file handle/cursor is untouched.

No startup state, file contents, open mode, process or IPC semantics change.
"""

from pathlib import Path
import sys

MARK="NATIVEBOOT2-B66-STARTERSCRIPTDUMP1"

def fail(msg):
    raise SystemExit(f"{MARK}: {msg}")

def rep1(text, old, new, label):
    n=text.count(old)
    if n!=1:
        fail(f"{label}: expected one anchor, found {n}")
    return text.replace(old,new,1)

def main():
    if len(sys.argv)!=2:
        fail("usage: apply_nativeboot2_b66_starterscriptdump1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    p=up/"src/emu/services/src/fs/files.cpp"
    proc=up/"src/emu/kernel/src/process.cpp"
    sa=up/"src/emu/services/src/sms/sa/sa.cpp"
    svc=up/"src/emu/kernel/src/svc.cpp"

    for f in (p,proc,sa,svc):
        if not f.is_file():
            fail(f"missing source: {f}")

    text=p.read_text(encoding="utf-8")
    if "[NBOOT2][STARTER_SCRIPT_DUMP]" in text:
        print(MARK+": already applied")
        return

    if "[NBOOT2][STARTER_RENDEZVOUS]" not in proc.read_text(encoding="utf-8"):
        fail("B65 rendezvous trace missing")
    if "[NBOOT2][SA_SELFTEST_RESPONSE]" not in sa.read_text(encoding="utf-8"):
        fail("B64 self-test response missing")
    if "[NBOOT2][STARTER_GLOBAL_STATE]" not in svc.read_text(encoding="utf-8"):
        fail("B62 global-state trace missing")

    helper_anchor='''namespace eka2l1 {
'''
    helper=r'''    // NATIVEBOOT2-B66 STARTERSCRIPTDUMP1:
    // Read the real RM-356 Starter scripts through a separate VFS handle so
    // diagnostics cannot perturb the guest's own EFsrv subsession or cursor.
    static void nboot2_b66_dump_starter_script(io_system *io,
        const std::u16string &path) {
        if (!io) {
            return;
        }

        const std::u16string lower =
            common::lowercase_ucs2_string(path);

        const std::u16string z_prefix =
            u"z:\\private\\100059c9\\";
        const std::u16string c_prefix =
            u"c:\\private\\100059c9\\";

        bool wanted = false;
        if (lower == z_prefix + u"scriptinit.txt" ||
            lower == z_prefix + u"script0.txt" ||
            lower == z_prefix + u"script1.txt") {
            wanted = true;
        } else if (lower.rfind(c_prefix + u"plg_script", 0) == 0 &&
                   lower.size() >= 4 &&
                   lower.substr(lower.size() - 4) == u".txt") {
            wanted = true;
        }

        if (!wanted) {
            return;
        }

        symfile probe = io->open_file(path, READ_MODE | BIN_MODE);
        if (!probe || !probe->valid()) {
            LOG_WARN(SERVICE_EFSRV,
                "[NBOOT2][STARTER_SCRIPT_DUMP] phase=open_fail path={} behavior=OBSERVE_ONLY",
                common::ucs2_to_utf8(path));
            return;
        }

        const std::uint64_t raw_size = probe->size();
        constexpr std::size_t max_capture = 65536;
        const std::size_t capture_size =
            static_cast<std::size_t>(
                (raw_size > max_capture) ? max_capture : raw_size);

        std::string raw;
        raw.resize(capture_size);

        std::size_t bytes_read = 0;
        if (capture_size > 0) {
            bytes_read = probe->read_file(
                raw.data(), 1, static_cast<std::uint32_t>(capture_size));
            if (bytes_read > capture_size) {
                bytes_read = capture_size;
            }
            raw.resize(bytes_read);
        }

        std::string escaped;
        escaped.reserve(raw.size() * 2);
        static constexpr char hex[] = "0123456789ABCDEF";

        for (const unsigned char ch : raw) {
            if (ch == '\r') {
                escaped += "\\r";
            } else if (ch == '\n') {
                escaped += "\\n";
            } else if (ch == '\t') {
                escaped += "\\t";
            } else if (ch >= 0x20 && ch <= 0x7E) {
                escaped.push_back(static_cast<char>(ch));
            } else {
                escaped += "\\x";
                escaped.push_back(hex[(ch >> 4) & 0xF]);
                escaped.push_back(hex[ch & 0xF]);
            }
        }

        constexpr std::size_t chunk_chars = 700;
        const std::size_t chunks =
            escaped.empty() ? 1 :
            ((escaped.size() + chunk_chars - 1) / chunk_chars);

        LOG_WARN(SERVICE_EFSRV,
            "[NBOOT2][STARTER_SCRIPT_DUMP] phase=begin path={} raw_size={} captured={} truncated={} chunks={} behavior=OBSERVE_ONLY",
            common::ucs2_to_utf8(path),
            raw_size,
            bytes_read,
            raw_size > max_capture,
            chunks);

        if (escaped.empty()) {
            LOG_WARN(SERVICE_EFSRV,
                "[NBOOT2][STARTER_SCRIPT_DUMP] phase=data path={} chunk=1/1 data=<EMPTY> behavior=OBSERVE_ONLY",
                common::ucs2_to_utf8(path));
        } else {
            for (std::size_t off = 0, index = 0;
                 off < escaped.size();
                 off += chunk_chars, ++index) {
                LOG_WARN(SERVICE_EFSRV,
                    "[NBOOT2][STARTER_SCRIPT_DUMP] phase=data path={} chunk={}/{} data={} behavior=OBSERVE_ONLY",
                    common::ucs2_to_utf8(path),
                    index + 1,
                    chunks,
                    escaped.substr(off, chunk_chars));
            }
        }

        LOG_WARN(SERVICE_EFSRV,
            "[NBOOT2][STARTER_SCRIPT_DUMP] phase=end path={} behavior=OBSERVE_ONLY",
            common::ucs2_to_utf8(path));
    }

'''
    text=rep1(text,helper_anchor,helper_anchor+helper,"helper insertion")

    open_anchor='''        LOG_INFO(SERVICE_EFSRV, "Opening file: {}, raw mode {}", name_utf8, open_mode_res.value());
        int handle = new_node(ctx->sys->get_io_system(), ctx->msg->own_thr, *name_res,
'''
    open_new='''        LOG_INFO(SERVICE_EFSRV, "Opening file: {}, raw mode {}", name_utf8, open_mode_res.value());
        nboot2_b66_dump_starter_script(io, *name_res);
        int handle = new_node(ctx->sys->get_io_system(), ctx->msg->own_thr, *name_res,
'''
    text=rep1(text,open_anchor,open_new,"open hook")

    for need in (
        "[NBOOT2][STARTER_SCRIPT_DUMP]",
        'u"z:\\\\private\\\\100059c9\\\\"',
        'u"scriptinit.txt"',
        'u"script0.txt"',
        'u"script1.txt"',
        'u"plg_script"',
        "io->open_file(path, READ_MODE | BIN_MODE)",
        "raw_size > max_capture",
        "behavior=OBSERVE_ONLY",
    ):
        if need not in text:
            fail("B66 source gate missing: "+need)

    # B66 must never write/resize/remove or reuse the guest's actual fs_node.
    # Validate the helper string itself. Do not depend on surrounding
    # files.cpp anchors because earlier milestones may legitimately rewrite
    # nearby comments/functions.
    block=helper
    for forbidden in (
        "WRITE_MODE",
        "write_file(",
        "resize(",
        "delete",
        "remove(",
        "ctx->complete(",
        "set_int(",
    ):
        if forbidden in block:
            fail("B66 diagnostic block changes state/files: "+forbidden)

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    p.write_text(text,encoding="utf-8")

    print(MARK+": applied")
    print("scope=RM356_STARTER_SCRIPT_READ_ONLY_DUMP")
    print("targets=Z_SCRIPTINIT_SCRIPT0_SCRIPT1_PLUS_C_PLG_SCRIPT_TXT")
    print("capture_limit=65536")
    print("guest_file_cursor=UNCHANGED")
    print("behavior_change=NONE")
    print("B62_B64_B65=PRESERVED")

if __name__=="__main__":
    main()
