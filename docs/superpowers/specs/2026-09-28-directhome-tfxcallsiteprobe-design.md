# Thiết kế DirectHome: TFX Callsite Register Probe

Trạng thái: spec đã được người dùng duyệt và probe đã triển khai trên nhánh DirectHome; chưa FASTBUILD, chưa tạo IPA, chưa thử trên thiết bị.

## Mục tiêu

Thu thập bằng chứng runtime ngay trước lệnh tại `Cone.dll+0x215E`: địa chỉ lệnh thực thi, `r0/r1` và định danh process/thread đang chạy. Đối chiếu sự kiện đó với lần Home gọi `CreateSession("TfxServer")` để xác định callback xuất hiện trong Home hay ở một caller khác.

Đây là build chẩn đoán, không phải thay đổi cách khởi chạy Home và không phải bằng chứng Home đã hoạt động.

## Phạm vi và bất biến

- Chỉ áp dụng trên `codex/compatboot1-directhome`; B99 đối chứng tiếp tục ở `b14804a4ccd594d837496e2f106c4b5e8a2cdb10` và không bị sửa.
- Chỉ kích hoạt ở profile CompatBoot vào Home: `native_phone_boot`, `compat_menu_probe_mode` và `compat_target_kind == 2` cùng được xác nhận.
- Giữ nguyên Native Boot mặc định, firmware RM-356 v60.0.003, đường khởi chạy `ailaunch.exe` thật và thứ tự sáu dịch vụ.
- Không tạo hoặc giả lập `TfxServer`; không đổi CenRep, IPC arguments, mã hoàn tất, thứ tự lệnh guest, panic hay semantics lỗi.
- Probe TFX-off vẫn ở trạng thái đã revert; không khôi phục hoặc tạo biến thể TFX-off.
- Không merge PR. Chỉ kết luận vào Home khi video trên thiết bị cho thấy giao diện Symbian thật và thao tác được.

## Cơ sở kỹ thuật

Nguồn upstream chính thức được khảo sát tại commit `0d1831aa8444fea52958e6f98be4dc4f8463540c`:

- [`arm_utils.cpp`](https://github.com/EKA2L1/EKA2L1/blob/0d1831aa8444fea52958e6f98be4dc4f8463540c/src/emu/cpu/src/arm_utils.cpp) chọn Dyncom mặc định cho iOS.
- [`arm_dyncom_interpreter.cpp`](https://github.com/EKA2L1/EKA2L1/blob/0d1831aa8444fea52958e6f98be4dc4f8463540c/src/emu/cpu/src/dyncom/arm_dyncom_interpreter.cpp) dispatch lệnh guest qua `GOTO_NEXT_INST`; tại điểm này interpreter có `Reg[15]`, `Reg[0]` và `Reg[1]` trước khi chạy lệnh tiếp theo.
- [`arm_interface.h`](https://github.com/EKA2L1/EKA2L1/blob/0d1831aa8444fea52958e6f98be4dc4f8463540c/src/emu/cpu/include/cpu/arm_interface.h) không mang định danh process/thread trong trạng thái core.
- [`scheduler.cpp`](https://github.com/EKA2L1/EKA2L1/blob/0d1831aa8444fea52958e6f98be4dc4f8463540c/src/emu/kernel/src/scheduler.cpp) nắm `crr_thread` và process sở hữu khi chuyển context, rồi nạp context vào core.

Vì vậy, log CPU đơn lẻ không đủ chứng minh caller là Home. Thiết kế nối interpreter với scheduler bằng một callback quan sát tùy chọn: interpreter phát sự kiện chỉ tại PC đích; scheduler bổ sung định danh thread/process hiện hành.

## Điểm đích và luồng dữ liệu

Trên firmware hiện tại, địa chỉ runtime của `Cone.dll` là `0x806E8E68`; cộng offset `0x215E` cho PC đích `0x806EAFC6`. Đây là lệnh Thumb tại địa chỉ chẵn. Probe so khớp chính xác PC đã chuẩn hóa, không quét toàn bộ dải mã Cone. Nếu baseline FASTBUILD hoặc firmware cho base khác, phải dừng để xác minh lại địa chỉ; không mở rộng thành trace toàn CPU.

1. Scheduler chỉ cài callback khi profile DirectHome được chọn. Callback lấy thread/process đang chạy tại đúng thời điểm sự kiện và bảo đảm callback được gỡ trước khi scheduler/core bị hủy.
2. Dyncom kiểm tra PC tại ranh giới trước khi dispatch lệnh. Khi PC bằng `0x806EAFC6`, callback ghi thanh ghi trước thực thi; mọi PC khác chỉ chịu phép so khớp hẹp, không phát log.
3. Log callsite gồm PC tuyệt đối, module/offset, `r0`, `r1`, LR, SP, CPSR/TFlag, UID3/tên process, ID duy nhất process/thread và tên thread. Nếu không lấy được thread/process, ghi rõ `context=missing`; không đoán danh tính hoặc dereference con trỏ thiếu.
4. Thêm companion marker `[NBOOT2][DIRECTHOME_TFX_SESSION]` riêng, chỉ bật ở profile DirectHome, cho các pha request/missing/found và ghi cùng process/thread ID. Giữ nguyên marker `TFX_SESSION` chung hiện có. Kết quả `KErrNotFound` và đường gọi gốc không đổi. Ghép sự kiện bằng process/thread ID và thứ tự log.

## Lựa chọn kiến trúc

Đã chọn callback tùy chọn trên abstraction `arm::core`, được scheduler sở hữu và Dyncom gọi tại PC chính xác. Cách này giữ nguồn định danh ở kernel scheduler, thay vì để interpreter phụ thuộc trực tiếp vào kernel.

Hai cách không chọn:

- Chỉ log từ interpreter: có `PC/r0/r1` nhưng thiếu PID/TID nên không chứng minh được Home là caller.
- Chỉ log tại `CreateSession`: biết process/thread và kết quả TFX nhưng không chụp được `r0/r1` tại `Cone.dll+0x215E`.

## Dữ liệu log và an toàn

Marker callsite dự kiến: `[NBOOT2][DIRECTHOME_TFX_CALLSITE]`. Marker phải ghi `behavior=OBSERVE_ONLY`, profile, core, PC/offset, `r0/r1` và định danh hiện hành. Companion `[NBOOT2][DIRECTHOME_TFX_SESSION]` ghi request, missing và found; marker `TFX_SESSION` chung hiện có không bị sửa.

Callback rỗng là no-op. Thiếu `crr_thread` hoặc process không được làm dừng guest. Tất cả log và phép kiểm tra đều nằm sau cổng DirectHome; không thêm đọc/ghi bộ nhớ guest, thay thanh ghi, thay PC, thay số lệnh hoặc can thiệp IPC. Patcher FASTBUILD phải từ chối nếu anchor thiếu hoặc không duy nhất, và phải idempotent.

## Kiểm thử và tiêu chí chấp nhận

- Test patcher xác nhận predicate chỉ khớp đúng PC, hook nằm trước khi chạy lệnh, lấy đúng `Reg[0]/Reg[1]`, và không đổi flow/control state.
- Test callback xác nhận thông tin process/thread lấy từ scheduler, profile khác DirectHome không cài/không phát probe, lifecycle gỡ callback an toàn và context thiếu không bị gán nhầm.
- Test TFX trace xác nhận companion marker chỉ phát trong DirectHome và cùng process/thread ID xuất hiện tại request/missing/found; `TFX_SESSION` chung, `KErrNotFound`, lời gọi completion và việc không tạo server vẫn nguyên vẹn.
- Test idempotence, anchor fail-closed, manifest order và regression chain DirectHome.
- Khi triển khai, chạy test tập trung, full suite và `ci/fastbuild1_manifest.py validate`; FASTBUILD phải dùng đúng nhánh DirectHome, build iOS thành công, binary có marker probe và không mang build ID B99. Lượt này chưa dispatch build.
- Trên thiết bị, cần thấy hit tại PC đích với định danh Home và đối chiếu cùng ID ở companion `DIRECTHOME_TFX_SESSION`. Nếu không hit hoặc context thiếu, kết quả là chưa đủ bằng chứng, không được suy ra Home đã gọi callback.

## Rủi ro và giới hạn

- FASTBUILD dùng upstream tree được khôi phục từ cache B28, trong khi source GitHub đã khảo sát ở commit khác. Patcher phải kiểm tra source thật trong cây cache tại lúc apply; nếu khác cấu trúc thì dừng thay vì sửa theo anchor gần giống.
- PC cố định phụ thuộc base Cone của firmware v60.0.003. Firmware không đổi trong thử nghiệm; nếu địa chỉ runtime khác, cập nhật target chỉ sau khi có bằng chứng log.
- Callback thêm một nhánh PC-check trong Dyncom và một callback tùy chọn ở core. Build này chỉ nhằm chẩn đoán; không suy rộng kết quả hiệu năng hoặc khả năng boot.
- Bằng chứng cùng PID/TID cho thấy hai sự kiện thuộc cùng thread, nhưng không tự nó chứng minh lệnh callsite là nguyên nhân duy nhất của lần `CreateSession`; cần đọc trình tự log cùng `r0/r1` và kết quả request.

## Ngoài phạm vi

- Sửa nguyên nhân Home chưa visible, khởi chạy TfxServer, đổi firmware hoặc thay đổi quy trình sáu dịch vụ.
- Trace toàn bộ lệnh CPU, thêm stub/fake server, bỏ qua lỗi, sửa kết quả `CreateSession`, thay hành vi Native Boot hoặc thay đổi B99.
- Kết luận Home thành công chỉ từ việc thấy process chạy, callsite hit hay marker TFX.
