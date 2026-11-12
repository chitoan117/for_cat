/* Standalone image-review utility; no product frontend/camera/network access. */
(function (root) {
  "use strict";
  function normalizedRect(width, height, left, top, right, bottom) {
    const values = [width, height, left, top, right, bottom];
    if (!values.every(Number.isFinite) || !Number.isInteger(width) || !Number.isInteger(height) ||
        width < 2 || height < 2 || width > 16384 || height > 16384 ||
        left < 0 || top < 0 || left >= right || top >= bottom || right > width || bottom > height) {
      throw new Error("INVALID_IMAGE_RECTANGLE");
    }
    return {x1: left / width, y1: top / height, x2: right / width, y2: bottom / height};
  }
  function configuration(mode, image, rectangle, reviewed, reviewId, cameraDevice) {
    if (mode !== "FULL_FRAME" && mode !== "ROI_ENABLED") throw new Error("INVALID_MODE");
    let box = null;
    if (image && rectangle) {
      try { box = normalizedRect(image.width, image.height, rectangle.left, rectangle.top, rectangle.right, rectangle.bottom); }
      catch (error) { if (mode === "ROI_ENABLED") throw error; }
    }
    const calibrated = Boolean(box && reviewed && typeof reviewId === "string" && reviewId.trim());
    if (mode === "ROI_ENABLED" && !calibrated) throw new Error("ROI_REVIEW_REQUIRED");
    return {mode: mode, enabled: mode === "ROI_ENABLED", calibrated: calibrated,
      review_id: calibrated ? reviewId.trim() : "", camera_device: cameraDevice || "",
      width: image ? image.width : 0, height: image ? image.height : 0,
      x1: box ? box.x1 : null, y1: box ? box.y1 : null, x2: box ? box.x2 : null, y2: box ? box.y2 : null};
  }
  const api = {normalizedRect: normalizedRect, configuration: configuration};
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.RoiCalibration = api;
}(typeof window !== "undefined" ? window : globalThis));
