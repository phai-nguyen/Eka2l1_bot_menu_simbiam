#!/usr/bin/env python3
"""Apply read-only, CompatBoot-scoped B94 teardown diagnostics."""
from pathlib import Path
import sys

MARK = "NATIVEBOOT2-B94-TEARDOWNPROBE1"
HEADER = '''#pragma once
#include <cstdint>
namespace eka2l1::kernel {
    struct notify_status_resolution_context {
        const void *process = nullptr;
        std::uintptr_t guest_address = 0;
    };
    inline thread_local notify_status_resolution_context b94_notify_status_context{};
    class scoped_notify_status_resolution {
        notify_status_resolution_context previous_;
    public:
        scoped_notify_status_resolution(const void *process, std::uintptr_t guest_address)
            : previous_(b94_notify_status_context) {
            b94_notify_status_context = { process, guest_address };
        }
        ~scoped_notify_status_resolution() { b94_notify_status_context = previous_; }
    };
    inline bool notify_status_resolution_matches(const void *process, std::uintptr_t guest_address) {
        return b94_notify_status_context.process == process
            && b94_notify_status_context.guest_address == guest_address;
    }
}
'''

def fail(message):
    raise SystemExit(f"{MARK}: {message}")

def replace_once(source, old, new, label):
    count = source.count(old)
    if count != 1:
        fail(f"{label}: expected one anchor, found {count}")
    return source.replace(old, new, 1)

def ensure_include(source, include, label):
    if include in source:
        return source
    anchor = "#include <kernel/kernel.h>\n"
    if source.count(anchor) != 1:
        include_lines = [line for line in source.splitlines(keepends=True) if line.startswith("#include ")]
        if len(include_lines) != 1:
            fail(f"{label}: missing unique include insertion point")
        anchor = include_lines[0]
    return source.replace(anchor, anchor + include + "\n", 1)

def patch_notify_complete(source):
    marker = "[COMPATBOOT][NOTIFY_STATUS]"
    if marker in source:
        if source.count(marker) != 2:
            fail("partial notify trace detected")
        return source
    source = ensure_include(source, "#include <config/config.h>", "notify_info")
    source = ensure_include(source, "#include <kernel/b94_teardown_probe.h>", "notify_info")
    old = "            epoc::request_status *sts_real = sts.get(requester->owning_process());\n            if (sts_real)\n"
    new = '''            kernel::process *nboot2_b94_requester_process = requester->owning_process();
            const bool nboot2_b94_notify_trace = kern->get_config()->compat_menu_probe_mode
                && (err_code == epoc::error_cancel);
            const std::uint32_t nboot2_b94_status_address = static_cast<std::uint32_t>(sts.ptr_address());
            const std::uint32_t nboot2_b94_requester_uid3 = nboot2_b94_requester_process
                ? static_cast<std::uint32_t>(std::get<2>(nboot2_b94_requester_process->get_uid_type())) : 0;
            if (nboot2_b94_notify_trace) {
                LOG_INFO(KERNEL,
                    "[COMPATBOOT][NOTIFY_STATUS] phase=before_resolve requester_ptr={} requester={} requester_process_ptr={} requester_process={} requester_uid3=0x{:08X} request_status=0x{:08X} notify_status_scope=begin",
                    static_cast<const void *>(requester), requester->name(), static_cast<const void *>(nboot2_b94_requester_process),
                    nboot2_b94_requester_process ? nboot2_b94_requester_process->name() : std::string("<none>"),
                    nboot2_b94_requester_uid3, nboot2_b94_status_address);
            }
            kernel::scoped_notify_status_resolution nboot2_b94_status_scope(
                nboot2_b94_notify_trace ? static_cast<const void *>(nboot2_b94_requester_process) : nullptr,
                nboot2_b94_notify_trace ? nboot2_b94_status_address : 0);
            epoc::request_status *sts_real = sts.get(nboot2_b94_requester_process);
            if (nboot2_b94_notify_trace) {
                LOG_INFO(KERNEL,
                    "[COMPATBOOT][NOTIFY_STATUS] phase=after_resolve requester_ptr={} requester_process_ptr={} requester_process={} requester_uid3=0x{:08X} request_status=0x{:08X} resolved_host_ptr={} notify_status_scope=result",
                    static_cast<const void *>(requester), static_cast<const void *>(nboot2_b94_requester_process),
                    nboot2_b94_requester_process ? nboot2_b94_requester_process->name() : std::string("<none>"),
                    nboot2_b94_requester_uid3, nboot2_b94_status_address, static_cast<void *>(sts_real));
            }
            if (sts_real)
'''
    return replace_once(source, old, new, "notify status resolution")

def patch_property_cancel(source):
    marker = "[COMPATBOOT][PROP_CANCEL]"
    if marker in source:
        if source.count(marker) != 1:
            fail("partial property cancel trace detected")
        return source
    source = ensure_include(source, "#include <config/config.h>", "property::cancel")
    old = "        if (kern->is_thread_alive((*subscription_iterator)->requester)) {\n            (*subscription_iterator)->complete(epoc::error_cancel);\n        }\n"
    new = '''        auto *nboot2_b94_requester = (*subscription_iterator)->requester;
        const bool nboot2_b94_requester_alive = kern->is_thread_alive(nboot2_b94_requester);
        if (kern->get_config()->compat_menu_probe_mode) {
            LOG_INFO(KERNEL,
                "[COMPATBOOT][PROP_CANCEL] phase=before_complete property_ref_ptr={} property_ptr={} requester_ptr={} requester={} requester_alive={} request_status=0x{:08X}",
                static_cast<const void *>(&info), static_cast<const void *>(this),
                static_cast<const void *>(nboot2_b94_requester),
                nboot2_b94_requester ? nboot2_b94_requester->name() : std::string("<none>"),
                nboot2_b94_requester_alive ? 1 : 0, info.sts.ptr_address());
        }
        if (nboot2_b94_requester_alive) {
            (*subscription_iterator)->complete(epoc::error_cancel);
        }
'''
    return replace_once(source, old, new, "property cancel liveness")

def patch_process_kill(source):
    marker = "[COMPATBOOT][PROCESS_KILL]"
    if marker in source:
        if source.count(marker) != 1:
            fail("partial process kill trace detected")
        return source
    source = ensure_include(source, "#include <config/config.h>", "process::kill")
    old = "    void process::kill(const entity_exit_type ext, const std::u16string &category, const std::int32_t reason) {\n        if (exit_type != entity_exit_type::pending) {\n"
    new = '''    void process::kill(const entity_exit_type ext, const std::u16string &category, const std::int32_t reason) {
        if (get_kernel_object_owner()->get_config()->compat_menu_probe_mode) {
            const auto nboot2_b94_uids = get_uid_type();
            LOG_INFO(KERNEL,
                "[COMPATBOOT][PROCESS_KILL] phase=begin process_ptr={} process={} uid3=0x{:08X} exit_type={} reason={}",
                static_cast<const void *>(this), name(),
                static_cast<std::uint32_t>(std::get<2>(nboot2_b94_uids)), static_cast<int>(ext), reason);
        }
        if (exit_type != entity_exit_type::pending) {
'''
    return replace_once(source, old, new, "process kill entry")

def patch_process_address_space(source):
    marker = "[COMPATBOOT][NOTIFY_STATUS_MAP]"
    if marker in source:
        if source.count(marker) != 2:
            fail("partial address-space trace detected")
        return source
    source = ensure_include(source, "#include <kernel/b94_teardown_probe.h>", "process address-space lookup")
    old = "        return mem->get_control()->get_host_pointer(mm_impl_->address_space_id(), addr);\n"
    new = '''        const bool nboot2_b94_trace_status_map = notify_status_resolution_matches(this, addr);
        if (nboot2_b94_trace_status_map) {
            LOG_INFO(KERNEL,
                "[COMPATBOOT][NOTIFY_STATUS_MAP] phase=begin process_ptr={} guest_status=0x{:08X} address_space={}",
                static_cast<const void *>(this), static_cast<std::uint32_t>(addr), mm_impl_->address_space_id());
        }
        void *nboot2_b94_host_pointer = mem->get_control()->get_host_pointer(mm_impl_->address_space_id(), addr);
        if (nboot2_b94_trace_status_map) {
            LOG_INFO(KERNEL,
                "[COMPATBOOT][NOTIFY_STATUS_MAP] phase=result process_ptr={} guest_status=0x{:08X} address_space={} host_pointer={}",
                static_cast<const void *>(this), static_cast<std::uint32_t>(addr),
                mm_impl_->address_space_id(), nboot2_b94_host_pointer);
        }
        return nboot2_b94_host_pointer;
'''
    return replace_once(source, old, new, "address-space host pointer lookup")

def main():
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b94_teardownprobe1.py <upstream-root>")
    upstream = Path(sys.argv[1]).resolve()
    thread_path = upstream / "src/emu/kernel/src/thread.cpp"
    property_path = upstream / "src/emu/kernel/src/property.cpp"
    process_path = upstream / "src/emu/kernel/src/process.cpp"
    for path in (thread_path, property_path, process_path):
        if not path.is_file():
            fail(f"missing B28 source: {path}")
    thread = patch_notify_complete(thread_path.read_text(encoding="utf-8"))
    prop = patch_property_cancel(property_path.read_text(encoding="utf-8"))
    process = process_path.read_text(encoding="utf-8")
    process = patch_process_kill(process)
    process = patch_process_address_space(process)
    (upstream / "src/emu/kernel/include/kernel/b94_teardown_probe.h").write_text(HEADER, encoding="utf-8")
    thread_path.write_text(thread, encoding="utf-8")
    property_path.write_text(prop, encoding="utf-8")
    process_path.write_text(process, encoding="utf-8")
    print(f"{MARK}: applied; diagnostics=read_only,CompatBoot_scoped")

if __name__ == "__main__":
    main()
