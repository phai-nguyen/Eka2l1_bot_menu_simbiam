#!/usr/bin/env python3
r"""NATIVEBOOT2 B67 STARTERSSCDUMP1.

B66 DEVICE1 proves the text files under private\\100059C9 are first-run /
file-initialisation scripts, while the same RM-356 boot explicitly opens:

  Z:\\resource\\starter_arm.RSC

immediately before the Starter state machine begins. Symbian System Starter
uses a ROM resource (SSC, Static Startup Configuration) to define startup
states and commands. B67 therefore captures the exact RM-356 starter_arm.RSC
bytes instead of inferring the 101 -> 102 boundary from generic startup order.

B67 is diagnostic-only:
- exact target: Z:\\resource\\starter_arm.RSC (case-insensitive)
- separate READ_MODE | BIN_MODE VFS handle
- guest EFsrv subsession/cursor untouched
- no P&S, IPC, process, rendezvous, graphics or teardown behavior changes
- raw bytes are emitted as unambiguous uppercase hex chunks
"""

from pathlib import Path
import sys

MARK="NATIVEBOOT2-B67-STARTERSSCDUMP1"

def fail(msg):
    raise SystemExit(f"{MARK}: {msg}")

def rep1(text, old, new, label):
    n=text.count(old)
    if n!=1:
        fail(f"{label}: expected one anchor, found {n}")
    return text.replace(old,new,1)

def main():
    if len(sys.argv)!=2:
        fail("usage: apply_nativeboot2_b67_startersscdump1.py <upstream-root>")

    up=Path(sys.argv[1]).resolve()
    p=up/"src/emu/services/src/fs/files.cpp"
    proc=up/"src/emu/kernel/src/process.cpp"
    sa=up/"src/emu/services/src/sms/sa/sa.cpp"
    svc=up/"src/emu/kernel/src/svc.cpp"

    for f in (p,proc,sa,svc):
        if not f.is_file():
            fail(f"missing source: {f}")

    text=p.read_text(encoding="utf-8")
    if "[NBOOT2][STARTER_SSC_DUMP]" in text:
        print(MARK+": already applied")
        return

    if "[NBOOT2][STARTER_SCRIPT_DUMP]" not in text:
        fail("B66 Starter script trace missing")
    if "[NBOOT2][STARTER_RENDEZVOUS]" not in proc.read_text(encoding="utf-8"):
        fail("B65 rendezvous trace missing")
    if "[NBOOT2][SA_SELFTEST_RESPONSE]" not in sa.read_text(encoding="utf-8"):
        fail("B64 self-test response missing")
    if "[NBOOT2][STARTER_GLOBAL_STATE]" not in svc.read_text(encoding="utf-8"):
        fail("B62 global-state trace missing")

    helper_anchor="    // NATIVEBOOT2-B66 STARTERSCRIPTDUMP1:\n"
    helper=r'''    // NATIVEBOOT2-B67 STARTERSSCDUMP1:
    // Capture the exact RM-356 Static Startup Configuration resource using a
    // separate read-only VFS handle. Hex-only output is intentionally used so
    // arbitrary binary RSC bytes can be reconstructed without escape ambiguity.
    static void nboot2_b67_dump_starter_ssc(io_system *io,
        const std::u16string &path) {
        if (!io) {
            return;
        }

        const std::u16string lower =
            common::lowercase_ucs2_string(path);
        if (lower != u"z:\\resource\\starter_arm.rsc") {
            return;
        }

        symfile probe = io->open_file(path, READ_MODE | BIN_MODE);
        if (!probe || !probe->valid()) {
            LOG_WARN(SERVICE_EFSRV,
                "[NBOOT2][STARTER_SSC_DUMP] phase=open_fail path={} behavior=OBSERVE_ONLY",
                common::ucs2_to_utf8(path));
            return;
        }

        const std::uint64_t raw_size = probe->size();
        constexpr std::size_t max_capture = 262144;
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

        static constexpr char digits[] = "0123456789ABCDEF";
        constexpr std::size_t chunk_bytes = 512;
        const std::size_t chunks =
            raw.empty() ? 1 :
            ((raw.size() + chunk_bytes - 1) / chunk_bytes);

        LOG_WARN(SERVICE_EFSRV,
            "[NBOOT2][STARTER_SSC_DUMP] phase=begin path={} raw_size={} captured={} truncated={} chunks={} encoding=HEX behavior=OBSERVE_ONLY",
            common::ucs2_to_utf8(path),
            raw_size,
            bytes_read,
            raw_size > max_capture,
            chunks);

        if (raw.empty()) {
            LOG_WARN(SERVICE_EFSRV,
                "[NBOOT2][STARTER_SSC_DUMP] phase=data path={} chunk=1/1 hex=<EMPTY> behavior=OBSERVE_ONLY",
                common::ucs2_to_utf8(path));
        } else {
            for (std::size_t off = 0, index = 0;
                 off < raw.size();
                 off += chunk_bytes, ++index) {
                const std::size_t count =
                    std::min(chunk_bytes, raw.size() - off);
                std::string hex;
                hex.resize(count * 2);
                for (std::size_t i = 0; i < count; ++i) {
                    const unsigned char ch =
                        static_cast<unsigned char>(raw[off + i]);
                    hex[i * 2] = digits[(ch >> 4) & 0xF];
                    hex[i * 2 + 1] = digits[ch & 0xF];
                }

                LOG_WARN(SERVICE_EFSRV,
                    "[NBOOT2][STARTER_SSC_DUMP] phase=data path={} chunk={}/{} offset={} bytes={} hex={} behavior=OBSERVE_ONLY",
                    common::ucs2_to_utf8(path),
                    index + 1,
                    chunks,
                    off,
                    count,
                    hex);
            }
        }

        LOG_WARN(SERVICE_EFSRV,
            "[NBOOT2][STARTER_SSC_DUMP] phase=end path={} behavior=OBSERVE_ONLY",
            common::ucs2_to_utf8(path));
    }

'''
    text=rep1(text,helper_anchor,helper+helper_anchor,"B67 helper insertion")

    hook_anchor='''        nboot2_b66_dump_starter_script(io, *name_res);
        int handle = new_node(ctx->sys->get_io_system(), ctx->msg->own_thr, *name_res,
'''
    hook_new='''        nboot2_b66_dump_starter_script(io, *name_res);
        nboot2_b67_dump_starter_ssc(io, *name_res);
        int handle = new_node(ctx->sys->get_io_system(), ctx->msg->own_thr, *name_res,
'''
    text=rep1(text,hook_anchor,hook_new,"EFsrv open hook")

    for need in (
        "[NBOOT2][STARTER_SSC_DUMP]",
        'u"z:\\\\resource\\\\starter_arm.rsc"',
        "io->open_file(path, READ_MODE | BIN_MODE)",
        "constexpr std::size_t max_capture = 262144",
        "encoding=HEX",
        "nboot2_b67_dump_starter_ssc(io, *name_res);",
        "behavior=OBSERVE_ONLY",
    ):
        if need not in text:
            fail("B67 source gate missing: "+need)

    block=helper
    for forbidden in (
        "WRITE_MODE",
        "write_file(",
        "delete",
        "remove(",
        "ctx->complete(",
        "set_int(",
        "set_property",
    ):
        if forbidden in block:
            fail("B67 diagnostic block changes guest state/files: "+forbidden)

    if (up/"src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    p.write_text(text,encoding="utf-8")

    print(MARK+": applied")
    print("scope=RM356_STARTER_ARM_RSC_READ_ONLY_HEX_DUMP")
    print("target=Z:\\\\resource\\\\starter_arm.RSC")
    print("capture_limit=262144")
    print("encoding=HEX")
    print("guest_file_cursor=UNCHANGED")
    print("behavior_change=NONE")
    print("B61_B62_B64_B65_B66=PRESERVED")

if __name__=="__main__":
    main()
