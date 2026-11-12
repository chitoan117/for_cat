# FOR_CAT - LENH SU DUNG DU AN

## 1. Ket noi Jetson Nano tu laptop

IP la DHCP, co the thay doi. Uu tien hostname:
server-jetson.local

MAC Jetson:
48-b0-2d-2f-34-dc

Tu PowerShell Windows:

ssh -Y toan@server-jetson.local

Neu hostname khong resolve, lay IP thuc te tu `hostname -I` tren Jetson
hoac DHCP router va doi host trong lenh SSH. Khong hard-code IP vao source.

Sau do:

arp -a

Tim MAC:
48-b0-2d-2f-34-dc


## 2. Kiem tra Jetson

hostname

hostname -I

free -h

df -h


## 3. Kiem tra X11 de hien camera tren laptop

echo $DISPLAY

Neu hien dang:

localhost:10.0

thi X11 dang hoat dong.


## 4. Chay nhan dien CAT / DOG

cd /home/toan/for_cat/jetson/ai

./cat_dog_trt

Headless pure inference, khong ghi JPEG, do 30 giay sau 5 warm-up frames:

./cat_dog_trt --headless --no-snapshot --seconds 30

Headless + snapshot khoang 1 Hz:

./cat_dog_trt --headless --seconds 30

GUI/X11 (can DISPLAY hop le tu phien SSH -Y va X server tren laptop):

echo "$DISPLAY"
./cat_dog_trt --gui --seconds 30

Mac dinh: latest-frame, V4L2 MJPG 640x480 @30, mot application slot.
Driver duoc thu buffer=1 roi chon 2: mot buffer da do chi ~15 FPS tren webcam nay.
Log CAP_PROP actual/readback, khong coi requested FPS la measured throughput.

Thoat:
Nhan q trong cua so camera

hoac:

Ctrl + C


## 5. Neu gap loi OpenCV / libgomp

export LD_PRELOAD=/usr/lib/aarch64-linux-gnu/libgomp.so.1

Sau do:

cd /home/toan/for_cat/jetson/ai
./cat_dog_trt


## 6. Compile lai chuong trinh C++

ROOT=/home/toan/for_cat
BUILD="$(mktemp -d /tmp/for-cat-test.XXXXXX)"
sh "$ROOT/scripts/build_cat_dog_trt.sh" "$BUILD/cat_dog_trt_low_latency"
"$BUILD/cat_dog_trt_low_latency" --headless --no-snapshot --seconds 30

Script dung C++14 -O2 -pthread, OpenCV4, TensorRT va CUDA10.2.
Output phai la path moi; script khong overwrite binary production.
`destroy()` deprecated warning tren TensorRT8.2 da duoc ghi nhan, khong tu upgrade stack.


## 7. Webcam

Kiem tra:

ls -l /dev/video*

Webcam hien tai:
/dev/video0


## 8. TensorRT model

ONNX:

/home/toan/for_cat/models/coco/yolov8n_320.onnx

TensorRT FP16 engine:

/home/toan/for_cat/models/tensorrt/yolov8n_320_fp16.engine

Input:
1 x 3 x 320 x 320

Output:
1 x 84 x 2100

COCO class:
CAT = 15
DOG = 16


## 9. Build TensorRT engine lai

Day la lenh rebuild engine thu cong, KHONG can cho camera patch.
Khong overwrite engine da validated; neu can thi dung output candidate rieng:

ENGINE_BUILD="$(mktemp -d /tmp/for-cat-engine.XXXXXX)"

/usr/src/tensorrt/bin/trtexec \
  --onnx=/home/toan/for_cat/models/coco/yolov8n_320.onnx \
  --saveEngine="$ENGINE_BUILD/yolov8n_320_fp16_candidate.engine" \
  --fp16 \
  --workspace=64


## 10. Chay TensorRT benchmark

/usr/src/tensorrt/bin/trtexec \
  --loadEngine=/home/toan/for_cat/models/tensorrt/yolov8n_320_fp16.engine


## 11. Thu muc du an

cd /home/toan/for_cat

Cac thu muc chinh:

jetson/
esp32/
ai/
docs/
models/
scripts/


## 12. Git - xem trang thai

cd /home/toan/for_cat

git status


## 13. Git - luu code moi len GitHub

cd /home/toan/for_cat

git status --short
git diff --check
git add -- jetson/ai/cat_dog_trt.cpp JETSON_COMMANDS.md

git commit -m "Update for_cat project"

git push


## 14. Git - tai code moi nhat tu GitHub

cd /home/toan/for_cat

git pull


## 15. Kiem tra GitHub remote

git remote -v

Repo:

https://github.com/chitoan117/for_cat


## 16. Xem lich su commit

git log --oneline --all --decorate -10


## 17. Che do an toan hien tai

AI dang o SHADOW MODE.

Jetson chi nhan dien va ghi nhan ket qua.

Chua cho AI tu dong kich hoat servo/pump.

ESP32-S3 se la bo dieu khien an toan cuoi cung khi ket noi actuator.


## 18. Logic muc tieu

Webcam
  -> Jetson Nano
  -> TensorRT AI
  -> CAT / DOG
  -> Logic he thong
  -> UART / USB Serial
  -> ESP32-S3
  -> Servo / Pump / Sensor

CAT:
observation only, KHONG tu dong cho an.

DOG:
BLOCK.

PERSON / UNKNOWN / NONE:
khong co feeding authority. Luu y decoder hien tai chi so CAT/DOG scores,
chua enforce winner tren toan bo 80 COCO classes, nen khong tuyen bo PERSON
duoc chan hoan toan o detector. Khong co AI -> actuator path.


## 19. Lenh dung chuong trinh

Ctrl + C


## 20. Lenh nhanh hay dung nhat

Ket noi Jetson:

ssh -Y toan@server-jetson.local

Chay AI:

cd /home/toan/for_cat/jetson/ai
./cat_dog_trt

Cap nhat GitHub:

cd /home/toan/for_cat
git status --short
git diff --check
git add -- jetson/ai/cat_dog_trt.cpp JETSON_COMMANDS.md
git commit -m "Update project"
git push

Chi push khi auth/remote state ro rang va cac gate test/compile/runtime da PASS.
Khong stage model, video, dataset, evidence rieng hay backup.

## 21. So sanh sequential / latest (cung engine, chay LAN LUOT)

./cat_dog_trt --capture-mode sequential --headless --no-snapshot --seconds 30
./cat_dog_trt --capture-mode latest --headless --no-snapshot --seconds 30
./cat_dog_trt --capture-mode sequential --gui --seconds 30
./cat_dog_trt --capture-mode latest --gui --seconds 30

`FRAME_AGE_ms` bat dau SAU cap.read(), khong thay kernel backlog.
`DRIVER_AGE_ms` dung timestamp V4L2 khi dong ho phu hop; -1 neu khong kha dung.
Khong goi hai metric nay la sensor-exposure/glass-to-glass latency.
FPS dung so frame / wall time, bao gom display/JPEG. Log ~1 Hz, final SUMMARY.
SNAPSHOT_ms la mean moi lan ghi; SNAPSHOT_AMORTIZED_ms la chi phi moi frame.
DROPPED la frame bi replace trong application slot, khong phai moi sensor drop.

## 22. Native tests cho capture/binding va detector

ROOT=/home/toan/for_cat
TEST_BUILD="$(mktemp -d /tmp/for-cat-native.XXXXXX)"
g++ -std=c++14 -O2 -pthread -Wall -Wextra -Werror \
  "$ROOT/jetson/ai/test_latency_support.cpp" -o "$TEST_BUILD/test_latency"
"$TEST_BUILD/test_latency"

# TSan hoac ASan/UBSan neu toolchain da co san; khong tu cai package:
g++ -std=c++14 -O1 -g -pthread -fsanitize=thread \
  "$ROOT/jetson/ai/test_latency_support.cpp" -o "$TEST_BUILD/test_tsan"
"$TEST_BUILD/test_tsan"

# Decoder/preprocess synthetic unit cases; khong phai physical animal evidence:
g++ -std=c++14 -O2 -pthread "$ROOT/jetson/ai/test_detector_regression.cpp" \
  -o "$TEST_BUILD/test_detector" $(pkg-config --cflags --libs opencv4) \
  -I/usr/include/aarch64-linux-gnu -I/usr/local/cuda-10.2/include \
  -L/usr/lib/aarch64-linux-gnu -L/usr/local/cuda-10.2/lib64 -lnvinfer -lcudart
"$TEST_BUILD/test_detector"

Optional: them 3 image paths CAT DOG PERSON vao lenh test_detector de test
engine that tren anh da co. Day van la OFFLINE_IMAGE, khong phai live physical PASS.

## 23. Rollback binary (khong xoa backup/model)

Ban cu da luu tai:
/home/toan/for_cat/jetson/ai/cat_dog_trt.backup_pre_latency

Neu can rollback, dung rieng detector truoc, khong dung capture session khac.

ROOT=/home/toan/for_cat
PENDING="$(mktemp "$ROOT/jetson/ai/.rollback.XXXXXX")"
install -m 755 "$ROOT/jetson/ai/cat_dog_trt.backup_pre_latency" "$PENDING"
mv "$PENDING" "$ROOT/jetson/ai/cat_dog_trt"

Binary legacy khong co flags instrumentation moi; source version moi van duoc
giu trong Git. Khong overwrite/xoa engine hay backup de rollback camera.

## 24. Behavior V2 — chi tooling offline, chua train

ONE CAT; EATING / DRINKING / IDLE. RED bowl=FOOD, BLUE bowl=WATER,
BLUE floor line=approach. NONE/UNKNOWN/UNSURE khong ep thanh IDLE.
Owner/other identity khong phai requirement cua V2; schema v1 giu nguyen.

Tren host Python >=3.10, dung workflow chinh xac trong:
docs/SINGLE_CAT_BEHAVIOR_V2.md

Reuse import_video/extract_frames/label_dataset/split_dataset/dataset_release.
Extraction: --schema-version 2 --interval-seconds 0.5 --minimum-spacing 0.5
Annotation V2: --subject CAT --behavior EATING|DRINKING|IDLE (chon mot nhan da review).
Validation/export/training-plan: --task behavior_v2
`prepare_training` chi tao plan, khong train. Khong chay tooling hien dai nay
bang system Python3.6 cua Nano. `bringup.camera` Python3.6 la diagnostic legacy;
missing ai.label_schema da duoc restore, dry-run khong mo camera.

Runtime C++ hien chua load ROI template, chua tracker/behavior classifier/FSM.
HX711 grams va water-refill safety van thuoc sensor/ESP32, khong phai camera.
