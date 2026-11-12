# D1 bơm NHỊP1s — trạng thái mới nhất09/11/2026

User đã hủy ý auto liên tục vì D1khôngchínhxác; sauđó YÊUCẦUMỚI RÕ: vẫngiữauto nhưngD122.6..22.9cm thìbơmnhịp1s đểtới22.5cm. Đã giải thích khôngthểđảmbảo mỗi nhịp nângnướcđúng0.1cm. Đây là chínhsáchmới cógiớihạnkhácbản30s trướcđó bịreviewtừchối; không retry/bypass bảnnạp30s. Bản30s KHÔNG nạp.

ĐÃ NẠP app370f28064c00def305f5d5afbe4c565e87a78c7ea21e13b3b5c62b0d7a67b8ee; base596317248ba2709d7f480c705d676187062bdd85fb24683ed31add216743cb25 đọcflash/OTA/partition/backup/writeverify/NVSgiữnguyênPASS. Compile413441program/35928globals. Source gốc D:/CODE_TEST_LOADCELL_CHUAN/esp32/esp32.ino vàD1PumpGate.h đã đồngbộ cóguard SHA (source_sync.json). Native test_pulse thực header dùngfirmware PASS.

## Chính sách hiện tại

- D1GPIO14/15 rawvalid/fresh<=1200ms,3mẫukhácnhauliêntiếptrong22.6..22.9cm mớiON.
- TựOFFsauTỐIĐA1000ms hoặc sớmhơn nếuD1<=22.5cm hay mất sốđo.
- NghỉOFFít nhất5000ms, rồi xác nhận3mẫumới. Không bơmngoàidải, khônglấygiátrịcũthayinvalid.
- Tốiđa3nhịp KỂTỪLÚCARM; khôngtựresetbudgetkhiđạtđích (tránhnoise reset gâybơmvôhạn). Nếu vẫnđủđiềukiệnđòinhịpthứ4 thìfaultPULSE_LIMIT. pump_reset/pump_auto on cầnoperator chủđộngcho lượt mới.
- D1mấtsốđo khiđangON thìOFFngayvàoSETTLING, khôngchốtlỗi do một mẫumấttínhiệu; vẫn bịcap3nhịp.
- Mọipercentbowl trảNAN đểkhônghiểnthị%chínhxác từkhoảngcách nhiễu. GiữD1khoảngcáchthamkhảo. D2chưacommission/bìnhcạnchưađưa vàoguard.
- Các lệnh manual pump_test [100..10000ms] giữnguyênnativeMCUtimer. 0/stop/pump_off/sensors_off tắtpump vàdisableauto.
- AutoOFF/driver_unverifiedsaureboot, RAMonlychưapersistautoboot. ModuleF5305SmớiHIGH=ON/LOW=OFF đượcuserxácnhậnphysicalOFFởphiêntrước. Không đổi servo/HX/food/backup/lịch/web/backend.

## Quan sát sau nạp

Đã gửi0/pump_reset/pump_driver_verified/pump_auto on/pump_status theo yêu cầumới. Khoảng40s quan sát, D1daođộng~20.01..23.38, không đủ3rawframesliêntiếptrongdảikhôngbịngắt; pulses0, running0, fault0. CuốicùngD122.33 reasonTARGET_225CM. Chưa cónhịp bơmthật ởđợtcommissionnày, KHÔNG báolàđãchứngminhnângnước0.1cm. Native tests chứngminh1s/5s/budget/đíchtimestamp, không chứngminhhardwareflow. Trạngtháicuối auto1/driververified1/running0/fault0/pulses0, đangarmedchờD1phùhợp; sourcecóhạnchế3nhịpđể khôngbơmlặp vôhạn.

Choăn vẫnpausedsauflash; servoestimateUNKNOWN, chưainspect_ok/homing. Khôngtare/cal hoặc di chuyểnservo. BackupNVSđượcbảo toàn.
