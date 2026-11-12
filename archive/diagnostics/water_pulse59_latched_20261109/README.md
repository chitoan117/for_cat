# D1 cạn6.1..6.4cm, dừng5.9cm — bản cuối09/11/2026

ĐÃ NẠP appb0147f9cdfd0a665a17b2702ab254e77221477c44eed1433123537cf02d717c6, compile413445program/35928globals; oldappc4dc435e1ce7dd50d8adc6059a748d0ff8654870aeee547d6fa892912d0034ee là bảntrunggian đãnạp chỉđổingưỡng. Bảncuốithêmrefilling latchđểsau1nhịpnếuD1=6.0cm vẫntiếptụcnhịp đến<=5.9, không bịkhoảngtrốngdeadband6.0.

User đã chỉnh cốđịnhD1 mới, xácnhận cạn6.1..6.4cm, yêu cầu "khởi động và cho bơm đếnD1=5.9ngắtngay,bơmtừtừ". GiữnhịpTỐIĐA1s, nghỉ>=5s,3mẫufreshdistinct đểkích, cap3nhịp/arming, invalid/staleOFFngay, khôngbơmliêntục. Đã cónative regressioncho6.0cmtiếptụclượtnước vàcácbiêntimer/budget/rollover. Percent vẫnNAN vìD1khôngđủđộchínhxácnhưuser đãnói. D2bìnhcạnchưacommission. PinD114/15,D218/19giữnguyên.

Đọc backup/partition/OTA/actualapp/hash/NVS trước và sau đềuPASS. MỐC CÂN CHỐT giữtare_counts=-699066.4666666667,grams_per_count=-0.000945082600219258, postflashliveg0.08. Khônggửitare/cal, khôngchỉnhfactor/filterscale. Source gốc D:/CODE_TEST_LOADCELL_CHUAN/esp32/esp32.ino vàD1PumpGate.h đồngbộquaSHAguard, source_sync.json. Bốnfilecầnbuild:ino+CatNearGate.h+FallbackGate.h+D1PumpGate.h.

User freshly confirmed "Đã cấp nguồn,cónước vàđầurađúngchén" saukhinạp, do nguồnđãtắttrongchẩncân. Đã gửi0/pump_reset/pump_driver_verified/pump_auto on/pump_status. Commission: D16.35CONFIRMING→pulses1SETTLING6.28/6.29/6.62→outsideband10.00(nobơm)→confirming6.04(refillingretained)→TARGET_59CM5.71,pulses1,running0,fault0,auto1. ĐãxácnhậnbằngtelemetrymộtnhịpđượcphátvàđãOFF, D1reported<=5.9; chưa cóphản hồiquansátphysicalnước/pumpdừngởlượtnày, khôngcoi5.71làđođộcaonướctuyệtđốichínhxác. Sourcecap1slàMAX, đạtđíchtrongnhịpthìtắtsớm.

Trạngtháicuối:auto1,driververified1,running0,fault0,pulses1. Còn2nhịptrongbudgetarmingnày; nếuđòinhịpthứ4thìPULSE_LIMIT,chờoperatorreset. Khôngtựmởlạibudget. Startup/rebootautoOFF,driverunverified, RAMonly. KhôngpersistbơmautoONsauboot.

Choăn vẫn tạmdừng(EXIT0)saukhinạp/khithửnước;servoestimateUNKNOWNnênkhônginspect_okgiả, khôngchoănhoặcmởđóngtrongphiên. CầnfreshphysicalCLOSEDconfirmationvànguồnservođãcấplạitrướckhitestchoănlại. Khôngmặcđịnhđãcấpnguồnservo chỉvìuserđãcấpnguồnpump.

Cácmốc22.4/22.3trướclúcchẩncânKHÔNGnạp. Cácmốc22.7→20/21.5đãbịmốcmới6.1..6.4→5.9thaythế. Bản30sliêntụcchưanạpvìbịreviewrejectsauuserđổiyêu cầu; bảnnhịp1sđượcyêucầumớiủyquyềnvànạp, khôngretry30s.
