FOR_CAT11/11/2026 MANUAL OFFLINE R2 — ĐÃ NẠP/READBACK/NVS BYTE-PRESERVED.
UART RX41/TX42 115200, servo1350us900ms/1600us1450ms,35g target/25s weight wait; chờHX3s khôngPWM.
Sửa tương tác WAIT_MANUAL_HX với dự phòng và hẹn giờ, không tự khóa khi yêu cầu còn đang đợi cân.
Nếu OLED KIEM TRA CUA: chỉ sau khi kiểm tra/căn cửa thật vềĐÓNG, đợi khởi độngxong và thả nút rồi nhấn giữ5s, OLEDhếtkhóa; THẢ rồiNHẤNlại để choăn. Giữ5s chỉxácnhậnkhôngtựmở. Nútgiữtừlúcboot/kẹtnút khôngmởkhóa.
Tare−698623 và gain−0.000945082600219258 giữtrongNVS; khôngxóaNVS/khôngtựzeroonboot.
WebmànJetsonmấtnetworkmở127.0.0.1:8000/app, vẫn cầnbackend+UART. Bảnbridgebulkread169... chưađượcdeploydoJetsonkhôngmạng; webofflinecầnkiểmthửthậtsauLCD/PCBnút.
Sourceesp32/esp32.ino cần7headerscùngthưmục (thêmButtonInspectionHold.h). Core3.3.12 ESP32S3 Flash4MB,CDCOnBootDisabled,PSRAMDisabled.
Physicalruntime test pending; do not claim physical35g/pump/poweroutage verified.
