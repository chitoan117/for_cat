# FOR_CAT - LENH SU DUNG DU AN

## 1. Ket noi Jetson Nano tu laptop

IP hien tai:
192.168.123.10

MAC Jetson:
48-b0-2d-2f-34-dc

Tu PowerShell Windows:

ssh -Y toan@192.168.123.10

Neu IP thay doi, quet mang bang PowerShell:

1..254 | ForEach-Object {
    $ip = "192.168.123.$_"
    $p = New-Object System.Net.NetworkInformation.Ping
    try {
        $r = $p.Send($ip, 100)
        if ($r.Status -eq "Success") {
            Write-Host $ip
        }
    } catch {}
}

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

g++ -std=c++14 -O2 \
  /home/toan/for_cat/jetson/ai/cat_dog_trt.cpp \
  -o /home/toan/for_cat/jetson/ai/cat_dog_trt \
  $(pkg-config --cflags --libs opencv4) \
  -I/usr/include/aarch64-linux-gnu \
  -I/usr/local/cuda-10.2/include \
  -L/usr/lib/aarch64-linux-gnu \
  -L/usr/local/cuda-10.2/lib64 \
  -lnvinfer \
  -lcudart


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

mkdir -p /home/toan/for_cat/models/tensorrt

/usr/src/tensorrt/bin/trtexec \
  --onnx=/home/toan/for_cat/models/coco/yolov8n_320.onnx \
  --saveEngine=/home/toan/for_cat/models/tensorrt/yolov8n_320_fp16.engine \
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

git add .

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
co the di tiep vao logic cho an.

DOG:
BLOCK.

PERSON / UNKNOWN / NONE:
BLOCK.


## 19. Lenh dung chuong trinh

Ctrl + C


## 20. Lenh nhanh hay dung nhat

Ket noi Jetson:

ssh -Y toan@192.168.123.10

Chay AI:

cd /home/toan/for_cat/jetson/ai
./cat_dog_trt

Cap nhat GitHub:

cd /home/toan/for_cat
git add .
git commit -m "Update project"
git push
