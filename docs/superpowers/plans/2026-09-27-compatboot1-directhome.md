# Kế hoạch triển khai COMPATBOOT1 Direct Home

> **Dành cho người thực hiện:** BẮT BUỘC dùng tiểu kỹ năng `superpowers:executing-plans` hoặc `superpowers:subagent-driven-development` để triển khai từng nhiệm vụ; đánh dấu từng bước bằng ô `- [ ]`.

**Mục tiêu:** Thêm lựa chọn CompatBoot riêng khởi chạy ailaunch.exe thật sau hàng rào sáu dịch vụ, đồng thời giữ nguyên B99 và Native Boot mặc định.

**Kiến trúc:** Bổ sung chế độ đích Direct Home bên cạnh Native Boot và probe Menu3 đang có. Dùng lại hàng rào dịch vụ, bộ nạp tiến trình và cơ chế chẩn đoán CompatBoot hiện tại; chỉ đổi executable đích theo profile. Định danh build riêng và các kiểm tra FASTBUILD bảo đảm log/IPA không bị nhầm với B99 hoặc chứa bypass B88/B89.

**Công nghệ:** Bản vá nguồn Python của FASTBUILD, Objective-C++/C++ trong upstream EKA2L1, kiểm thử hợp đồng bằng unittest, GitHub Actions FASTBUILD, firmware RM-356.

**Thiết kế:** `docs/superpowers/specs/2026-09-27-compatboot1-directhome-design.md`

## Ràng buộc chung

- Mã nguồn nền là `b14804a4ccd594d837496e2f106c4b5e8a2cdb10` (B99).
- Làm trên nhánh riêng `codex/compatboot1-directhome`; không sửa hoặc gộp vào B99 hay PR #7.
- Native Boot vẫn là chế độ mặc định; Direct Home chỉ chạy khi được chọn rõ.
- Chỉ profile Direct Home bỏ qua chính sách khởi động firmware thông thường và chuỗi PhoneUI bình thường; không sửa hành vi lỗi/panic của Native Boot.
- Chờ đủ FileServer, FBS, WindowServer, CenRep, AppArc và AknCapServer trước khi chạy đích.
- Đích Direct Home duy nhất là ailaunch.exe thật tại `Z:\sys\bin\ailaunch.exe`; probe đầu tiên không tự chuyển sang Menu3 khi thất bại.
- Giữ các kiểm tra không có bypass B88/B89; không đổi firmware, không vẽ UI giả, không thêm stub hoặc ảo hóa trạng thái khi chưa có bằng chứng.
- Chỉ xác nhận Home/Idle thành công khi thấy UI Symbian thật và tương tác được trên thiết bị.

## Những điểm cần kiểm soát khi rà soát

- **Native Boot bị ảnh hưởng ngoài ý muốn:** kiểm thử chọn Native Boot phải xác nhận vẫn gọi đường khởi chạy gốc, không bật profile CompatBoot.
- **Dịch vụ chưa thật sự sẵn sàng:** với từng dịch vụ trong danh sách sáu dịch vụ và trường hợp tiến trình còn sống nhưng server chưa sẵn sàng, barrier không được mở sớm.
- **Hết thời gian chờ barrier:** báo chính xác dịch vụ còn thiếu và không spawn ailaunch.exe.
- **AILaunch lỗi khi tạo/chạy:** log kết quả lỗi, chỉ thử một lần và không âm thầm fallback sang Menu3.
- **Đánh dấu nhầm UI/nhầm profile:** marker TARGET_VISIBLE chỉ áp dụng cho cửa sổ ailaunch.exe thật; các trace đặc thù Menu3 không được gắn nhầm cho Direct Home.
- **Nhầm IPA hoặc log với B99:** build ID Direct Home phải riêng biệt; FASTBUILD yêu cầu ID mới và từ chối binary mang ID B99 hoặc marker bypass B88/B89.

---

### Nhiệm vụ 1: Thêm profile Direct Home tách biệt ở UI và bridge

**Tệp:**
- Sửa: `apply_nativeboot2_compatboot1_menuprobe1.py`
- Sửa: `test_nativeboot2_compatboot1_menuprobe1.py`
- Tạo: `test_nativeboot2_compatboot1_directhome1.py`

**Giao diện:**
- Khai báo `eka2l1::ios::bridge::compatboot_target` với `menu3_probe = 1` và `direct_home = 2`.
- Khai báo bridge `bool start_compat_boot(compatboot_target target)`; giữ `start_native_phone()` làm đường Native Boot.
- Lưu loại đích tạm thời trong trạng thái runtime CompatBoot: `0=none`, `1=menu3_probe`, `2=direct_home`; không serialize vào cấu hình người dùng.
- Menu Emulator hiển thị riêng Native Boot, CompatBoot Menu Probe hiện có và CompatBoot Direct Home. Nhãn Direct Home được Việt hóa thành “CompatBoot vào Home”.
- Phương thức khởi động chung ghi nhận duy nhất lựa chọn mode và gọi đúng bridge; không để mode tồn tại sau rollback/dừng.

- [ ] **Bước 1: Viết kiểm thử thất bại trước** trong test mới cho ba lựa chọn, mode Direct Home chỉ bật khi người dùng chọn, Native Boot vẫn mặc định, và trạng thái được xóa khi khởi động thất bại/dừng.
- [ ] **Bước 2: Chạy kiểm thử tập trung để xác nhận thất bại** vì chưa có target enum, bridge và lựa chọn Direct Home.

  Chạy: `python3 -m unittest test_nativeboot2_compatboot1_directhome1.py -v`
  Mong đợi: FAIL ở các assertion về lựa chọn Direct Home/bridge và trạng thái mode.
- [ ] **Bước 3: Cập nhật patcher UI/bridge/state** theo giao diện đã chốt; giữ nguyên lựa chọn và luồng Menu3 hiện có, thêm lựa chọn Direct Home và reset mode khi rollback/dừng.
- [ ] **Bước 4: Chạy test Direct Home và test CompatBoot hiện có**.

  Chạy: `python3 -m unittest test_nativeboot2_compatboot1_directhome1.py test_nativeboot2_compatboot1_menuprobe1.py -v`
  Mong đợi: PASS; Menu3 và Native Boot vẫn giữ hợp đồng cũ.
- [ ] **Bước 5: Commit** phần profile UI/bridge/state và các kiểm thử.

### Nhiệm vụ 2: Chạy ailaunch.exe sau barrier và giữ trace đúng phạm vi

**Tệp:**
- Sửa: `apply_nativeboot2_compatboot1_menuprobe1.py`
- Sửa: `test_nativeboot2_compatboot1_directhome1.py`
- Sửa: `apply_nativeboot2_b96_estorleaveexports1.py`
- Sửa: `test_nativeboot2_b96_estorleaveexports1.py`

**Giao diện:**
- Hàm kiểm tra barrier dùng trạng thái target đã chọn; chỉ chạy khi toàn bộ sáu dịch vụ sẵn sàng.
- Target Direct Home dùng đường dẫn `Z:\sys\bin\ailaunch.exe`; Menu Probe tiếp tục dùng `Z:\sys\bin\menu3.exe`.
- Mỗi profile chỉ spawn một lần. Cả lỗi tạo tiến trình và lỗi `run()` đều ghi target/path/result; không fallback.
- Marker TARGET_VISIBLE phải khớp UID3 của target đã spawn và bằng chứng WindowGroup vừa visible vừa physically seen.
- Trace có tên MENU3_LEAVE5 chỉ được phép phát trong profile Menu3; Direct Home dùng marker lỗi target chung.

- [ ] **Bước 1: Viết kiểm thử thất bại trước** cho từng dịch vụ chặn barrier, tiến trình sống nhưng server chưa sẵn sàng, timeout, target path, one-shot, lỗi create/run không fallback và điều kiện TARGET_VISIBLE.
- [ ] **Bước 2: Chạy test để xác nhận thất bại**.

  Chạy: `python3 -m unittest test_nativeboot2_compatboot1_directhome1.py -v`
  Mong đợi: FAIL ở các assertion target/barrier/timeout/visibility chưa được hỗ trợ.
- [ ] **Bước 3: Viết phần chọn target trong patcher**: giữ nguyên kiểm tra sáu dịch vụ và deadline; khi barrier đạt, chọn đúng executable từ target mode; ghi UID3 của tiến trình đích; không gọi launcher lần hai.
- [ ] **Bước 4: Giới hạn trace Menu3** để không gắn nhãn Menu3 cho leave của AILaunch; giữ nguyên kết quả leave và hành vi lỗi của cả hai target.
- [ ] **Bước 5: Chạy kiểm thử Direct Home, Menu3 và B96**.

  Chạy: `python3 -m unittest test_nativeboot2_compatboot1_directhome1.py test_nativeboot2_compatboot1_menuprobe1.py test_nativeboot2_b96_estorleaveexports1.py -v`
  Mong đợi: PASS; đủ sáu service mới mở barrier, timeout không spawn, AILaunch lỗi không fallback, marker visible cần đúng UID/cửa sổ.
- [ ] **Bước 6: Commit** thay đổi barrier/target/trace sau khi các test tập trung đạt.

### Nhiệm vụ 3: Định danh Direct Home và tích hợp FASTBUILD

**Tệp:**
- Tạo: `apply_nativeboot2_compatboot1_directhomefingerprint1.py`
- Tạo: `test_nativeboot2_compatboot1_directhomefingerprint1.py`
- Sửa: `ci/fastbuild1_manifest.txt`
- Sửa: `test_fastbuild1_manifest.py`
- Sửa: `.github/workflows/build-ios-nativeboot2-current-fast.yml`
- Sửa: `test_fastbuild1_workflows.py`
- Giữ nguyên: `ci/fastbuild1_reject_phoneui_bypass_markers.sh` và mọi kiểm tra B88/B89 hiện có.

**Giao diện:**
- Runtime marker duy nhất cho nhánh thử: `[NBOOT2][BUILD_ID] build=COMPATBOOT1_DIRECTHOME1 track=H2_COMPATBOOT1_DIRECTHOME1`.
- Bản vá nhận đúng marker B99 do manifest tạo, thay bằng marker Direct Home tại điểm bắt đầu phiên; từ chối anchor thiếu/nhiều hoặc marker đặt sai chỗ.
- FASTBUILD yêu cầu marker Direct Home, từ chối marker B99 trong binary thử nghiệm và tiếp tục từ chối dấu bypass B88/B89.
- Manifest chạy patcher nhận diện Direct Home sau patcher nhận diện B99; test Direct Home được đăng ký trong regression chain.

- [ ] **Bước 1: Viết test fingerprint thất bại trước** cho chèn đúng một lần, chạy lại idempotent, anchor thiếu/không duy nhất, thay marker B99 và không để marker Direct Home xuất hiện ngoài điểm khởi chạy.
- [ ] **Bước 2: Chạy test mới và xác nhận thất bại**.

  Chạy: `python3 -m unittest test_nativeboot2_compatboot1_directhomefingerprint1.py -v`
  Mong đợi: FAIL vì patcher chưa tồn tại.
- [ ] **Bước 3: Tạo patcher fingerprint và test**; giữ tên/đường dẫn B99 ở lịch sử, chỉ đổi marker trong binary nhánh Direct Home.
- [ ] **Bước 4: Đăng ký cặp patcher/test vào manifest** và thêm kiểm thử manifest để khóa đúng thứ tự sau B99, cùng regression Direct Home.
- [ ] **Bước 5: Cập nhật cổng workflow** để yêu cầu marker Direct Home chính xác, từ chối marker B99 và tiếp tục gọi verifier cấm bypass B88/B89.
- [ ] **Bước 6: Chạy kiểm thử FASTBUILD cục bộ**.

  Chạy: `python3 -m unittest test_nativeboot2_compatboot1_directhomefingerprint1.py test_nativeboot2_compatboot1_directhome1.py test_nativeboot2_compatboot1_menuprobe1.py test_nativeboot2_b96_estorleaveexports1.py test_fastbuild1_manifest.py test_fastbuild1_workflows.py -v`
  Mong đợi: PASS; manifest hợp lệ, target/profile đúng và các marker kiểm soát chính xác.
- [ ] **Bước 7: Commit** fingerprint, manifest và workflow sau khi test đạt.

### Nhiệm vụ 4: Xác minh FASTBUILD và chuẩn bị lượt thử thiết bị

**Tệp:**
- Cập nhật sau khi có kết quả: `docs/handoff/NEWCHAT-COMPATBOOT1-DIRECTHOME1-2026-09-27.md`
- Tạo sau khi có kết quả thiết bị: `docs/handoff/history/COMPATBOOT1-DIRECTHOME1-DEVICE1.md`

**Giao diện:**
- Báo cáo build ghi commit, workflow run, artifact và SHA-256 IPA.
- Báo cáo thiết bị phân biệt rõ “đã spawn”, “đã visible” và “Home/Idle tương tác được”; không suy diễn từ marker đơn lẻ.
- B99 artifact và log của nó tiếp tục là đối chứng; firmware không thay đổi.

- [ ] **Bước 1: Chạy toàn bộ kiểm thử/manifest cục bộ**.

  Chạy: `python3 -m unittest discover -p 'test_*.py'`, sau đó `python3 ci/fastbuild1_manifest.py validate .`
  Mong đợi: test đạt (ghi rõ test upstream-dependent nào bị bỏ qua); manifest hợp lệ.
- [ ] **Bước 2: Dispatch FASTBUILD trên nhánh codex/compatboot1-directhome**; xác nhận bootstrap B28, regressions, biên dịch iOS, audit binary, cổng B88/B89, đóng gói IPA và tải artifact đều hoàn tất.
- [ ] **Bước 3: Ghi handoff build** với marker Direct Home, run ID, artifact ID, SHA-256 và giới hạn rằng build xanh chưa chứng minh Home hoạt động.
- [ ] **Bước 4: Sau khi cài trên cùng firmware RM-356**, chọn “CompatBoot vào Home”, thu log/video mới và giữ nguyên log/artifact B99 để đối chiếu.
- [ ] **Bước 5: Chỉ ghi đạt Home khi video thấy Home/Idle Symbian thật và thao tác được**; nếu không, phân loại theo barrier timeout, loader/create/run, dependency đầu tiên hoặc thiếu WindowGroup visibility, rồi ghi vào handoff mà không thêm shim trước khi duyệt.

---

## Thứ tự phụ thuộc

Nhiệm vụ 1 tạo lựa chọn và trạng thái target; Nhiệm vụ 2 dựa trên trạng thái đó để chọn AILaunch sau barrier. Nhiệm vụ 3 khóa định danh/manifest/workflow cho chính nhánh Direct Home. Nhiệm vụ 4 xác minh chuỗi build rồi mới chuyển sang kiểm thử thiết bị. Không nhiệm vụ nào sửa B99 hoặc chạy workflow trên nhánh B99.

## Hướng thực hiện đề xuất

Các nhiệm vụ 1–3 cùng phụ thuộc vào một patcher FASTBUILD và fixture của cùng luồng CompatBoot, nên nên được triển khai tuần tự trong một phiên bởi một người thực hiện, sau đó có một lượt review độc lập toàn nhánh. Nhiệm vụ 4 chỉ bắt đầu sau khi các kiểm thử cục bộ đạt.
