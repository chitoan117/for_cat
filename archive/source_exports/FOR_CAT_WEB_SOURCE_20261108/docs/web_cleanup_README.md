# Cập nhật giao diện FOR_CAT — 06/11/2026

Đã triển khai lên http://192.168.1.6:8000/app và đồng bộ 7 tệp giao diện cùng 5 tệp kiểm thử về `D:/DA_KT_NC/feeder_demo`.

## Thay đổi

- Trang tổng quan gọn hơn: trạng thái kết nối, nhận diện mèo, mức dự trữ, nút cho ăn, bữa tiếp theo, camera và hoạt động gần đây.
- Bỏ nhãn mã nội bộ và các đoạn hướng dẫn dài trên màn hình chính; giữ thông tin chuyên sâu trong phần mở rộng Chi tiết.
- Rút gọn trang Cho ăn, Lịch sử, Hệ thống và Cài đặt; thống nhất màu, thẻ, biểu tượng và trạng thái tiếng Việt.
- Dữ liệu chưa có tiếp tục hiển thị là chưa có dữ liệu. Yêu cầu đã gửi tới ESP32 không được coi là đã cấp thức ăn thành công.
- Dùng tài nguyên khởi động và thư mục phông chữ theo phiên bản để tránh giao diện/phông cũ trong cache.

## Phạm vi giữ nguyên

Không sửa firmware ESP32, servo, loadcell, backend Jetson, hiệu chuẩn, cơ sở dữ liệu hoặc nguyên lý cho ăn/bơm nước. Các tệp mô hình, kết nối API, camera controller, bộ lưu yêu cầu và lịch ăn giữ nguyên từng byte; đối chiếu trong `unchanged_logic.json` và `source_sync.json`.

Không gửi lệnh cho ăn, bơm, chỉnh hiệu chuẩn hay sửa lịch trong quá trình kiểm tra UI. Máy chủ xem trước chỉ cho phép HTTP đọc và luồng trạng thái.

## Kiểm tra

- Flutter analyze: không có lỗi/cảnh báo.
- Toàn bộ bộ kiểm thử: 82 đạt, 3 bài bỏ qua có sẵn.
- Sau chỉnh chiều cao thẻ: chạy lại 29 bài UI, tất cả đạt.
- Bài responsive kiểm tra cả 5 tab ở bề rộng 320, 390, 768 và 1280.
- Kiểm tra trực quan trên trình duyệt ở 390 × 844 và 800 × 480; kiểm tra bản thật sau triển khai. Đã mở hộp xác nhận trong bản xem trước rồi hủy.
- Bản thật kết nối dữ liệu; phiên kiểm tra mới không có lỗi/cảnh báo console. Ảnh `after.png` chụp trên địa chỉ Jetson thật.
- HTTP kiểm tra trang, JS, CanvasKit, phông chữ và marker; toàn bộ tệp triển khai khớp SHA-256 trong `web_manifest.json`.
- API, bridge ESP32 và AI vẫn active với PID giữ nguyên trong lúc triển khai; không khởi động lại dịch vụ.
- CanvasKit và phông chữ được đóng gói cục bộ. Không ngắt mạng thực tế trong phiên này.

## Lưu trữ và khôi phục

- Thư mục đang phục vụ trên Jetson: `/home/toan/for_cat/.native-build/flutter/four_ultrasonic_20261027_r2`.
- Bản sao đầy đủ trước thay đổi: `/home/toan/for_cat/.native-build/flutter/four_ultrasonic_20261027_r2.before_cleanup_20261106`.
- Biên bản Jetson: `/home/toan/for_cat/evidence/web_cleanup_20261106/deployment_result.json`.
- Mã nguồn làm việc và bản trước sửa ở `app/` và `before/`. Khóa gói Flutter giữ nguyên.
- Bản release đóng gói: `web_cleanup_20261106.tar.gz`; bước `package_web.py` thêm tên tài nguyên theo hash sau Flutter build.
- JS chính SHA-256: `a7c6f3902bc30016068d1dabe90b87027208ab27d73369e23974e386351f9f5a`.

Khi cần khôi phục, đổi tên thư mục hiện tại sang tên lưu riêng rồi đổi tên thư mục `.before_cleanup_20261106` về đúng đường dẫn đang phục vụ. Giữ cả hai bản, không xóa dữ liệu. Không chạy lại script triển khai vào thư mục backup đã tồn tại.
