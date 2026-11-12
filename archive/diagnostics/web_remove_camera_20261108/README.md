# Bỏ thẻ Camera trên web — 08/11/2026

Đã bỏ LiveCameraPanel và khoảng cách thừa khỏi OverviewPage, gỡ import không dùng. Giữ nguyên nhận diện CAT/DOG, camera AI trên Jetson, backend, firmware, servo, cân và lịch.

Source thực: D:/DA_KT_NC/feeder_demo/lib/user_pages.dart. Bản trước sửa: user_pages.before.dart. Cập nhật đúng kiểm thử Tổng quan có sẵn; các kiểm thử thành phần camera riêng giữ nguyên.

Flutter analyze file: không có lỗi. Build release thành công. Sáu kiểm thử trong live_camera_test.dart đạt. HTTP trên Jetson kiểm tra hash JS/tài nguyên; HTTP từ laptop xác nhận bootstrap/entry mới. Không thực hiện đánh giá trực quan trình duyệt trong phiên này.

Đang phục vụ: /home/toan/for_cat/.native-build/flutter/four_ultrasonic_20261027_r2

Bản trước: /home/toan/for_cat/.native-build/flutter/four_ultrasonic_20261027_r2.before_remove_camera_20261108

Main JS SHA256 mới: 2209f6fb678948561cd796188c2bb8c2586577d7551464e13d824b7f7775f75d. Thay cho a7c6f3902bc30016068d1dabe90b87027208ab27d73369e23974e386351f9f5a. Entry/bootstrap/assets có tên theo hash chống cache.

Ba dịch vụ API/bridge/AI giữ nguyên PID và active khi triển khai. Không gửi lệnh phần cứng. Không sửa bản ZIP source báo cáo xuất trước đó; ZIP đó là snapshot trước khi bỏ Camera.
