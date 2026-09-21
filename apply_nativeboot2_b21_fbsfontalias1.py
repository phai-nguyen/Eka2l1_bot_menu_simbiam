#!/usr/bin/env python3
"""Apply NATIVEBOOT2 B21 FBSFONTALIAS1 on top of B20.

B20 device evidence:
- graphics/UI startup reaches splashscreen, AknIconSrv, AppArc and akncapserver;
- akncapserver sends FBS opcode 0x1E and then stops progressing;
- ~30 seconds later SysStart/Domino kills akncapserver with KErrTimedOut.

Symbian 9.4 TFbsMessage defines opcode 30/0x1E as EFbsMessFontNameAlias.
CFbsTypefaceStore::SetFontNameAliasL sends:
    slot0 = alias descriptor
    slot1 = alias length
    slot2 = target font descriptor
    slot3 = target length
The real FBServ stores/updates/removes a case-insensitive alias and completes.

B21 implements that behavior in EKA2L1's existing font_store:
- decode the documented IPC ABI;
- add/update/delete aliases case-insensitively;
- during font lookup, try the requested name first, then its alias if needed;
- complete KErrNone on valid requests and KErrBadDescriptor on malformed IPC;
- emit [NBOOT2][FBS_FONT_ALIAS] diagnostics.

No unrelated FBS opcode is changed.
"""
from __future__ import annotations
import sys
from pathlib import Path

MARK = "NATIVEBOOT2-B21-FBSFONTALIAS1"

def fail(msg: str) -> None:
    raise SystemExit(f"{MARK}: {msg}")

def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        fail(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)

def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: apply_nativeboot2_b21_fbsfontalias1.py <upstream-root>")

    up = Path(sys.argv[1]).resolve()
    fbs_cpp = up / "src/emu/services/src/fbs/fbs.cpp"
    fbs_h = up / "src/emu/services/include/services/fbs/fbs.h"
    store_cpp = up / "src/emu/services/src/fbs/impls/font_store.cpp"
    store_h = up / "src/emu/services/include/services/fbs/font_store.h"
    repo_cpp = up / "src/emu/services/src/centralrepo/repo.cpp"
    cen_cpp = up / "src/emu/services/src/centralrepo/centralrepo.cpp"
    sa_cpp = up / "src/emu/services/src/sms/sa/sa.cpp"
    svc = up / "src/emu/kernel/src/svc.cpp"
    fs = up / "src/emu/services/src/fs/fs.cpp"
    loader = up / "src/emu/services/src/loader/loader.cpp"
    hal = up / "src/emu/system/src/hal.cpp"
    state = up / "src/emu/ios/src/state.cpp"
    root = up / "src/emu/ios/app/RootViewController.mm"

    for p in (fbs_cpp, fbs_h, store_cpp, store_h, repo_cpp, cen_cpp, sa_cpp,
              svc, fs, loader, hal, state, root):
        if not p.is_file():
            fail(f"missing baseline file: {p}")

    # B20 checkpoint gates.
    rp = repo_cpp.read_text(encoding="utf-8")
    cc = cen_cpp.read_text(encoding="utf-8")
    for gate in (
        "[NBOOT2][CEN_RESET_ALL]",
        "[NBOOT2][CEN_RESET_ALL_DONE]",
        "[NBOOT2][CEN_RESET_ALL_FAIL]",
        "attach_repo->entries = init_repo->entries;",
        "attach_repo->deleted_settings = init_repo->deleted_settings;",
    ):
        if gate not in rp:
            fail(f"B20 repo gate missing: {gate}")
    if "NBOOT2::CenRepResetAll" not in cc:
        fail("B20 CenRep registration missing")

    # Earlier startup invariants.
    sa = sa_cpp.read_text(encoding="utf-8")
    for gate in (
        "[NBOOT2][SA_LANG_ABI]",
        "[NBOOT2][SA_RTC_VALID]",
        "[NBOOT2][SA_HIDDEN_RESET]",
        "[NBOOT2][SA_STARTUP_MODE]",
        "[NBOOT2][SA_OP1_PENDING]",
        "[NBOOT2][SA_RESPONSE]",
    ):
        if gate not in sa:
            fail(f"SAServer gate missing: {gate}")

    svc_text = svc.read_text(encoding="utf-8")
    for gate in (
        "[NBOOT2][DM_INIT_SET_INT]",
        "[NBOOT2][RM356_CREATOR_SECURITY]",
        "BRIDGE_REGISTER(0xB1, creator_security_info)",
    ):
        if gate not in svc_text:
            fail(f"kernel gate missing: {gate}")

    if "[NBOOT2][RM356_FS_FORMAT_OPEN]" not in fs.read_text(encoding="utf-8"):
        fail("B10 marker missing")
    if "[NBOOT2][RM356_LOADER_FSY]" not in loader.read_text(encoding="utf-8"):
        fail("B8 marker missing")
    if "[NBOOT2][RM356_STARTUP_REASON]" not in hal.read_text(encoding="utf-8"):
        fail("B6 marker missing")
    if "[NBOOT2][ESTART_RUN]" not in state.read_text(encoding="utf-8"):
        fail("ESTART marker missing")
    if "NATIVEBOOT2 EMUHUB1" not in root.read_text(encoding="utf-8"):
        fail("EMUHUB1 marker missing")
    if (up / "src/emu/j2me").exists():
        fail("NOJAVA invariant violated")

    fh = fbs_h.read_text(encoding="utf-8")
    if "fbs_font_name_alias" not in fh:
        fail("upstream FBS enum does not contain fbs_font_name_alias")

    decl_anchor = "        void set_pixel_size_in_twips(service::ipc_context *ctx);\n"
    decl_new = decl_anchor + "        void set_font_name_alias(service::ipc_context *ctx);\n"
    if "void set_font_name_alias(service::ipc_context *ctx);" not in fh:
        fh = replace_once(fh, decl_anchor, decl_new, "FBS FontNameAlias declaration")
    fbs_h.write_text(fh, encoding="utf-8")

    sh = store_h.read_text(encoding="utf-8")

    # Add only headers needed by the new persistent alias table API.
    if "#include <optional>" not in sh:
        sh = replace_once(sh, "#include <unordered_map>\n", "#include <optional>\n#include <unordered_map>\n", "font_store optional include")
    if "#include <utility>" not in sh:
        sh = replace_once(sh, "#include <unordered_map>\n", "#include <unordered_map>\n#include <utility>\n", "font_store utility include")

    member_anchor = "        std::vector<epoc::typeface_support> typefaces;\n"
    member_new = member_anchor + (
        "\n        // NATIVEBOOT2-B21: Symbian FBServ keeps font-name aliases in the\n"
        "        // top-level font store. Preserve insertion order and compare keys\n"
        "        // case-insensitively, matching CFbTop::FindFontNameAlias().\n"
        "        std::vector<std::pair<std::u16string, std::u16string>> font_name_aliases_;\n"
    )
    if "font_name_aliases_" not in sh:
        sh = replace_once(sh, member_anchor, member_new, "font alias storage")

    # Older cached baselines may not contain attach_user_font_fallbacks().
    # Anchor the new API on seek_the_open_font(), which exists in every
    # baseline supported by the B21 implementation and is the call site that
    # consumes the alias mapping.
    api_anchor = "        open_font_info *seek_the_open_font(epoc::font_spec_base &spec);\n"
    api_new = (
        "        void set_font_name_alias(const std::u16string &alias, const std::u16string &font_name);\n"
        "        std::optional<std::u16string> resolve_font_name_alias(const std::u16string &alias) const;\n\n"
        + api_anchor
    )
    if "void set_font_name_alias(const std::u16string &alias" not in sh:
        sh = replace_once(sh, api_anchor, api_new, "font alias API before seek_the_open_font")
    store_h.write_text(sh, encoding="utf-8")

    sc = store_cpp.read_text(encoding="utf-8")
    seek_anchor = "    open_font_info *font_store::seek_the_open_font(epoc::font_spec_base &spec) {\n"

    alias_impl = r'''    // NATIVEBOOT2-B21 FBSFONTALIAS1:
    // Symbian's CFbTop stores alternating alias/real-name descriptors and
    // compares aliases case-insensitively. Empty target removes the alias.
    void font_store::set_font_name_alias(const std::u16string &alias, const std::u16string &font_name) {
        for (auto it = font_name_aliases_.begin(); it != font_name_aliases_.end(); ++it) {
            if (common::compare_ignore_case(it->first, alias) == 0) {
                if (font_name.empty()) {
                    font_name_aliases_.erase(it);
                } else {
                    it->second = font_name;
                }
                return;
            }
        }

        if (!alias.empty() && !font_name.empty()) {
            font_name_aliases_.emplace_back(alias, font_name);
        }
    }

    std::optional<std::u16string> font_store::resolve_font_name_alias(const std::u16string &alias) const {
        for (const auto &entry : font_name_aliases_) {
            if (common::compare_ignore_case(entry.first, alias) == 0) {
                return entry.second;
            }
        }

        return std::nullopt;
    }

'''
    if "// NATIVEBOOT2-B21 FBSFONTALIAS1:" not in sc:
        sc = replace_once(sc, seek_anchor, alias_impl + seek_anchor, "font alias implementation")

    # The cached B19/B20 baseline uses the older one-pass font matcher.
    # Preserve its scoring algorithm: first give the requested face name its
    # existing exact-match chance, then (only when that fails) substitute a
    # configured alias target for the existing exact/scoring pass.
    legacy_name_anchor = "        const std::u16string my_name = spec.tf.name.to_std_string(nullptr);\n"
    legacy_name_new = """        const std::u16string requested_name = spec.tf.name.to_std_string(nullptr);

        // Symbian tries the requested name before consulting the alias table.
        for (auto &info : open_font_store) {
            if (info.face_attrib.name.to_std_string(nullptr) == requested_name) {
                return &info;
            }
        }

        const std::optional<std::u16string> aliased_name = resolve_font_name_alias(requested_name);
        const std::u16string my_name = aliased_name.has_value() ? *aliased_name : requested_name;
"""
    if "resolve_font_name_alias(requested_name)" not in sc:
        sc = replace_once(sc, legacy_name_anchor, legacy_name_new, "alias-aware legacy font lookup")
    store_cpp.write_text(sc, encoding="utf-8")

    fc = fbs_cpp.read_text(encoding="utf-8")
    fetch_anchor = "    void fbscli::fetch(service::ipc_context *ctx) {\n"

    handler = r'''    // NATIVEBOOT2-B21 FBSFONTALIAS1:
    // CFbsTypefaceStore::SetFontNameAliasL sends descriptors in slots 0/2
    // and their character counts in slots 1/3. A zero/negative target length
    // removes the alias. Valid requests are synchronous and must complete.
    void fbscli::set_font_name_alias(service::ipc_context *ctx) {
        const std::optional<std::int32_t> alias_len = ctx->get_argument_value<std::int32_t>(1);
        const std::optional<std::int32_t> font_len = ctx->get_argument_value<std::int32_t>(3);

        if (!alias_len.has_value() || !font_len.has_value()) {
            LOG_ERROR(SERVICE_FBS,
                "[NBOOT2][FBS_FONT_ALIAS] action=invalid reason=missing_lengths completion={}",
                epoc::error_bad_descriptor);
            ctx->complete(epoc::error_bad_descriptor);
            return;
        }

        // Symbian CFbTop treats an empty alias as a successful no-op.
        if (*alias_len <= 0) {
            LOG_WARN(SERVICE_FBS,
                "[NBOOT2][FBS_FONT_ALIAS] action=noop alias_len={} font_len={} completion=0",
                *alias_len, *font_len);
            ctx->complete(epoc::error_none);
            return;
        }

        const std::optional<std::u16string> alias = ctx->get_argument_value<std::u16string>(0);
        if (!alias.has_value() || (static_cast<std::int32_t>(alias->size()) != *alias_len)) {
            LOG_ERROR(SERVICE_FBS,
                "[NBOOT2][FBS_FONT_ALIAS] action=invalid reason=alias_descriptor alias_len={} completion={}",
                *alias_len, epoc::error_bad_descriptor);
            ctx->complete(epoc::error_bad_descriptor);
            return;
        }

        std::u16string font_name;
        const char *action = "delete";

        if (*font_len > 0) {
            const std::optional<std::u16string> font = ctx->get_argument_value<std::u16string>(2);
            if (!font.has_value() || (static_cast<std::int32_t>(font->size()) != *font_len)) {
                LOG_ERROR(SERVICE_FBS,
                    "[NBOOT2][FBS_FONT_ALIAS] action=invalid reason=font_descriptor font_len={} completion={}",
                    *font_len, epoc::error_bad_descriptor);
                ctx->complete(epoc::error_bad_descriptor);
                return;
            }

            font_name = *font;
            action = "set";
        }

        server<fbs_server>()->persistent_font_store.set_font_name_alias(*alias, font_name);

        LOG_WARN(SERVICE_FBS,
            "[NBOOT2][FBS_FONT_ALIAS] action={} alias={} font={} alias_len={} font_len={} completion=0",
            action, common::ucs2_to_utf8(*alias), common::ucs2_to_utf8(font_name),
            *alias_len, *font_len);

        ctx->complete(epoc::error_none);
    }

'''
    if "// NATIVEBOOT2-B21 FBSFONTALIAS1:" not in fc:
        fc = replace_once(fc, fetch_anchor, handler + fetch_anchor, "FBS FontNameAlias IPC handler")

    case_anchor = """        case fbs_get_default_glyph_bitmap_type:
            get_default_glyph_bitmap_type(ctx);
            break;

"""
    case_new = case_anchor + """        case fbs_font_name_alias:
            set_font_name_alias(ctx);
            break;

"""
    if "case fbs_font_name_alias:" not in fc:
        fc = replace_once(fc, case_anchor, case_new, "FBS FontNameAlias route")
    fbs_cpp.write_text(fc, encoding="utf-8")

    # Post-apply gates.
    fh = fbs_h.read_text(encoding="utf-8")
    fc = fbs_cpp.read_text(encoding="utf-8")
    sh = store_h.read_text(encoding="utf-8")
    sc = store_cpp.read_text(encoding="utf-8")

    for needle in (
        "void set_font_name_alias(service::ipc_context *ctx);",
        "fbs_font_name_alias",
    ):
        if needle not in fh:
            fail(f"post-apply fbs.h gate missing: {needle}")

    for needle in (
        "[NBOOT2][FBS_FONT_ALIAS]",
        "case fbs_font_name_alias:",
        "set_font_name_alias(ctx);",
        "persistent_font_store.set_font_name_alias",
        "ctx->complete(epoc::error_none);",
    ):
        if needle not in fc:
            fail(f"post-apply fbs.cpp gate missing: {needle}")

    for needle in (
        "font_name_aliases_",
        "set_font_name_alias(const std::u16string &alias",
        "resolve_font_name_alias(const std::u16string &alias) const",
    ):
        if needle not in sh:
            fail(f"post-apply font_store.h gate missing: {needle}")

    for needle in (
        "font_store::set_font_name_alias",
        "font_store::resolve_font_name_alias",
        "resolve_font_name_alias(requested_name)",
        "aliased_name",
        "common::compare_ignore_case",
    ):
        if needle not in sc:
            fail(f"post-apply font_store.cpp gate missing: {needle}")

    print("NATIVEBOOT2-B21 FBSFONTALIAS1 applied")
    print("fbs_opcode=0x1E_EFbsMessFontNameAlias")
    print("ipc_slots=alias_desc,alias_len,font_desc,font_len")
    print("alias_compare=CASE_INSENSITIVE")
    print("empty_font_name=DELETE_ALIAS")
    print("lookup=REQUESTED_NAME_THEN_ALIAS")
    print("valid_completion=KErrNone")
    print("malformed_completion=KErrBadDescriptor")
    print("B20_CENRESETALL1=PRESERVED")
    print("B19_SALANGABI1=PRESERVED")
    print("B18_SARTC1=PRESERVED")
    print("B17_SAHIDDENRESET1=PRESERVED")
    print("B16_SAMODE1=PRESERVED")
    print("B15_SAASYNC1=PRESERVED")
    print("B14_SARESPONSE1=PRESERVED")
    print("B11_DMINIT1=PRESERVED")
    print("NOJAVA=MANIC3=EMUHUB1=PRESERVED")

if __name__ == "__main__":
    main()
