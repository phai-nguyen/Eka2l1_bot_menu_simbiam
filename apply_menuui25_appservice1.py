#!/usr/bin/env python3
"""MENUUI25 APPSERVICE1: implement AppArc service discovery used by Messaging New message.

Device evidence on MENUUI24:
- Contacts Exit PASS.
- Messaging Exit PASS.
- Messaging New message receives touch, loads UniMtms.dll/UniMtms.r01,
  then blocks on synchronous !AppListServer opcode 46 (0x2E).
Symbian maps:
- 46 = EAppListServInitServerAppList / RApaLsSession::GetServerApps(serviceUid)
- 48 = EAppListServGetServiceImplementations
Messaging CMuiuMsgEditorService::DiscoverL uses service UID 0x101F8820 to find
UniEditor (app UID 0x102072D8) and inspect its service opaque data.

This patch:
1) parses APP_REGISTRATION_INFO datatype/file-ownership/service_list fields;
2) resolves SERVICE_INFO opaque resource data;
3) implements server-app filtering for opcode 46 + GetNextApp;
4) implements opcode 48 with Symbian stream-compatible TApaAppServiceInfo array
   serialization and the two-call buffer-size handshake.

Preserves MENUUI24 AKN-ZORDER1, MENUUI23 APPTYPE1, MENUUI22 SCHEDRUN1,
MANIC3 and NOJAVA. No scheduler/process-kill/canvas shortcuts.
"""
from __future__ import annotations

import sys
from pathlib import Path

MARK = "MENUUI25 APPSERVICE1"


def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: {msg}")


def replace_once(text: str, old: str, new: str, name: str) -> str:
    count = text.count(old)
    if count != 1:
        fail(f"{name}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_menuui25_appservice1.py <upstream-root>")

    up = Path(sys.argv[1]).resolve()
    common_h = up / "src/emu/services/include/services/applist/common.h"
    applist_h = up / "src/emu/services/include/services/applist/applist.h"
    reg_cpp = up / "src/emu/services/src/applist/registeration.cpp"
    applist_cpp = up / "src/emu/services/src/applist/applist.cpp"
    op_h = up / "src/emu/services/include/services/applist/op.h"
    oom_cpp = up / "src/emu/services/src/ui/cap/oom_app.cpp"
    kernel = up / "src/emu/kernel/src/kernel.cpp"
    svc = up / "src/emu/kernel/src/svc.cpp"
    root = up / "src/emu/ios/app/RootViewController.mm"

    for p in (common_h, applist_h, reg_cpp, applist_cpp, op_h, oom_cpp, kernel, svc, root):
        if not p.is_file():
            fail(f"required baseline file missing: {p}")

    if (up / "src/emu/j2me").exists():
        fail("NOJAVA invariant violated: src/emu/j2me exists")

    # Baseline gates.
    op_text = op_h.read_text(encoding="utf-8")
    if "applist_request_init_server_applist" not in op_text:
        fail("opcode 46 enum name missing")
    if "applist_request_get_service_implementations" not in op_text:
        fail("opcode 48 enum name missing")
    if "SYMBIAN-SYSTEMAPPS1 MENUUI24 AKN_ZORDER:" not in oom_cpp.read_text(encoding="utf-8"):
        fail("MENUUI24 AKN-ZORDER1 baseline missing")
    if "SYMBIAN-SYSTEMAPPS1 MENUUI23 APPTYPE:" not in applist_cpp.read_text(encoding="utf-8"):
        fail("MENUUI23 APPTYPE1 baseline missing")
    if "SYMBIAN-SYSTEMAPPS1 MENUUI22 SCHEDRUN_SVC:" not in kernel.read_text(encoding="utf-8"):
        fail("MENUUI22 SCHEDRUN1 baseline missing")
    if "SYMBIAN-SYSTEMAPPS1 MENUUI22 SYNC_COMPLETE:" not in svc.read_text(encoding="utf-8"):
        fail("MENUUI22 sync diagnostics missing")
    if "MANIC_MODALFIX1" not in root.read_text(encoding="utf-8"):
        fail("MANIC3 baseline missing")

    service_marker = "SYMBIAN-SYSTEMAPPS1 MENUUI25 SERVICE_IMPL:"
    server_marker = "SYMBIAN-SYSTEMAPPS1 MENUUI25 SERVER_APPLIST:"
    reg_marker = "SYMBIAN-SYSTEMAPPS1 MENUUI25 SERVICE_REG:"

    if service_marker in applist_cpp.read_text(encoding="utf-8"):
        print("MENUUI25 APPSERVICE1 already present")
        return

    # ------------------------------------------------------------------
    # common.h: service registration model
    # ------------------------------------------------------------------
    text = common_h.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "#include <cstdint>\n#include <utils/des.h>\n",
        "#include <cstdint>\n#include <vector>\n#include <utils/des.h>\n",
        "common vector include",
    )
    old = """    struct data_type {
        std::int32_t priority_;
        std::string type_;
    };

    struct view_data {
"""
    new = """    struct data_type {
        std::int32_t priority_;
        std::string type_;
    };

    // AppArc SERVICE_INFO from APP_REGISTRATION_INFO.
    struct apa_app_service_info {
        std::uint32_t uid_{ 0 };
        std::vector<data_type> data_types_;
        std::uint32_t opaque_resource_id_{ 0 };
        std::vector<std::uint8_t> opaque_data_;
    };

    struct view_data {
"""
    text = replace_once(text, old, new, "service model")
    common_h.write_text(text, encoding="utf-8")

    # ------------------------------------------------------------------
    # applist.h: registry services + per-session service enumeration state
    # ------------------------------------------------------------------
    text = applist_h.read_text(encoding="utf-8")
    old = """        std::vector<data_type> data_types;
        std::vector<view_data> view_datas;
        file_ownership_list ownership_list;

        drive_number land_drive;
"""
    new = """        std::vector<data_type> data_types;
        std::vector<apa_app_service_info> services;
        std::vector<view_data> view_datas;
        file_ownership_list ownership_list;

        drive_number land_drive;
"""
    text = replace_once(text, old, new, "registry services field")

    old = """        enum app_filter_method {
            APP_FILTER_BY_EMBED,
            APP_FILTER_BY_FLAGS,
            APP_FILTER_NONE
        };

        std::size_t current_index_;
        std::uint32_t flags_mask_;
        std::uint32_t flags_match_value_;
        std::uint32_t requested_screen_mode_;

        app_filter_method filter_method_;

    public:
"""
    new = """        enum app_filter_method {
            APP_FILTER_BY_EMBED,
            APP_FILTER_BY_FLAGS,
            APP_FILTER_BY_SERVICE,
            APP_FILTER_NONE
        };

        std::size_t current_index_;
        std::uint32_t flags_mask_;
        std::uint32_t flags_match_value_;
        std::uint32_t requested_screen_mode_;

        std::int32_t requested_service_screen_mode_;
        std::uint32_t requested_service_uid_;
        std::string service_buffer_;

        app_filter_method filter_method_;

    public:
"""
    text = replace_once(text, old, new, "session service state")

    old = """        void get_filtered_apps_by_flags(service::ipc_context &ctx);
        void get_next_app(service::ipc_context &ctx);
    };
"""
    new = """        void get_filtered_apps_by_flags(service::ipc_context &ctx);
        void init_server_app_list(service::ipc_context &ctx);
        void get_service_implementations(service::ipc_context &ctx);
        void get_next_app(service::ipc_context &ctx);
    };
"""
    text = replace_once(text, old, new, "session method declarations")
    applist_h.write_text(text, encoding="utf-8")

    # ------------------------------------------------------------------
    # registeration.cpp: parse modern optional registration fields.
    # ------------------------------------------------------------------
    text = reg_cpp.read_text(encoding="utf-8")
    helper_anchor = """    static bool read_non_localisable_info(common::ro_stream *stream, apa_app_registry &reg, const drive_number land_drive) {
"""
    helpers = """    static bool read_str8(common::ro_stream *stream, std::string &dat) {
        std::uint8_t len = 0;
        if (stream->read(&len, sizeof(len)) != sizeof(len)) {
            return false;
        }

        dat.resize(len);
        if (len && stream->read(dat.data(), len) != len) {
            return false;
        }

        return true;
    }

    static bool read_data_type_array(common::ro_stream *stream, std::vector<data_type> &types) {
        std::int16_t count = 0;
        if (stream->read(&count, sizeof(count)) != sizeof(count)) {
            return false;
        }

        if (count <= 0) {
            return true;
        }

        types.reserve(types.size() + static_cast<std::size_t>(count));
        for (std::int16_t i = 0; i < count; i++) {
            data_type type{};
            if (stream->read(&type.priority_, sizeof(type.priority_)) != sizeof(type.priority_)) {
                return false;
            }
            if (!read_str8(stream, type.type_)) {
                return false;
            }
            types.push_back(std::move(type));
        }

        return true;
    }

""" + helper_anchor
    text = replace_once(text, helper_anchor, helpers, "registration helpers")

    old = """        if (stream->read(&reg.default_screen_number, 1) != 1) {
            return false;
        }

        // TODO: Read MIME infos, and file ownership lists

        return true;
    }
"""
    new = """        if (stream->read(&reg.default_screen_number, 1) != 1) {
            return false;
        }

        // Older registration resources may end here. All fields below are optional
        // from EKA2L1's compatibility perspective.
        if (stream->left() < sizeof(std::int16_t)) {
            return true;
        }

        if (!read_data_type_array(stream, reg.data_types)) {
            return false;
        }

        if (stream->left() < sizeof(std::int16_t)) {
            return true;
        }

        std::int16_t ownership_count = 0;
        if (stream->read(&ownership_count, sizeof(ownership_count)) != sizeof(ownership_count)) {
            return false;
        }

        for (std::int16_t i = 0; i < ownership_count; i++) {
            std::u16string owned_file;
            if (!read_str16_aligned(stream, owned_file)) {
                return false;
            }
            reg.ownership_list.push_back(std::move(owned_file));
        }

        // SERVICE_INFO did not exist in the earliest registration format.
        if (stream->left() < sizeof(std::int16_t)) {
            return true;
        }

        std::int16_t service_count = 0;
        if (stream->read(&service_count, sizeof(service_count)) != sizeof(service_count)) {
            return false;
        }

        if (service_count > 0) {
            reg.services.reserve(static_cast<std::size_t>(service_count));
        }

        for (std::int16_t i = 0; i < service_count; i++) {
            apa_app_service_info service{};
            if (stream->read(&service.uid_, sizeof(service.uid_)) != sizeof(service.uid_)) {
                return false;
            }

            if (!read_data_type_array(stream, service.data_types_)) {
                return false;
            }

            if (stream->read(&service.opaque_resource_id_, sizeof(service.opaque_resource_id_))
                != sizeof(service.opaque_resource_id_)) {
                return false;
            }

            reg.services.push_back(std::move(service));
        }

        // Final APP_REGISTRATION_INFO LLINK opaque_data belongs to the app launcher,
        // not to SERVICE_INFO. Consume it when present so the layout stays exact.
        if (stream->left() >= sizeof(std::uint32_t)) {
            std::uint32_t app_opaque_resource_id = 0;
            stream->read(&app_opaque_resource_id, sizeof(app_opaque_resource_id));
        }

        return true;
    }
"""
    text = replace_once(text, old, new, "modern optional registration parser")
    reg_cpp.write_text(text, encoding="utf-8")

    # ------------------------------------------------------------------
    # applist.cpp: resolve opaque resources, filter service apps, serialize impls.
    # ------------------------------------------------------------------
    text = applist_cpp.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "#include <common/benchmark.h>\n",
        "#include <common/benchmark.h>\n#include <common/buffer.h>\n",
        "buffer include",
    )
    text = replace_once(
        text,
        "#include <utils/apacmd.h>\n",
        "#include <utils/apacmd.h>\n#include <utils/cardinality.h>\n",
        "cardinality include",
    )

    helper_anchor = """    static void populate_icon_sizes(common::chunkyseri &seri, apa_app_registry *reg) {
"""
    service_helpers = """    static bool registry_implements_service(const apa_app_registry &reg, const std::uint32_t service_uid) {
        return std::any_of(reg.services.begin(), reg.services.end(),
            [service_uid](const apa_app_service_info &service) {
                return service.uid_ == service_uid;
            });
    }

    static bool write_symbian_des8(common::wo_stream &stream, const std::uint8_t *data,
        const std::size_t size) {
        if (size > 0x7FFFFFFEU) {
            return false;
        }

        // TDesHeader(TDesC8): cardinality value = (length << 1) + 1.
        utils::cardinality header(static_cast<std::uint32_t>((size << 1) + 1));
        if (!header.externalize(stream)) {
            return false;
        }

        return !size || stream.write(data, size) == size;
    }

    static bool write_symbian_des8(common::wo_stream &stream, const std::string &data) {
        return write_symbian_des8(stream,
            reinterpret_cast<const std::uint8_t *>(data.data()), data.size());
    }

    struct app_service_impl_ref {
        std::uint32_t app_uid_;
        const apa_app_service_info *service_;
    };

    static std::optional<std::string> serialize_service_impl_array(
        const std::vector<app_service_impl_ref> &implementations) {
        common::wo_growable_buf_stream stream;

        utils::cardinality outer_count(static_cast<std::uint32_t>(implementations.size()));
        if (!outer_count.externalize(stream)) {
            return std::nullopt;
        }

        for (const auto &impl : implementations) {
            if (stream.write(&impl.app_uid_, sizeof(impl.app_uid_)) != sizeof(impl.app_uid_)) {
                return std::nullopt;
            }

            utils::cardinality type_count(
                static_cast<std::uint32_t>(impl.service_->data_types_.size()));
            if (!type_count.externalize(stream)) {
                return std::nullopt;
            }

            for (const auto &type : impl.service_->data_types_) {
                if (!write_symbian_des8(stream, type.type_)) {
                    return std::nullopt;
                }
                if (stream.write(&type.priority_, sizeof(type.priority_)) != sizeof(type.priority_)) {
                    return std::nullopt;
                }
            }

            if (!write_symbian_des8(stream, impl.service_->opaque_data_.data(),
                    impl.service_->opaque_data_.size())) {
                return std::nullopt;
            }
        }

        return stream.content();
    }

""" + helper_anchor
    text = replace_once(text, helper_anchor, service_helpers, "service serialization helpers")

    # Repeated RSC reads must start from offset zero.
    old = """            eka2l1::ro_file_stream std_rsc_raw(f.get());
            if (!std_rsc_raw.valid()) {
                return {};
            }

            loader::rsc_file std_rsc(reinterpret_cast<common::ro_stream *>(&std_rsc_raw));
"""
    new = """            eka2l1::ro_file_stream std_rsc_raw(f.get());
            if (!std_rsc_raw.valid()) {
                return {};
            }
            std_rsc_raw.seek(0, common::seek_where::beg);

            loader::rsc_file std_rsc(reinterpret_cast<common::ro_stream *>(&std_rsc_raw));
"""
    text = replace_once(text, old, new, "RSC repeat read reset")

    old = """        if (!result) {
            return false;
        }

        // Getting our localised resource info
"""
    new = """        if (!result) {
            return false;
        }

        // Resolve SERVICE_INFO opaque data stored in the registration file.
        // KResourceOffsetMask means the data lives in the localisable RSC instead.
        static constexpr std::uint32_t KResourceOffsetMask = 0xFFFFF000U;
        for (auto &service : reg.services) {
            if (service.opaque_resource_id_
                && !(service.opaque_resource_id_ & KResourceOffsetMask)) {
                service.opaque_data_ = read_rsc_from_file(
                    f, static_cast<int>(service.opaque_resource_id_), false, nullptr);
            }
        }

        // Getting our localised resource info
"""
    text = replace_once(text, old, new, "registration opaque resolution")

    old = """        f = io->open_file(localised_path, READ_MODE | BIN_MODE);

        dat = read_rsc_from_file(f, reg.localised_info_rsc_id, true, nullptr);

        common::ro_buf_stream localised_app_info_resource_stream(&dat[0], dat.size());
"""
    new = """        f = io->open_file(localised_path, READ_MODE | BIN_MODE);

        if (f) {
            for (auto &service : reg.services) {
                if (service.opaque_resource_id_
                    && (service.opaque_resource_id_ & KResourceOffsetMask)) {
                    service.opaque_data_ = read_rsc_from_file(
                        f, static_cast<int>(service.opaque_resource_id_), true, nullptr);
                }
            }
        }

        dat = read_rsc_from_file(f, reg.localised_info_rsc_id, true, nullptr);

        common::ro_buf_stream localised_app_info_resource_stream(
            dat.empty() ? nullptr : &dat[0], dat.size());
"""
    text = replace_once(text, old, new, "localized opaque resolution")

    old = """        LOG_INFO(SERVICE_APPLIST, "Found app: {}, uid: 0x{:X}",
            common::ucs2_to_utf8(reg.mandatory_info.long_caption.to_std_string(nullptr)),
            reg.mandatory_info.uid);
"""
    new = """        LOG_INFO(SERVICE_APPLIST, "Found app: {}, uid: 0x{:X}",
            common::ucs2_to_utf8(reg.mandatory_info.long_caption.to_std_string(nullptr)),
            reg.mandatory_info.uid);

        if (!reg.services.empty()) {
            LOG_WARN(SERVICE_APPLIST,
                "SYMBIAN-SYSTEMAPPS1 MENUUI25 SERVICE_REG: app_uid=0x{:08X} service_count={}",
                reg.mandatory_info.uid, reg.services.size());
        }
"""
    text = replace_once(text, old, new, "service registry diagnostic")

    old = """    applist_session::applist_session(service::typical_server *svr, kernel::uid client_ss_uid, epoc::version client_ver)
        : typical_session(svr, client_ss_uid, client_ver)
        , filter_method_(APP_FILTER_NONE) {
    }
"""
    new = """    applist_session::applist_session(service::typical_server *svr, kernel::uid client_ss_uid, epoc::version client_ver)
        : typical_session(svr, client_ss_uid, client_ver)
        , requested_service_screen_mode_(-1)
        , requested_service_uid_(0)
        , filter_method_(APP_FILTER_NONE) {
    }
"""
    text = replace_once(text, old, new, "session constructor")

    method_anchor = """    void applist_session::get_next_app(service::ipc_context &ctx) {
"""
    methods = """    void applist_session::init_server_app_list(service::ipc_context &ctx) {
        const std::optional<std::int32_t> screen_mode =
            ctx.get_argument_value<std::int32_t>(0);
        const std::optional<std::uint32_t> service_uid =
            ctx.get_argument_value<std::uint32_t>(1);

        if (!screen_mode.has_value() || !service_uid.has_value()) {
            ctx.complete(epoc::error_argument);
            return;
        }

        requested_service_screen_mode_ = screen_mode.value();
        requested_service_uid_ = service_uid.value();
        current_index_ = 0;
        filter_method_ = APP_FILTER_BY_SERVICE;

        LOG_WARN(SERVICE_APPLIST,
            "SYMBIAN-SYSTEMAPPS1 MENUUI25 SERVER_APPLIST: result=armed opcode=46 service_uid=0x{:08X} screen_mode={}",
            requested_service_uid_, requested_service_screen_mode_);
        ctx.complete(epoc::error_none);
    }

    void applist_session::get_service_implementations(service::ipc_context &ctx) {
        const std::optional<std::uint32_t> service_uid =
            ctx.get_argument_value<std::uint32_t>(0);
        const std::optional<std::int32_t> initial_size =
            ctx.get_argument_value<std::int32_t>(2);

        if (!service_uid.has_value() || !initial_size.has_value() || initial_size.value() < 0) {
            service_buffer_.clear();
            ctx.complete(epoc::error_argument);
            return;
        }

        if (initial_size.value() > 0) {
            std::vector<app_service_impl_ref> implementations;
            auto &registries = server<applist_server>()->regs;

            for (const auto &reg : registries) {
                for (auto it = reg.services.rbegin(); it != reg.services.rend(); ++it) {
                    if (it->uid_ == service_uid.value()) {
                        implementations.push_back(
                            { reg.mandatory_info.uid, &(*it) });
                    }
                }
            }

            if (implementations.empty()) {
                service_buffer_.clear();
                LOG_WARN(SERVICE_APPLIST,
                    "SYMBIAN-SYSTEMAPPS1 MENUUI25 SERVICE_IMPL: result=not_found opcode=48 service_uid=0x{:08X}",
                    service_uid.value());
                ctx.complete(epoc::error_not_found);
                return;
            }

            const std::optional<std::string> serialized =
                serialize_service_impl_array(implementations);
            if (!serialized.has_value()) {
                service_buffer_.clear();
                ctx.complete(epoc::error_general);
                return;
            }

            service_buffer_ = serialized.value();

            if (service_buffer_.size() > static_cast<std::size_t>(initial_size.value())) {
                LOG_WARN(SERVICE_APPLIST,
                    "SYMBIAN-SYSTEMAPPS1 MENUUI25 SERVICE_IMPL: result=resize opcode=48 service_uid=0x{:08X} entries={} bytes={} initial={}",
                    service_uid.value(), implementations.size(),
                    service_buffer_.size(), initial_size.value());
                ctx.complete(static_cast<int>(service_buffer_.size()));
                return;
            }

            LOG_WARN(SERVICE_APPLIST,
                "SYMBIAN-SYSTEMAPPS1 MENUUI25 SERVICE_IMPL: result=ready opcode=48 service_uid=0x{:08X} entries={} bytes={} initial={}",
                service_uid.value(), implementations.size(),
                service_buffer_.size(), initial_size.value());
        } else if (service_buffer_.empty()) {
            ctx.complete(epoc::error_not_ready);
            return;
        }

        if (!ctx.write_data_to_descriptor_argument(3,
                reinterpret_cast<const std::uint8_t *>(service_buffer_.data()),
                static_cast<std::uint32_t>(service_buffer_.size()))) {
            service_buffer_.clear();
            ctx.complete(epoc::error_bad_descriptor);
            return;
        }

        LOG_WARN(SERVICE_APPLIST,
            "SYMBIAN-SYSTEMAPPS1 MENUUI25 SERVICE_IMPL: result=complete opcode=48 service_uid=0x{:08X} bytes={}",
            service_uid.value(), service_buffer_.size());
        service_buffer_.clear();
        ctx.complete(epoc::error_none);
    }

""" + method_anchor
    text = replace_once(text, method_anchor, methods, "service session methods")

    old = """        auto &registries = server<applist_server>()->regs;
        for (; current_index_ < registries.size(); current_index_++) {
            if (!registries[current_index_].supports_screen_mode(requested_screen_mode_)) {
                continue;
            }
            
            if (filter_method_ == APP_FILTER_BY_FLAGS) {
                if ((registries[current_index_].caps.flags & flags_mask_) == flags_match_value_) {
                    ctx.write_data_to_descriptor_argument<apa_app_info>(1, registries[current_index_].mandatory_info);
                    ctx.complete(epoc::error_none);

                    current_index_++;

                    return;
                }
            }
        }
"""
    new = """        auto &registries = server<applist_server>()->regs;
        for (; current_index_ < registries.size(); current_index_++) {
            const int screen_mode = (filter_method_ == APP_FILTER_BY_SERVICE)
                ? requested_service_screen_mode_
                : static_cast<int>(requested_screen_mode_);

            if (!registries[current_index_].supports_screen_mode(screen_mode)) {
                continue;
            }
            
            if (filter_method_ == APP_FILTER_BY_FLAGS) {
                if ((registries[current_index_].caps.flags & flags_mask_) == flags_match_value_) {
                    ctx.write_data_to_descriptor_argument<apa_app_info>(1, registries[current_index_].mandatory_info);
                    ctx.complete(epoc::error_none);

                    current_index_++;

                    return;
                }
            } else if (filter_method_ == APP_FILTER_BY_SERVICE) {
                if (registry_implements_service(
                        registries[current_index_], requested_service_uid_)) {
                    LOG_WARN(SERVICE_APPLIST,
                        "SYMBIAN-SYSTEMAPPS1 MENUUI25 SERVER_APPLIST: result=match opcode=4 service_uid=0x{:08X} app_uid=0x{:08X}",
                        requested_service_uid_,
                        registries[current_index_].mandatory_info.uid);
                    ctx.write_data_to_descriptor_argument<apa_app_info>(
                        1, registries[current_index_].mandatory_info);
                    ctx.complete(epoc::error_none);

                    current_index_++;
                    return;
                }
            }
        }
"""
    text = replace_once(text, old, new, "get_next service filter")

    switch_anchor = """            case applsit_request_init_attr_filtered_list:
                get_filtered_apps_by_flags(*ctx);
                break;

            case applist_request_get_next_app:
                get_next_app(*ctx);
                break;
"""
    switch_new = """            case applist_request_init_server_applist:
                init_server_app_list(*ctx);
                break;

            case applist_request_get_service_implementations:
                get_service_implementations(*ctx);
                break;

            case applsit_request_init_attr_filtered_list:
                get_filtered_apps_by_flags(*ctx);
                break;

            case applist_request_get_next_app:
                get_next_app(*ctx);
                break;
"""
    text = replace_once(text, switch_anchor, switch_new, "modern AppList switch")

    # Gates.
    for required in (
        "case applist_request_init_server_applist:",
        "case applist_request_get_service_implementations:",
        "APP_FILTER_BY_SERVICE",
        "serialize_service_impl_array",
        "reg.services",
        server_marker,
        service_marker,
        reg_marker,
    ):
        if required not in text and required != "APP_FILTER_BY_SERVICE":
            fail("applist implementation gate missing: " + required)

    applist_cpp.write_text(text, encoding="utf-8")

    # Header gates after writes.
    h = applist_h.read_text(encoding="utf-8")
    for required in (
        "APP_FILTER_BY_SERVICE",
        "requested_service_uid_",
        "get_service_implementations",
        "std::vector<apa_app_service_info> services;",
    ):
        if required not in h:
            fail("applist header gate missing: " + required)

    reg = reg_cpp.read_text(encoding="utf-8")
    for required in (
        "read_data_type_array",
        "service_count",
        "opaque_resource_id_",
    ):
        if required not in reg:
            fail("registration parser gate missing: " + required)

    print("MENUUI25 APPSERVICE1 applied")
    print("opcode46=InitServerAppList_IMPLEMENTED")
    print("opcode48=GetServiceImplementations_IMPLEMENTED")
    print("service_registry=PARSED opaque_data=RESOLVED")
    print("forced_process_kill=NOT_ADDED scheduler_change=NONE canvas_change=NONE")
    print("MENUUI24/MENUUI23/SCHEDRUN1/MANIC3/NOJAVA=PRESERVED")


if __name__ == "__main__":
    main()
