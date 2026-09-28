# Recovery Checkpoints

Mục tiêu của thư mục này là cho phép khôi phục dự án nếu cuộc trò chuyện ChatGPT bị lỗi trước khi kịp tạo HANDOFF đầy đủ.

## Nguồn sự thật

- Repository: `phai-nguyen/Eka2l1_bot_menu_simbiam`
- Workstream hiện tại: `codex/compatboot1-directhome`
- `docs/checkpoints/LAST_STATE.md`: checkpoint kỹ thuật do người làm dự án cập nhật khi đạt mốc quan trọng.
- `docs/checkpoints/AUTO_LAST_COMMIT.md`: black-box recorder do GitHub Actions tự cập nhật sau mỗi push vào nhánh DirectHome.
- `docs/handoff/CURRENT.md`: HANDOFF dài hạn khi có.
- Git history + GitHub Actions + device logs: bằng chứng cuối cùng nếu HANDOFF thiếu.

## Quy tắc khôi phục

Khi mở cuộc trò chuyện mới sau sự cố:

1. Đọc `docs/checkpoints/LAST_STATE.md`.
2. Đọc `docs/checkpoints/AUTO_LAST_COMMIT.md` nếu có.
3. Kiểm tra HEAD thực tế của `codex/compatboot1-directhome`, PR đang mở và GitHub Actions gần nhất.
4. Đối chiếu log/device evidence mới nhất trước khi kết luận trạng thái runtime.
5. Không suy đoán rằng thay đổi local chưa push đã tồn tại trên remote.
6. Không sửa/merge nhánh B99 so sánh `codex/compatboot1-menuprobe2-nobypass` trừ khi người dùng yêu cầu rõ ràng.

## Câu lệnh khôi phục gợi ý

> Tiếp tục EKA2L1 từ docs/checkpoints/LAST_STATE.md và AUTO_LAST_COMMIT.md trên nhánh codex/compatboot1-directhome. Kiểm tra HEAD/Actions thực tế trước, giữ nguyên B99, rồi tiếp tục từ NEXT ACTION. Không nghiên cứu lại các mốc đã xác nhận.
