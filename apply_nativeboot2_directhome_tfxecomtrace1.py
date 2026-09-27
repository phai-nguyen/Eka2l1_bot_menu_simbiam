#!/usr/bin/env python3
"""DirectHome TFX ECom response tracing, with no guest IPC changes."""
from pathlib import Path
import sys


MARK = "NATIVEBOOT2-DIRECTHOME-TFXECOMTRACE1"
COPY_MARKER = "[NBOOT2][DIRECTHOME_TFX_ECOM_COPY]"
COMPLETE_MARKER = "[NBOOT2][DIRECTHOME_TFX_ECOM_COMPLETE]"


def fail(message):
    raise SystemExit(f"{MARK}: {message}")


def rep(text, old, new, label):
    count = text.count(old)
    if count != 1:
        fail(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


def rep_between(text, begin, end, old, new, label):
    start = text.find(begin)
    finish = text.find(end, start + 1)
    if start < 0 or finish < 0:
        fail(f"{label}: bounds not found")
    region = text[start:finish]
    count = region.count(old)
    if count != 1:
        fail(f"{label}: expected one bounded anchor, found {count}")
    region = region.replace(old, new, 1)
    return text[:start] + region + text[finish:]


def apply_to_svc(source):
    has_copy = COPY_MARKER in source
    has_complete = COMPLETE_MARKER in source
    if has_copy and has_complete:
        return source, False
    if has_copy or has_complete:
        fail("partial trace already present; refusing a duplicate/partial patch")

    for marker in (
        "[NBOOT2][AKNSKIN_TFX_ECOM]",
        "[NBOOT2][TFX_ECOM_DLL]",
        "[NBOOT2][TFX_SESSION]",
    ):
        if marker not in source:
            fail("missing baseline marker " + marker)

    helpers = r'''    // DirectHome-only ECom trace. The filter ties each IPC message to the
    // native AknSkinSrv client and native ecomserver process.
    static bool directhome_tfx_ecom_trace_message(kernel_system *kern, ipc_msg_ptr msg) {
        if (!kern || !kern->get_config()->native_phone_boot || !msg || !msg->own_thr || !msg->msg_session) {
            return false;
        }

        kernel::process *caller = msg->own_thr->owning_process();
        kernel::process *callee = kern->crr_process();
        if (!caller || !callee) {
            return false;
        }

        auto session_server = msg->msg_session->get_server();
        if (!session_server || session_server->name() != "!ecomserver") {
            return false;
        }

        const auto caller_uids = caller->get_uid_type();
        const auto callee_uids = callee->get_uid_type();
        return static_cast<std::uint32_t>(std::get<2>(caller_uids)) == 0x10207114
            && static_cast<std::uint32_t>(std::get<2>(callee_uids)) == 0x10009D8F;
    }

    static void directhome_tfx_ecom_log_copy(kernel_system *kern, ipc_msg_ptr msg, const std::int32_t slot,
        const ipc_copy_info &copy_info, const std::int32_t result) {
        if (!directhome_tfx_ecom_trace_message(kern, msg)) {
            return;
        }

        const bool server_to_client = (copy_info.flags & IPC_DIR_WRITE) != 0;
        std::uint32_t payload_units = 0;
        if (result >= 0) {
            if (server_to_client) {
                if (copy_info.target_length > 0) {
                    payload_units = static_cast<std::uint32_t>(copy_info.target_length);
                }
            } else {
                payload_units = static_cast<std::uint32_t>(result);
            }
        }

        const std::uint32_t element_bytes = (copy_info.flags & CHUNK_SHIFT_BY_1)
            ? static_cast<std::uint32_t>(sizeof(std::uint16_t)) : 1U;
        std::uint32_t sample_words[8] = {};
        const std::uint32_t sample_units = payload_units < (sizeof(sample_words) / element_bytes)
            ? payload_units : static_cast<std::uint32_t>(sizeof(sample_words) / element_bytes);
        const std::uint32_t sample_bytes = sample_units * element_bytes;

        kernel::process *callee = kern->crr_process();
        std::uint8_t *payload = (copy_info.flags & IPC_HLE_EKA1)
            ? copy_info.target_host_ptr : copy_info.target_ptr.get(callee);
        if (payload && sample_bytes > 0) {
            std::memcpy(sample_words, payload, sample_bytes);
        }

        LOG_WARN(KERNEL,
            "[NBOOT2][DIRECTHOME_TFX_ECOM_COPY] message_id={} function=0x{:X} slot={} slot_type={} descriptor=0x{:08X} direction={} result={} payload_units={} unit_bytes={} sample_bytes={} payload_words=[0x{:08X},0x{:08X},0x{:08X},0x{:08X},0x{:08X},0x{:08X},0x{:08X},0x{:08X}] behavior=OBSERVE_ONLY",
            msg->id, static_cast<std::uint32_t>(msg->function), slot,
            static_cast<int>(msg->args.get_arg_type(slot)),
            static_cast<std::uint32_t>(msg->args.args[slot]),
            server_to_client ? "server_to_client" : "client_to_server", result,
            payload_units, element_bytes, sample_bytes,
            sample_words[0], sample_words[1], sample_words[2], sample_words[3],
            sample_words[4], sample_words[5], sample_words[6], sample_words[7]);
    }

'''
    source = rep(
        source,
        "    BRIDGE_FUNC(void, message_construct, std::int32_t msg_handle, service::message2 *msg_to_construct) {\n",
        helpers + "    BRIDGE_FUNC(void, message_construct, std::int32_t msg_handle, service::message2 *msg_to_construct) {\n",
        "ECom trace helper insertion",
    )

    complete_begin = "    BRIDGE_FUNC(void, message_complete, std::int32_t msg_handle, std::int32_t val) {"
    complete_end = "    BRIDGE_FUNC(void, message_complete_handle,"
    complete_anchor = "        ipc_msg_ptr msg = kern->get_msg(msg_handle);\n\n"
    complete_trace = r'''        ipc_msg_ptr msg = kern->get_msg(msg_handle);
        if (directhome_tfx_ecom_trace_message(kern, msg)) {
            LOG_WARN(KERNEL,
                "[NBOOT2][DIRECTHOME_TFX_ECOM_COMPLETE] message_id={} caller={} thread={} function=0x{:X} status_ptr=0x{:08X} result={} flag=0x{:08X} args=[0x{:08X},0x{:08X},0x{:08X},0x{:08X}] behavior=OBSERVE_ONLY",
                msg->id, msg->own_thr->owning_process()->name(), msg->own_thr->name(),
                static_cast<std::uint32_t>(msg->function), msg->request_sts.ptr_address(), val,
                static_cast<std::uint32_t>(msg->args.flag),
                static_cast<std::uint32_t>(msg->args.args[0]),
                static_cast<std::uint32_t>(msg->args.args[1]),
                static_cast<std::uint32_t>(msg->args.args[2]),
                static_cast<std::uint32_t>(msg->args.args[3]));
        }

'''
    source = rep_between(
        source, complete_begin, complete_end, complete_anchor, complete_trace,
        "ECom completion result trace",
    )

    copy_begin = "    BRIDGE_FUNC(std::int32_t, message_ipc_copy,"
    copy_end = "    BRIDGE_FUNC(std::int32_t, message_ipc_copy_eka1,"
    copy_anchor = """        const std::int32_t result = do_ipc_manipulation(kern, msg->own_thr, param_ptr_host, *info_host, start_offset);
        msg->unref();

        return result;
"""
    copy_trace = """        const std::int32_t result = do_ipc_manipulation(kern, msg->own_thr, param_ptr_host, *info_host, start_offset);
        directhome_tfx_ecom_log_copy(kern, msg, param, *info_host, result);
        msg->unref();

        return result;
"""
    source = rep_between(source, copy_begin, copy_end, copy_anchor, copy_trace, "ECom descriptor copy trace")
    return source, True


def main():
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_directhome_tfxecomtrace1.py <upstream-root>")

    upstream = Path(sys.argv[1]).resolve()
    svc_path = upstream / "src/emu/kernel/src/svc.cpp"
    if not svc_path.is_file():
        fail(f"missing source: {svc_path}")

    source = svc_path.read_text(encoding="utf-8")
    patched, changed = apply_to_svc(source)
    if changed:
        svc_path.write_text(patched, encoding="utf-8")
        print(MARK + ": applied")
    else:
        print(MARK + ": already applied")
    print("scope=AKNSKINSRV_TO_ECOM_OBSERVE_ONLY")
    print("descriptor_sample_max_bytes=32")
    print("ipc_completion_rewrite=NONE")
    print("ipc_descriptor_rewrite=NONE")
    print("fake_tfxserver=NONE")


if __name__ == "__main__":
    main()
