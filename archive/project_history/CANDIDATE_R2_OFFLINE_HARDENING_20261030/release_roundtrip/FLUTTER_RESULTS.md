# Paired Flutter / API readiness

Candidate dùng sourcewidgets hiện có, không redesign. Seven sharedUI/camerahelper
files được snapshot **unchanged** và pin trongSHARED_UI_BASELINE.json; pubspec dùng
`../flutter_shared`, không còn absoluteD:path gây lỗiLinuxresolution. TargetFlutter
SDK/deps không được cài, chưa build trênJetson.

Latestportableclosure run `evidence/flutter_20261030_114952`:21PASS/analyzeclean.
Newbaselinecomparison `flutter_20261030_121738`:1PASS/analyzeclean.22unique, không
cộng lần21trước đó. R2baselinecontrollercopy ởtest/baseline_panel.dart chỉ probe,
không activeUI; sau4s cachedhealthy vẫnconnected, hardeningexpired.

Covered actualAPI fixtures:CAT/DOG/NONE, staleAIUNKNOWN, healthyHXgrams/4ultras/PIR/
OLED/button, outoforder, disconnect/reconnect/timeout, hostmismatch, unsafe.
LocalmonotonicTTL tiếp tục chạy khiHTTPpending/fails; identicalframe không reset
age. RTT được tính conservative từrequesttime. Clockregression/unknownage không
giảfresh; null không thành0. AIage độc lập và NONE khác UNKNOWN.

SIMULATEDbanner luôn hiện; forgedOFFLINEpayloadREAL bịreject. Defaultcamera slot
không instantiateLiveCameraPanel khi sourceSIMULATED/UNKNOWN. Chưa validateLIVE
measurements/camera, không gọi syntheticLIVEfixture là realproof.

NewmassDTO:target35/tolerance5/bounds30–40; client rejectsold/missingpolicy, vì vậy
API/UI phải đi cùng nhau. Actual30/35/36/38/40 hiển thị đúnggram khifinal/safety
qualify;41sourceunsettled choactualnull vàlastobserved41, không hiển thị0 hoặc35.
ACK luônPENDING; masspassalone không COMPLETE; defaultwireSUCCESSkhông cógrams
hiện MASS_UNKNOWN, ERROR/contradiction làFAULT.

No deployment. NewAPIfields additive nhưng freshness/reboot/acceptance semantics
và clientpolicyrequirements thay đổi so với lockedR2; reviewcoupledpackage,
không chỉ copy một Dartfile lên production.
