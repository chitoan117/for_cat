# Trạng thái tại thời điểm sao lưu 12/11/2026

## Bản hiện tại

- Firmware offline R2 source5e5f39…; app đã nạp/readback f370aa4d8c3f473565a644b514e9ec15da45392d5f2c6221e7f2cbb4991cf789. NVS giữ nguyên trong lần nạp. Tare gần nhất−698623.0, gain−0.000945082600219258, chỉ là mốc của bo/cơ khí hiện tại.
- Manual có WAIT_MANUAL_HX tối đa3s để chờ mẫu cân, sau đó cấp mục tiêu35g, bảo vệ chờ khối lượng25s. R2 sửa nhánh fallback/schedule nhận trạng thái đang chờ cân.
- Servo GPIO6: mở1350µs/900ms, đóng1600µs/1450ms, dừng1500µs. Servo quay liên tục, vị trí theo thời gian, không có công tắc hành trình hoạt động; chưa có phản hồi vị trí.
- Đã thêm giữ nút5s xác nhận cửa đóng khi khóa, nhưng chủ máy báo thử thực tế **chưa gỡ được KIEM TRA CUA và không hiện GIU5S XACNHAN**. Cần đo GPIO21/kiểm tra nút và firmware đang chạy. Chưa xác minh sửa được cả nút PCB và nút web khi mất Wi-Fi.
- Bridge hiện tại a68b28… dùng `/dev/ttyTHS1`. Bulk-read169456… là candidate chưa triển khai.
- Water_control backend7d561…; root backend có các bản cập nhật water/reserve ngày11/11. Web artifact main.dart.js59ef40a45169aa5093c14704555e54c4c027b04a2f231ef30ad4892544fbae90.

## Bảng chân hiện tại

| Phần | GPIO ESP32-S3 |
|---|---|
| E1 HC-SR04 phát hiện đến gần | TRIG12/ECHO13 |
| E2 HC-SR04 hộp thức ăn | TRIG16/ECHO17 |
| D1 HC-SR04 chén nước | TRIG14/ECHO15 |
| D2 HC-SR04 bình dự trữ | TRIG18/ECHO19 |
| HX711 | DT4/SCK5 |
| OLED | SDA8/SCL9 |
| Servo | 6 |
| Pump qua module công suất, HIGH bật | 7 |
| Nút manual | 21, INPUT_PULLUP, nhấn nối GND |
| Jetson J6 physical8 TX → ESP RX | 41 |
| Jetson J6 physical10 RX ← ESP TX | 42 |
| Jetson J6 physical6 | GND chung |

PIR đã bỏ, GPIO11 không dùng. GPIO47 không dùng dừng cửa. Các trường protocol tên `JSN_SR04T_1/2` là tên legacy; cả4cảm biến thực đều HC-SR04. Một số metadata cũ còn ghi D2 ECHO10; bảng chân và firmware hiện tại là18/19, không đấu theo nhãn cũ. Tín hiệu UART/ECHO tới ESP phải phù hợp mức3.3V, không dùng UART để cấp5V.

## Nước và dự trữ

D1/pump chỉ hoạt động khi người dùng On, mặc địnhOff. Mốc bắt đầu≥5.7cm, dừng ở mẫu mới≤5.5cm, bảo vệ tối đa10s và dừng khi dữ liệu lỗi/cũ. Dừng motor không chặn được dòng nước tự chảy/siphon; phần ống/chống siphon vẫn phải xử lý cơ khí. E2 và D2 theo dõi dự trữ độc lập với On/OffD1. Mốc cạn đã lưu E2=14.06cm và D2=20.25cm; chưa có mốc đầy nên không khẳng định phần trăm khi chưa hiệu chuẩn.

## Giới hạn bản sao lưu

SSH LAN và Tailscale tới Jetson đều timeout lúc sao lưu. Source được gom từ export trực tiếp gần nhất và các thay đổi đã có bằng chứng triển khai trên laptop; chưa so lại với ổ Jetson trong phiên12/11. Dữ liệu vận hành/ảnh camera/dataset/credential/SDK/venv không đưa vào repo công khai. Thử dự phòng đã từng có servo mở/đóng, nhưng không lấy đó làm chứng nhận nguồn dự phòng hoặc độ chính xác35.000g trong mọi tình huống.
