# DirectHome TFX Callsite Probe Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ghi thanh ghi ngay trước lệnh `Cone.dll+0x215E` và cùng định danh process/thread với lần `CreateSession("TfxServer")` trên DirectHome, chỉ để quan sát.

**Architecture:** Patcher FASTBUILD thêm callback tùy chọn vào `arm::core`; Dyncom chỉ gọi ở PC `0x806EAFC6`, trước dispatch; scheduler gắn định danh của thread đang thực thi. Một patcher riêng thêm log phiên TFX, không sửa patcher B43. Mỗi patcher chạy atomically theo nhiều tệp và từ chối anchor lệch.

**Tech Stack:** Python 3 patchers/unittest, upstream EKA2L1 C++ (Dyncom/kernel), GitHub Actions FASTBUILD iOS.

**Spec:** `docs/superpowers/specs/2026-09-28-directhome-tfxcallsiteprobe-design.md`

## Global Constraints

- Chỉ nhánh `codex/compatboot1-directhome`; không sửa B99 `b14804a4ccd594d837496e2f106c4b5e8a2cdb10`, không merge PR.
- Gate duy nhất: `native_phone_boot && compat_menu_probe_mode && compat_target_kind == 2`; Native Boot mặc định và Menu3 không bị ảnh hưởng.
- Firmware RM-356 v60.0.003, `ailaunch.exe` thật và barrier sáu dịch vụ giữ nguyên; TFX-off đã revert không được khôi phục.
- Không tạo server giả, đổi CenRep/IPC, completion, `KErrNotFound`, thanh ghi/PC, thứ tự lệnh guest hay panic.
- Mục tiêu chính xác `Cone.dll` base `0x806E8E68` + `0x215E` = PC Thumb đã chuẩn hóa `0x806EAFC6`; base thay đổi phải dừng xác minh.
- Không có local upstream tree: test fixture trước; FASTBUILD phải xác nhận anchor của cây B28 cache thực và dừng nếu lệch.
- Chỉ kết luận đã vào Home khi giao diện Symbian thật hiển thị và tương tác được trên thiết bị.

## Review Focus

- PC Thumb có bit 0, lân cận `0x806EAFC4/0x806EAFC8` hoặc ARM state: chỉ chính xác PC Thumb đích mới log (Task 1).
- B28 cache khác source upstream đã khảo sát: patcher lỗi trước mọi ghi tệp, không thử anchor gần đúng (Task 1).
- CPU chạy lúc không có `crr_thread` hoặc process đã mất: log `context=missing`, không gán nhầm thread cũ (Task 2).
- Config chuyển sang DirectHome sau khi scheduler đã được tạo, hoặc chuyển ra khỏi nó: callback gắn/gỡ ở context switch, không giữ profile cũ khi tái khởi động (Task 2).
- TFX server có hoặc không có, hoặc process/thread trống: log ba pha đúng ID/ngữ cảnh, đường `KErrNotFound`/server gốc không đổi (Task 3).

---

## File Structure

- `apply_nativeboot2_directhome_tfxcallsiteprobe1.py`: kiểm tra toàn bộ anchor trước khi ghi, vá interface core, Dyncom và scheduler; không ôm logic phiên TFX.
- `test_nativeboot2_directhome_tfxcallsiteprobe1.py`: unittest fixture cho preflight, matching/ordering, gating, lifecycle và hợp đồng C++ được tạo.
- `apply_nativeboot2_directhome_tfxsessiontrace1.py`: vá riêng `session_create` sau B43; không sửa script B43.
- `test_nativeboot2_directhome_tfxsessiontrace1.py`: fixture và contract cho request/missing/found, ID, semantics.
- `ci/fastbuild1_manifest.txt`, `test_fastbuild1_manifest.py`: ghép cặp apply/test theo thứ tự sau ECom trace.
- `.github/workflows/build-ios-nativeboot2-current-fast.yml`, `test_fastbuild1_workflows.py`: gate binary có hai marker mới và vẫn loại B99/bypass.
- Chỉ trong upstream tree khi patcher chạy: `src/emu/cpu/include/cpu/arm_interface.h`, `src/emu/cpu/src/dyncom/arm_dyncom_interpreter.cpp`, `src/emu/kernel/src/scheduler.cpp`, `src/emu/kernel/src/svc.cpp`.

### Task 1: Interface core và hook Dyncom chính xác

**Files:** Create `apply_nativeboot2_directhome_tfxcallsiteprobe1.py`, `test_nativeboot2_directhome_tfxcallsiteprobe1.py`; patch upstream `arm_interface.h`, `arm_dyncom_interpreter.cpp` (scheduler patch chỉ ở Task 2).

**Interfaces:** Produce `arm::directhome_tfx_callsite_sample { std::uint32_t pc,r0,r1,lr,sp,cpsr; bool thumb; }` and `arm::core::set_directhome_tfx_callsite_observer(std::function<void(const directhome_tfx_callsite_sample &)>)`; a null observer is a no-op. Add one protected/public dispatch helper on `arm::core` for Dyncom according to actual class visibility. Patcher exposes `apply_to_core(source: str) -> str`, `apply_to_dyncom(source: str) -> str` and prevalidates all three target files before any disk write.

- [ ] **Step 1: Viết test RED** `test_only_thumb_exact_pc_before_dispatch`: fixture Dyncom có `GOTO_NEXT_INST`, `Reg[15/0/1/14/13]` và CPSR/TFlag; assert `pc == 0x806EAFC6 && thumb`, sample dùng đúng các thanh ghi, hook nằm trước instruction dispatch; không có write tới Reg/PC hay thay `GOTO_NEXT_INST`. Test neighbor/ARM state không hit.
- [ ] **Step 2: Viết test RED** `test_missing_duplicate_anchor_is_atomic_and_idempotent`: thiếu/trùng một anchor trong từng file, thiếu scheduler hay file không đúng revision đều raise `SystemExit`, nội dung mọi tệp giữ nguyên; apply hai lần cho output giống nhau, trạng thái partial marker bị từ chối.
- [ ] **Step 3: Chạy** `python3 -m unittest test_nativeboot2_directhome_tfxcallsiteprobe1.py -v`; mong đợi FAIL vì patcher/interface chưa có.
- [ ] **Step 4: Đối chiếu cây upstream B28 nếu có** `rg -n 'GOTO_NEXT_INST|class core|switch_context' <upstream>/src/emu/{cpu,kernel}` và xác định duy nhất vị trí hook *trước* dispatch, interface/visibility, destructor và include C++ thực tế. Nếu không có cây local, chỉ dùng fixture và để FASTBUILD fail-closed xác thực; không mở rộng anchor dựa trên phỏng đoán.
- [ ] **Step 5: Cài patcher** với sample/callback như Interfaces và điều kiện `pc == 0x806EAFC6 && thumb` tại đúng pre-dispatch; callback null no-op; preflight toàn bộ bốn file rồi mới ghi, dùng một marker trạng thái nhất quán cho mỗi vùng; không đọc guest memory hay sửa control flow.
- [ ] **Step 6: Chạy** `python3 -m unittest test_nativeboot2_directhome_tfxcallsiteprobe1.py -v`; mong đợi các test Task 1 PASS.
- [ ] **Step 7: Commit** `feat: add fail-closed Dyncom TFX callsite observer` với đúng hai script mới.

### Task 2: Scheduler gắn context DirectHome và lifecycle

**Files:** Modify `apply_nativeboot2_directhome_tfxcallsiteprobe1.py`, `test_nativeboot2_directhome_tfxcallsiteprobe1.py`; patch upstream `scheduler.cpp`.

**Interfaces:** Consume `arm::core::set_directhome_tfx_callsite_observer(...)` and `arm::directhome_tfx_callsite_sample`. Callback scheduler lấy `crr_thread` hiện tại và `owning_process()` ngay tại hit; output `[NBOOT2][DIRECTHOME_TFX_CALLSITE]` với `behavior=OBSERVE_ONLY`, `profile=DirectHome`, `pc`, `module=Cone.dll`, `offset=0x215E`, `r0`, `r1`, `lr`, `sp`, `cpsr`, `thumb`, process UID3/name/`unique_id()`, thread name/`unique_id()`; thiếu context ghi `context=missing` và không in ID của context trước. Chỉ cài sau gate DirectHome; clear callback trước khi scheduler/core bị hủy.

- [ ] **Step 1: Viết test RED** `test_scheduler_profile_gate_and_same_thread_identity`: assert cả ba gate; callback lấy thread tại invocation (không capture process/thread lúc cài), đúng UID3/tên/unique IDs, và không có probe ở Native Boot/Menu3.
- [ ] **Step 2: Viết test RED** `test_missing_context_and_destroy_clear_callback`: null thread/process in `context=missing`, không dereference; config bật DirectHome sau lúc dựng scheduler thì gắn callback ở lần context switch kế tiếp, tắt profile thì gỡ; observer được clear trước teardown, không còn callback stale khi restart.
- [ ] **Step 3: Chạy** `python3 -m unittest test_nativeboot2_directhome_tfxcallsiteprobe1.py -v`; mong đợi FAIL ở assertions scheduler marker/gate/lifetime.
- [ ] **Step 4: Vá scheduler** dùng core mà `switch_context` nạp context, cập nhật gắn/gỡ callback theo profile tại context switch và clear trước teardown; tránh capture raw thread/process lâu dài. Xác minh `unique_id()` trên process/thread và thực tế sở hữu core tại B28 trước khi chốt anchor; không thay scheduling.
- [ ] **Step 5: Chạy** `python3 -m unittest test_nativeboot2_directhome_tfxcallsiteprobe1.py -v`; mong đợi PASS gồm idempotence, atomicity, missing context và non-DirectHome.
- [ ] **Step 6: Commit** `feat: attribute DirectHome TFX callsite to current guest thread`.

### Task 3: Companion CreateSession trace

**Files:** Create `apply_nativeboot2_directhome_tfxsessiontrace1.py`, `test_nativeboot2_directhome_tfxsessiontrace1.py`; patch upstream `src/emu/kernel/src/svc.cpp`.

**Interfaces:** Produce `[NBOOT2][DIRECTHOME_TFX_SESSION]` on `request`, `missing`, `found` for literal `server_name == "TfxServer"` gated by the same DirectHome triple. Fields `pid`/`tid` from `pr->unique_id()`/`kern->crr_thread()->unique_id()` plus names/UID3, or explicit `context=missing`. No change to existing `[NBOOT2][TFX_SESSION]` and B43 `b43_tfx_miss`; keep original miss return and found `do_create_session_from_server(...)`.

- [ ] **Step 1: Viết test RED** `test_three_phases_same_ids_and_gate`: fixture B43 `session_create` asserts request before lookup, missing before `return epoc::error_not_found`, found before original `do_create_session_from_server`, same PID/TID expressions and triple gate; non-TFX/native/Menu3 không log.
- [ ] **Step 2: Viết test RED** `test_null_context_existing_marker_and_atomicity`: null thread/process safe; B43 marker/logic unchanged; missing/duplicate anchor and partial marker fail before write; second apply no-op; no fake server, IPC/completion rewrite.
- [ ] **Step 3: Chạy** `python3 -m unittest test_nativeboot2_directhome_tfxsessiontrace1.py -v`; mong đợi FAIL vì patcher chưa có.
- [ ] **Step 4: Cài patcher `session_create`** trên vùng bounded giữa `session_create` và `session_create_from_handle`, không sửa B43 script; xác minh B28+B43 anchor; chỉ ghi sau khi mọi điều kiện độc nhất được kiểm tra.
- [ ] **Step 5: Chạy** `python3 -m unittest test_nativeboot2_directhome_tfxsessiontrace1.py -v`; mong đợi fixture PASS. Khi có upstream tree đã apply B43, chạy `python3 test_nativeboot2_b43_tfxserverdiag1.py <upstream>` và contract script mới với cùng đối số; mong đợi cả hai PASS.
- [ ] **Step 6: Commit** `feat: correlate DirectHome TFX sessions without altering IPC`.

### Task 4: Tích hợp manifest, binary gate và xác minh

**Files:** Modify `ci/fastbuild1_manifest.txt`, `test_fastbuild1_manifest.py`, `.github/workflows/build-ios-nativeboot2-current-fast.yml`, `test_fastbuild1_workflows.py`.

**Interfaces:** Append callsite apply/test then session apply/test after `apply_nativeboot2_directhome_tfxecomtrace1.py|test_nativeboot2_directhome_tfxecomtrace1.py`; workflow `strings` must contain both exact markers, DirectHome BUILD_ID exactly once, no B99 BUILD_ID and no PhoneUI bypass markers.

- [ ] **Step 1: Viết test RED** `test_checked_in_manifest_includes_latest_compatboot_diagnostics` for exact final two pairs and previous ECom pair, plus workflow test `test_current_build_verifies_directhome_tfx_probe_markers` for both `grep -Fq` gates and existing B99/bypass checks.
- [ ] **Step 2: Chạy** `python3 -m unittest test_fastbuild1_manifest.py test_fastbuild1_workflows.py -v`; mong đợi FAIL ở thứ tự và marker mới.
- [ ] **Step 3: Sửa manifest và workflow** như Interfaces; không chạm B28 workflow hay B99 branch, giữ cổng binary cũ.
- [ ] **Step 4: Chạy** `python3 -m unittest test_nativeboot2_directhome_tfxcallsiteprobe1.py test_nativeboot2_directhome_tfxsessiontrace1.py test_fastbuild1_manifest.py test_fastbuild1_workflows.py -v` và `python3 ci/fastbuild1_manifest.py validate .`; mong đợi PASS và `FASTBUILD1-MANIFEST: VALID`.
- [ ] **Step 5: Chạy toàn bộ** `python3 -m unittest discover -p 'test_*.py' -v`; ghi rõ test nào SKIP vì thiếu upstream tree; `git diff --check`; không tuyên bố C++ build pass từ source-contract test.
- [ ] **Step 6: Commit** `ci: gate DirectHome TFX callsite and session markers` sau kiểm thử.
- [ ] **Step 7: Đối chiếu FASTBUILD** chỉ khi nhánh đã push và workflow được phép dispatch: đúng SHA nhánh DirectHome, cache B28 apply/test từng cặp, compile iOS, `strings` có hai marker, IPA/SHA-256 và không có marker B99; nếu anchor/compile fail, dừng và sửa có test, không gửi IPA lỗi. Không tự kết luận Home đã chạy từ build hoặc log; đợi thử thiết bị.

## Handoff

Kế hoạch này chỉ tạo nguồn và kiểm thử trước; build/IPA là cổng xác minh sau khi mã được review. File kế hoạch crash-teardowntrace1 đang untracked là của người dùng, không stage hay ghi đè. Người triển khai phải đọc spec và kiểm tra `git status` trước từng commit, chỉ stage các file trong task.
