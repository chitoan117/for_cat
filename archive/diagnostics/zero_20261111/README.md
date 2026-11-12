# Đặt chén rỗng về0g — 11/11/2026

Chủ máy xác nhận chén rỗng, đúng vị trí, không tay/mèo/vật tì và giữ nguyên. Đã gửi đúng lệnh `t` (Retare/tarePreservingFactor), không dùng `tare` xóa hệ số hoặc nhập mốc cũ.

- Trước chỉnh,8 mẫu−2,25/−2,36/−2,35/−2,27/−2,32/−2,20/−2,17/−2,20g, đủ ổn định.
- ACK mới `hx_cal`, operation=rezero,ok=true,saved=true; **tare_counts mới−698623,0**. Hệ số đúng trước đó **−0,000945082600219258g/count**; ACKin12chữsố −0,000945082600219.
- Chủ máy sau đó xác nhận **“đã đúng rồi” trên OLED**, rồi chuyển yêu cầu sang sửa nút manual.
- Khung nhất quán sau chỉnh: signed−0,08g, display0,0g, tare−698623, hệ số−0,000945082600219258. Trong lượt đọc trực tiếp UART sau đó, HXraw−698467 với mốc này và manualbaseline−0,29g; không lấy lại zero lần hai.
- Chế độ trước chỉnh được khôi phục `start`. Không nạp firmware, không đổi servo/35g/pump hoặc mốc dự trữ.

## Lỗi kiểm tra và kết nối quan sát được

Script kiểm tra đầu tiên dừng ở so sánh hệ số trước/sau: một khungUART trước chỉnh ghi−0,002945082600219258, khác hệ số đúng−0,000945082600219258 đã xác minh. Source `tarePreservingFactor()` chỉ chép calibration và đổi tare; ACK và khung sau chỉnh vẫn cho đúng hệ số. Dữ liệu này **gợi ý khungUART bị sai**, chưa xác định nguyên nhân vật lý; không dùng giá trị−0,002945… để sửa/import lại calibration.

UART có nhiều khung lỗi và giai đoạn stale, số cân kiểm tra liên tục sau chỉnh chưa đạt do chỉ nhận một khung nhất quán trong32s. Không khẳng định đường truyền đã ổn định hoặc số đo luôn chính xác0,000g. Mốc đã lưu NVS và OLED được owner xác nhận đúng; lỗi manual đang xử lý riêng tại `../manual_20261111`.

Remote evidence trước khi mấtSSH: `/home/toan/for_cat/evidence/zero_20261111/zero_1794373816.json`, `saved_zero_verification.json`. Chưa tải được bản đầy đủ về laptop vì mạng đổi trong lúc làm; không có lệnh zero nào khác gửi sau ACK này.

**Mốc−698623 mới thay thế−700986,7333 trong các ghi chú cũ.** Không dùng mốc cũ trong script nạp hoặc khôi phục sau này. Gain vẫn−0,000945082600219258. Sourcecanonical và firmware vẫn app581… khi kết thúc phần trừ bì.
