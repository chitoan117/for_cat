# Multi-cat vision policy — non-authoritative observation only

`vision/detector.py` requires a configured detector and classifier boundary. No trained model is bundled. A classifier receives a **valid cat crop**, never the whole scene automatically.

| Scene | Safe observation behavior | Feeding authority |
| --- | --- | --- |
| No cat | NO_SUBJECT; no identity crop/classifier | none |
| One confident cat/crop, owner classifier output | OWNER_CAT only after configured detector/identity thresholds | identity alone authorizes nothing |
| OTHER_CAT only | may record other-cat behavior if evidence valid | none based on identity |
| Owner + other, or multiple unknown cats | UNKNOWN with ambiguous=true; do not select the highest score as sole owner | none |
| Overlapping detections | multiple boxes are ambiguous | none |
| Invalid/tiny crop, low detector confidence | UNKNOWN, do not classify arbitrary scene | none |
| Low/absent identity confidence | UNKNOWN | none |

ROIs use normalized positive-area x1,y1,x2,y2. Food/water behavior requires both model ROI evidence and the detected cat center in the configured bowl ROI. Short ROI dropout may be tolerated by the temporal policy; no stable session is created outside the ROI. FEEDER_APPROACH can gate NEAR_FOOD/NEAR_WATER approach evidence. Coordinates/thresholds must be calibrated to the actual camera position; no production ROI is assigned by default.

All current AI runs are shadow/monitoring only. Multiple cats, UNKNOWN, unavailable camera/model or unvalidated thresholds cannot trigger automatic physical feeding. Manual requests and ESP32 final safety remain separate; physical SERIAL feeds remain blocked in this prototype.
