# B99 — hướng dẫn kiểm tra trên iPhone

## Kết quả build

- FASTBUILD **#324** — thành công.
- Mã lần chạy: `36318399524`.
- Commit: `a82d31a2626f8bd77e8e4c83ba57069b79ff252f`.
- Artifact IPA: [Tải gói IPA B99](https://github.com/phai-nguyen/Eka2l1_bot_menu_simbiam/actions/runs/36318399524/artifacts/10931945136).
- SHA-256 của file IPA: `1fe03ed0b2716066932a9a21c75e283f87196211453f1e40914f5338b5a78f70`.
- Gói là IPA chưa ký; artifact ZIP được giữ đến **2026-10-11 12:18 UTC**.

## Điều đã được xác nhận

- Mốc B28 và tất cả regression trong manifest đều đạt; bước biên dịch iOS, kiểm tra binary và đóng gói IPA đều thành công.
- Binary có dấu nhận diện `[NBOOT2][BUILD_ID] build=B99 track=H2_COMPATBOOT1_NOBYPASS1`.
- Cổng binary đã kiểm tra và xác nhận không có dấu B88 `[NBOOT2][PHONEUI_CONE14_CONTINUE_B88]` hoặc B89 `[NBOOT2][PHONEUI_FAILSTATE_BYPASS_B89]`.
- B99 chỉ bổ sung dấu nhận diện log ở đầu phiên giả lập. NativeBoot mặc định và các kiểm tra PhoneUI vẫn được giữ nguyên.
- Chưa thử B99 trên iPhone; chưa biết phiên này có tới Home Screen hay không.

## Cài và thử

1. Mở link artifact trên iPhone và đăng nhập GitHub nếu được yêu cầu.
2. Tải file ZIP, chọn lưu vào ứng dụng **Tệp (Files)**, rồi chạm ZIP để giải nén.
3. Cài file IPA bằng đúng công cụ ký/cài đã dùng cho các bản thử trước.
4. Giữ lại log B98. Cài B99 đè lên ứng dụng hiện tại, mở ứng dụng và bắt đầu một phiên giả lập mới.
5. Thu log mới. Log hợp lệ phải có đầy đủ dấu `build=B99 track=H2_COMPATBOOT1_NOBYPASS1`.
6. Ghi lại: có hiện `Phone start-up failed` không; ứng dụng tự thoát hay bạn tự thoát; log có đủ hàng rào sáu dịch vụ và dấu chạy `menu3.exe` thật không; có thấy Home Screen Symbian thật và tương tác được không.
7. Gửi log mới và video nếu có. Không xóa log B98 và không đổi firmware trong lượt thử này.

Màn hình `Phone start-up failed` không được tính là Home Screen. Dấu `shutdown_done` đơn lẻ cũng không đủ để kết luận ứng dụng iPhone bị crash.
