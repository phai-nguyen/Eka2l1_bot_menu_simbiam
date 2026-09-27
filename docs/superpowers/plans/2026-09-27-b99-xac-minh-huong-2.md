# Kế hoạch B99: xác minh build không bypass của hướng 2

> **Dành cho người triển khai:** Thực hiện từng bước trong kế hoạch và đánh dấu hoàn tất bằng ô kiểm (`- [ ]`).

**Mục tiêu:** Tạo và chạy thử một build hướng 2 có dấu nhận diện riêng, để làm rõ vì sao log B98 có các dấu B88/B89 dù hướng 2 được xây dựng để gỡ bypass.

**Cách làm:** Giữ nguyên hành vi khởi động hiện tại của nhánh hướng 2. Chỉ thêm một dấu log nhận diện build khi bắt đầu phiên giả lập. FASTBUILD phải xác nhận dấu nhận diện B99 có trong app và các dấu bypass B88/B89 không có. Chỉ xem log thiết bị là lượt B99 hợp lệ khi log mới có dấu nhận diện này.

**Công nghệ:** Kiểm thử và script Python, FASTBUILD manifest, GitHub Actions build iOS, `RootViewController.mm`, log chạy trên iPhone.

**Tài liệu gốc:** `docs/handoff/NEWCHAT-COMPATBOOT1-NOBYPASS1-2026-09-27.md`; bằng chứng cần làm rõ là log thiết bị B98 ngày 27-09-2026 và gói checkpoint B97 trên Google Drive.

## Ràng buộc chung

- Làm trên nhánh `codex/compatboot1-menuprobe2-nobypass` của repo cũ; giữ hướng 1 riêng ở repo mới `phai-nguyen/Eka2l1-nhanh-menuu3`.
- NativeBoot tiếp tục là mặc định. CompatBoot vẫn phải được chọn riêng, chờ đủ sáu dịch vụ nền, rồi mới thăm dò `menu3.exe` thật đúng một lần.
- Không thêm lại B88 xử lý riêng lỗi Telephone CONE 14 hoặc B89 đổi SYSSTART từ `116` sang `109`.
- Không đổi firmware, không bỏ qua lỗi PhoneUI và không thêm bản vá phỏng đoán.
- Không xem một dấu log, việc tiến trình được tạo hoặc màn hình lỗi/trắng là thành công. Thành công trên thiết bị vẫn cần tới Home/Menu Symbian thật và tương tác được.

## Những điểm cần kiểm soát khi rà soát

- **Cài nhầm IPA hoặc dùng log cũ:** log mới phải có đúng dấu nhận diện B99/H2.
- **B88/B89 bị đưa lại vào bản build:** kiểm thử và kiểm tra chuỗi trong binary phải phát hiện, làm FASTBUILD thất bại.
- **Dấu chẩn đoán vô tình đổi hành vi hoặc xuất hiện lặp:** kiểm thử xác nhận đây chỉ là một dòng log, ghi đúng một lần khi phiên giả lập bắt đầu.
- **Hàng rào dịch vụ hoặc lệnh chạy Menu3 bị ảnh hưởng:** giữ nguyên các kiểm thử hiện có cho sáu dịch vụ, chạy một lần và chẩn đoán Menu3.
- **Log tích lũy bị nhầm thành lượt B99:** lưu riêng log B98 trước; dùng dấu B99 và thời điểm khởi động để nhận diện log mới.

---

### Task 1 — Nhiệm vụ 1: Thêm dấu nhận diện runtime cho build B99 hướng 2

**Tệp liên quan:**
- Tạo: `apply_nativeboot2_b99_buildfingerprint1.py`
- Tạo: `test_nativeboot2_b99_buildfingerprint1.py`
- Sửa: `ci/fastbuild1_manifest.txt`
- Sửa: `test_fastbuild1_workflows.py`

**Giao diện:**
- Script áp dụng bản vá nhận đường dẫn thư mục upstream làm tham số duy nhất, theo cách FASTBUILD đang chạy các script hiện có.
- Script thêm đúng một dấu log tại điểm bắt đầu phiên giả lập iOS: `[NBOOT2][BUILD_ID] build=B99 track=H2_COMPATBOOT1_NOBYPASS1`.
- Kiểm thử xác nhận dấu này chỉ xuất hiện một lần, tại điểm bắt đầu phiên; không sửa trạng thái khởi động, xử lý panic, lệnh chạy ứng dụng hay dịch vụ.

- [ ] **Bước 1: Viết kiểm thử hợp đồng để thất bại trước**, kiểm tra dấu log được chèn đúng một lần tại điểm bắt đầu phiên và không đổi hành vi khởi động.
- [ ] **Bước 2: Chạy kiểm thử mới** trên fixture hiện có; xác nhận nó thất bại vì chưa có dấu B99.
- [ ] **Bước 3: Viết bản vá tối thiểu, có thể chạy an toàn nhiều lần**, trong `apply_nativeboot2_b99_buildfingerprint1.py`; báo lỗi nếu không tìm thấy hoặc tìm thấy nhiều điểm chèn phù hợp.
- [ ] **Bước 4: Đăng ký cặp script áp dụng/kiểm thử** trong `ci/fastbuild1_manifest.txt`, đồng thời yêu cầu FASTBUILD kiểm tra dấu B99.
- [ ] **Bước 5: Chạy lại kiểm thử tập trung và kiểm tra manifest**; cả kiểm thử dấu nhận diện và xác thực manifest phải đạt.

### Task 2 — Nhiệm vụ 2: Bắt FASTBUILD xác minh dấu B99 và việc gỡ bypass

**Tệp liên quan:**
- Sửa: `.github/workflows/build-ios-nativeboot2-current-fast.yml`
- Sửa: `test_fastbuild1_workflows.py`
- Dùng lại: `test_nativeboot2_b27_wservpanic13trace1.py`

**Giao diện:**
- Dùng bước kiểm tra chuỗi trong binary hiện có của FASTBUILD làm phép xác minh.
- Binary phải có dấu B99; đồng thời không được có `[NBOOT2][PHONEUI_CONE14_CONTINUE_B88]` hoặc `[NBOOT2][PHONEUI_FAILSTATE_BYPASS_B89]`.
- Kiểm thử B27 hiện có tiếp tục yêu cầu giữ xử lý panic gốc và lệnh ghi SYSSTART `prop->set_int(value)`.

- [ ] **Bước 1: Thêm kiểm thử workflow để thất bại trước**, yêu cầu dấu B99 có mặt và cả hai dấu bypass vẫn vắng mặt.
- [ ] **Bước 2: Chạy `python3 -m unittest test_fastbuild1_workflows.py -v`**; xác nhận kiểm thử mới thất bại trước khi sửa workflow.
- [ ] **Bước 3: Sửa bước kiểm tra binary của FASTBUILD** để yêu cầu dấu B99 chính xác, đồng thời giữ nguyên các kiểm tra cấm B88/B89.
- [ ] **Bước 4: Chạy kiểm thử workflow và B27**; chúng phải xác nhận dấu B99 có mặt, đồng thời giữ nguyên hành vi PhoneUI/SYSSTART gốc.

### Task 3 — Nhiệm vụ 3: Build, kiểm tra và thử B99 trên iPhone

**Tệp liên quan:**
- Cập nhật sau khi có kết quả: `docs/handoff/NEWCHAT-COMPATBOOT1-NOBYPASS1-2026-09-27.md`
- Tạo sau khi có kết quả: `docs/handoff/history/B99-DEVICE1.md`

**Giao diện:**
- Báo cáo FASTBUILD phải ghi commit, mã lần chạy, mã artifact và SHA-256 của IPA.
- Log thiết bị hợp lệ phải có dấu B99 và hành vi không bypass đúng dự kiến. Các dấu CompatBoot phải ghi riêng kết quả chờ sáu dịch vụ và chạy Menu3 thật.

- [ ] **Bước 1: Chạy kiểm tra cục bộ:** `python3 -m unittest discover -v`, `python3 ci/fastbuild1_manifest.py validate .`, `git diff --check`, cùng các kiểm thử tập trung B27/B99.
- [ ] **Bước 2: Chạy FASTBUILD từ nhánh hướng 2**; xác nhận các cổng kiểm tra, biên dịch iOS, kiểm tra binary, đóng gói IPA chưa ký và tạo artifact đều hoàn tất.
- [ ] **Bước 3: Ghi lại danh tính artifact** (mã lần chạy, mã artifact, SHA-256, commit) vào handoff B99 trước khi cài lên iPhone.
- [ ] **Bước 4: Cài đúng IPA đó đè lên app hiện tại**, dùng cùng firmware RM-356; giữ riêng các tệp B98 rồi thu một bộ log mới có dấu B99.
- [ ] **Bước 5: Phân loại lượt thử:** thiếu dấu B99 nghĩa là IPA/log không đúng hoặc đã cũ, lượt thử không hợp lệ; có dấu B99 nhưng vẫn có một trong hai dấu B88/B89 nghĩa là build không đạt hợp đồng; có dấu B99, không có bypass, và có log hàng rào/Menu3 thì lượt thử hướng 2 hợp lệ.
- [ ] **Bước 6: Ghi lại màn hình và cách thoát app**; không xem thông báo Phone start-up failed là Home Screen thành công, cũng không suy ra app iOS bị crash chỉ từ `shutdown_done`.

## Cách quyết định bước tiếp theo sau B99

- Nếu log B99 mới không có dấu B88/B89 nhưng vẫn hiện `Phone start-up failed`, ta đã xác minh được hướng 2 chạy đúng chế độ no-bypass; khi đó so sánh blocker còn lại với hướng 1.
- Nếu log có dấu B88/B89 cùng với dấu nhận diện B99, dừng thay đổi hành vi boot và kiểm tra manifest, binary đã build, cùng IPA đã cài.
- Nếu Home/Menu Symbian thật và tương tác được, ghi nhận đây là mốc Home Screen đầu tiên đạt yêu cầu; vẫn giữ nguyên các ràng buộc còn lại.
