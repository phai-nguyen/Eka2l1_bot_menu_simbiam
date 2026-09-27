# Thiết kế COMPATBOOT1: vào thẳng màn hình Home

Trạng thái: tài liệu thiết kế để duyệt; chưa bắt đầu triển khai.

## Mục tiêu

Tạo một đường khởi động tương thích riêng để thử vào màn hình Home/Idle của Nokia 5800 RM-356 nhanh hơn. Sau khi hàng rào sẵn sàng của sáu dịch vụ giao diện hiện có đạt yêu cầu, đường này sẽ khởi chạy ailaunch.exe thật từ firmware tại Z:\sys\bin\ailaunch.exe.

Đây là đường chạy riêng, không chứng minh chuỗi khởi động firmware bình thường đã thành công.

## Mốc nền và cách ly

- Mã nguồn nền: b14804a4ccd594d837496e2f106c4b5e8a2cdb10 (B99).
- Nhánh đề xuất: codex/compatboot1-directhome.
- Nhánh không-bypass và artifact B99 được giữ nguyên để làm bản đối chứng. Không gộp thay đổi này vào B99 hoặc PR #7.
- Native Boot vẫn là chế độ mặc định. Đường mới chỉ chạy khi người dùng chọn rõ profile CompatBoot riêng.
- Chỉ profile thử nghiệm này bỏ qua chính sách khởi động firmware thông thường và không chạy chuỗi khởi động PhoneUI bình thường. Không sửa cách Native Boot xử lý lỗi, panic hoặc kết quả khởi động PhoneUI.

## Luồng khởi động đề xuất

1. Khởi chạy EKA2L1 và nạp firmware RM-356 cùng bộ tài nguyên như B99.
2. Chọn rõ profile CompatBoot Direct Home; không tự bật profile này trong Native Boot.
3. Chờ đủ sáu dịch vụ nền giao diện hiện có: FileServer, FBS, WindowServer, CenRep, AppArc và AknCapServer. Không khởi chạy đích trước khi hàng rào báo sẵn sàng.
4. Dùng bộ nạp tiến trình của máy khách để chạy ailaunch.exe thật trong firmware tại Z:\sys\bin\ailaunch.exe. Không tự vẽ hoặc thay thế bằng giao diện Home Nokia phía ứng dụng iOS.
5. Giữ nguyên và ghi nhận lỗi khởi chạy của tiến trình đích; xác định thành phần phụ thuộc đầu tiên còn thiếu, leave, panic hoặc lỗi bộ nạp. Không âm thầm bỏ lỗi và không tự chuyển sang Menu3 trong probe Direct Home đầu tiên.

Đường B99 hiện đã có chế độ CompatBoot, hàng rào sáu dịch vụ và probe chạy Menu3 thật. Đề xuất này thêm một profile đích Direct Home riêng, không đổi đích của B99 và không đổi hành vi Native Boot.

## Log và cách xử lý lỗi

Dùng mã nhận diện build/track riêng cho nhánh thử; tuyệt đối không gắn nhãn B99. Giữ các kiểm tra xác nhận không có dấu bypass B88/B89. Bổ sung log có phạm vi hẹp để liên kết việc chọn profile, kết quả hàng rào, lần khởi chạy và kết quả của đích, cùng lỗi đầu tiên thuộc đích.

Các marker đề xuất:

- [COMPATBOOT][MODE] profile=direct_home
- [COMPATBOOT][BARRIER_READY] services=...
- [COMPATBOOT][BARRIER_TIMEOUT] missing=...
- [COMPATBOOT][TARGET_LAUNCH] path=Z:\sys\bin\ailaunch.exe result=...
- [COMPATBOOT][FIRST_FAILURE] source=... target=ailaunch.exe ...
- [COMPATBOOT][TARGET_VISIBLE] target=ailaunch.exe — chỉ ghi khi có bằng chứng thật về cửa sổ/bề mặt hiển thị của máy khách.

Nếu hết thời gian chờ hàng rào, không khởi chạy đích. Nếu đích lỗi, phải giữ lỗi đó quan sát được; probe ban đầu không được chuyển đổi panic, sửa trạng thái thành công, bịa trạng thái hệ thống, thay resource, đổi firmware hoặc thêm stub dịch vụ diện rộng.

## Tiêu chí chấp nhận

### Build và cách ly

- Kiểm thử hợp đồng xác nhận Direct Home là chế độ tùy chọn; Native Boot vẫn mặc định và giữ nguyên hành vi PhoneUI/SYSSTART.
- Profile đã chọn phải chờ đủ sáu dịch vụ trước khi khởi chạy; probe này chỉ chạy ailaunch.exe thật từ firmware.
- Mã nhận diện build là duy nhất cho thử nghiệm; các bất biến B99 và kiểm tra không có bypass B88/B89 vẫn được giữ.
- FASTBUILD, biên dịch iOS, kiểm tra binary và đóng gói IPA chưa ký đều đạt.

### Bằng chứng trên thiết bị

- Log thiết bị nhận diện đúng build thử nghiệm, ghi nhận hàng rào và lần khởi chạy ailaunch.exe.
- Màn hình Home/Idle Symbian thật phải hiện và nhận thao tác chạm/nhập liệu. Chỉ thấy tiến trình còn sống, một lần chuyển trạng thái hoặc marker khởi chạy thì chưa đủ.
- Giữ lại log và artifact B99 để so sánh. Không thay firmware.

## Rủi ro và điểm cần xác minh khi triển khai

- Hàng rào sáu dịch vụ chưa chắc đã đủ cho AILaunch; cần quan sát thành phần phụ thuộc đầu tiên còn thiếu thay vì đoán.
- Trước khi triển khai, xác minh danh tính executable AILaunch trong firmware, quy ước khởi chạy và cách chứng minh cửa sổ/bề mặt hiển thị.
- Direct Home có thể thất bại dù Menu3 chạy được. Thử nghiệm này nhằm trả lời riêng câu hỏi đó; Menu3 là đích chẩn đoán độc lập, không phải phương án tự chuyển sang để tính là thành công.
- Nếu Direct Home chạy được, điều đó chứng minh đường tương thích tùy chọn hoạt động; không chứng minh chuỗi khởi động firmware bình thường đã hoàn tất.

## Ngoài phạm vi

- Sửa B99, artifact hoặc log B99, hay hành vi không-bypass của B99.
- Đổi firmware, gộp PR #7 hoặc thay đổi Native Boot mặc định.
- Vẽ giao diện Nokia giả, tuyên bố thành công khi chưa có bằng chứng tương tác trên thiết bị, hoặc bỏ qua/che giấu lỗi của đích trên diện rộng.
- Thêm stub dịch vụ hoặc ảo hóa trạng thái trước khi có thành phần phụ thuộc cụ thể được chứng minh và được duyệt riêng.
