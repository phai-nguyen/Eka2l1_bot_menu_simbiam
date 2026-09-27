#!/usr/bin/env python3
"""Contract for the DirectHome AknSkinSrv -> ECom response trace.

The probe must report copied ECom descriptors and the real message completion
code without changing IPC arguments, completion values, or missing-server
semantics.
"""
from pathlib import Path
import re
import sys


MARK = "NATIVEBOOT2-DIRECTHOME-TFXECOMTRACE1-TEST"


def fail(message):
    raise SystemExit(f"{MARK}: FAIL: {message}")


def need(text, needle, where):
    if needle not in text:
        fail(f"missing in {where}: {needle}")


def function_block(source, start, end, label):
    begin = source.find(start)
    finish = source.find(end, begin + 1)
    if begin < 0 or finish < 0:
        fail(f"cannot isolate {label}")
    return source[begin:finish]


def main():
    if len(sys.argv) != 2:
        fail("usage: test_nativeboot2_directhome_tfxecomtrace1.py <upstream-root>")

    svc_path = Path(sys.argv[1]).resolve() / "src/emu/kernel/src/svc.cpp"
    if not svc_path.is_file():
        fail(f"missing source: {svc_path}")
    svc = svc_path.read_text(encoding="utf-8")

    for marker in (
        "[NBOOT2][AKNSKIN_TFX_ECOM]",
        "[NBOOT2][TFX_ECOM_DLL]",
        "[NBOOT2][TFX_SESSION]",
        "[NBOOT2][DIRECTHOME_TFX_ECOM_COPY]",
        "[NBOOT2][DIRECTHOME_TFX_ECOM_COMPLETE]",
    ):
        need(svc, marker, "DirectHome ECom trace")

    predicate = function_block(
        svc,
        "static bool directhome_tfx_ecom_trace_message(",
        "static void directhome_tfx_ecom_log_copy(",
        "AknSkinSrv/ECom filter",
    )
    for needle in (
        "native_phone_boot",
        "0x10207114",
        "0x10009D8F",
        '"!ecomserver"',
    ):
        need(predicate, needle, "AknSkinSrv/ECom filter")

    completion = function_block(
        svc,
        "BRIDGE_FUNC(void, message_complete,",
        "BRIDGE_FUNC(void, message_complete_handle,",
        "message_complete",
    )
    complete_marker = completion.find("[NBOOT2][DIRECTHOME_TFX_ECOM_COMPLETE]")
    callback = completion.find("kern->call_ipc_complete_callbacks(msg, val);")
    if complete_marker < 0 or callback < complete_marker:
        fail("ECom completion trace must precede the unchanged completion callback")
    need(completion, "message_id={}", "ECom completion correlation")
    need(completion, "result={}", "ECom completion result")
    if re.search(r"\bval\s*=(?!=)", completion[max(0, complete_marker - 500):callback]):
        fail("ECom completion trace appears to rewrite the server result")
    need(completion, "status->set(val, kern->is_eka1())", "real IPC completion")
    need(completion, "msg->unref();", "original message release")

    copy = function_block(
        svc,
        "BRIDGE_FUNC(std::int32_t, message_ipc_copy,",
        "BRIDGE_FUNC(std::int32_t, message_ipc_copy_eka1,",
        "message_ipc_copy",
    )
    copy_call = copy.find("do_ipc_manipulation(kern, msg->own_thr, param_ptr_host, *info_host, start_offset)")
    copy_marker = copy.find("directhome_tfx_ecom_log_copy(kern, msg, param, *info_host, result)")
    release = copy.find("msg->unref();", copy_marker)
    returned = copy.find("return result;", release)
    if min(copy_call, copy_marker, release, returned) < 0 or not (copy_call < copy_marker < release < returned):
        fail("descriptor trace must observe completed copies and preserve the original return")
    copy_logger = function_block(
        svc,
        "static void directhome_tfx_ecom_log_copy(",
        "    BRIDGE_FUNC(void, message_construct,",
        "ECom descriptor trace helper",
    )
    need(copy_logger, "[NBOOT2][DIRECTHOME_TFX_ECOM_COPY]", "ECom descriptor trace")
    need(copy_logger, "payload_words", "bounded descriptor payload")
    need(copy_logger, "IPC_DIR_WRITE", "descriptor direction")
    need(copy_logger, "msg->id", "ECom request correlation")
    if re.search(r"msg->args\.args\s*\[\s*param\s*\]\s*=", copy):
        fail("descriptor trace appears to rewrite an IPC argument")

    session_create = function_block(
        svc,
        "BRIDGE_FUNC(std::int32_t, session_create,",
        "BRIDGE_FUNC(std::int32_t, session_create_from_handle,",
        "session_create",
    )
    need(session_create, "return epoc::error_not_found;", "unchanged TfxServer miss")
    if "create_and_add<service::server>" in session_create:
        fail("probe fabricates a server in session_create")

    print(f"{MARK}: PASS")
    print("scope=OBSERVE_ONLY")
    print("ipc_completion_rewrite=NONE")
    print("ipc_descriptor_rewrite=NONE")
    print("fake_tfxserver=NONE")


if __name__ == "__main__":
    main()
