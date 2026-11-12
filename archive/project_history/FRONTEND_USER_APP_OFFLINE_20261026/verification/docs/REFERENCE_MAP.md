# Reference map — design sources, never forr_cat validation results

| Category | Reference / intended use | Evidence boundary |
| --- | --- | --- |
| NVIDIA jetson-inference | https://github.com/dusty-nv/jetson-inference — detectNet, crop/classifier/TensorRT concept; README inspected | no code vendored, no model deployed, no accuracy borrowed |
| NVIDIA Jetson | https://developer.nvidia.com/embedded/jetpack — exact Nano/JetPack compatibility to check after arrival | no Jetson version asserted |
| Espressif S3 GPIO | https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-reference/peripherals/gpio.html — consulted strap/USB/SPI reservation notes | no seller GPIO compatibility asserted |
| Espressif board/toolchain | installed `esp32-s3-devkitc-1.json`, Arduino `boards.txt`, S3 `qio_opi` libraries, `default_16MB.csv` — inspected compile support | official N8 target plus memory overrides only, not seller schematic |
| Espressif NVS / Arduino Preferences | installed Arduino Preferences headers/library; https://docs.espressif.com/projects/arduino-esp32/en/latest/api/preferences.html | compiled adapter and host record codec only, no NVS power-loss claim |
| Optional Roboflow | https://docs.roboflow.com/ — annotation/export concepts only, local session reconstruction required | no upload/key/dependency or imported dataset |
| Public cat re-identification research | Literature selection **pending**: verify subjects, identity split, licence and OTHER_CAT false-acceptance methodology before using a study | no study score presented as our result; no dataset downloaded |
| Cat behavior research | Literature selection **pending**: temporal definitions of eating/drinking, inter-annotator agreement and occlusion handling | synthetic temporal tests are not behavioral validation |
| Food palatability/preference research | Literature selection **pending**: repeated trials/confounder controls, consumption and approach metrics | current formula explicitly EXPERIMENTAL |
| Open-source pet feeders | Project selection **pending**: inspect licences, actuator safety/mechanics and electrical evidence, not random code copying | no unrelated source copied and no hardware pass inferred |

Links are reference entry points, not a bibliography of experimentally adopted studies. Actual academic citations and detailed method review should be added only after selecting verifiable research relevant to the real setup.
