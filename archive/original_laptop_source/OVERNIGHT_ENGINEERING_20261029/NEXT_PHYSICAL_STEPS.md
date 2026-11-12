# Next USER steps — ngắn, theo gate

1. Review diff `offline_continuation/candidate_changes.patch` và testsummary.
   Giữ newcandidate riêng; không apply lên RCv2, production hoặc firmwarebin đã khóa.
2. Review `HARDWARE_PHYSICAL_BRINGUP_20261029/maintenance_readiness/SAFE_READONLY_CHECKS.md`.
   Nếu USER đồngý, SFTP riêng foldermới vào staging, chạy `readiness.py` defaultPLAN
   rồi explicitmetadata collect. Chỉ đọc existing nativePASS result, không build lạiR1.
3. Gửi actualunit/USB/currentPID/holders, existingboot/securityevidence, ECHOpeak/
   protection, powerisolation và RAM-lossACK. APPflash tiếp tụcNO_GO.
4. Nếu thiếuboot/eFuseproof: USER duyệt **read-maintenance window riêng** trước khi
   dùng serial_window/bootcapture/ROMread. Không nối readapproval sangflashapproval;
   handback đúngoriginalUSERBridge, kiểmAI/APIactive và oldcompatibilitystate.
5. Sau khi mọi flashgate cóproof và reviewriêng, offline app_plan mới được phép
   sinh conditionalAPP-onlywrite/verify/rollback argv. Chưa có writeargv được cấp.
6. Candidateovernight mới cần targetC++14/GCC7.5 regression riêng **chỉ khi USER
   muốn dùng patch mới**; không suy từ R1PASS. Ownercatmodel cần realdataset/enrollment
   và qualification riêng. Closed-loop35g chỉ tới physicalbench khi mechanism/
   calibration/safety đãduyệt, không dùngsensorWeb hoặc genericCAT để kíchservo.

Agent dừng ở đây: không SSH, Serial/camera, reset/serviceaction, actuator hoặcflash.
