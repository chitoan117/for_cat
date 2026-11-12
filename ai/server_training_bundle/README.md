# FOR_CAT GPU TRAINING BUNDLE

Models:
1. CAT detector
2. Behavior: EATING / DRINKING / OTHER
3. Food state: EMPTY_BOWL / FOOD_FULL

Public cat data is generic cat data only.
It is NOT OWNER_CAT data.

OWNER_CAT identity will be trained later using real images/videos
of the user's actual cat.

Original dataset YAML/provenance files are stored in:
provenance/

Deployment:
USB Webcam -> Jetson Nano -> AI -> ESP32-S3

Keep AI_SHADOW_MODE enabled during initial validation.
ESP32-S3 remains the physical actuator safety authority.
