"""
KiranaVision — OpenCV Countertop & Weighing Machine Preprocessing Pipeline
Handles illumination normalization, motion stability gating, contour segmentation,
and bounding box annotation for overhead scale cameras.
"""
from typing import Dict, List, Optional, Tuple
import base64
import cv2
import numpy as np


class OpenCVScalePipeline:
    def __init__(self):
        self.prev_gray: Optional[np.ndarray] = None
        self.clahe = cv2.createCLAHE(clipLimit=2.2, tileGridSize=(8, 8))
        # Default normalized ROI representing the weighing machine platform (x1, y1, x2, y2 in 0..1)
        self.roi_norm: Tuple[float, float, float, float] = (0.08, 0.08, 0.92, 0.92)

    def decode_image(self, image_bytes: bytes) -> np.ndarray:
        arr = np.frombuffer(image_bytes, dtype=np.uint8)
        bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if bgr is None:
            raise ValueError("Unable to decode image frame with OpenCV")
        return bgr

    def encode_base64_jpeg(self, bgr: np.ndarray, quality: int = 88) -> str:
        ok, buf = cv2.imencode(".jpg", bgr, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
        if not ok:
            return ""
        b64 = base64.b64encode(buf.tobytes()).decode("ascii")
        return f"data:image/jpeg;base64,{b64}"

    def normalize_lighting(self, bgr: np.ndarray) -> np.ndarray:
        """Applies LAB L-channel CLAHE to compensate for counter shadows and glare."""
        lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
        l_ch, a_ch, b_ch = cv2.split(lab)
        l_eq = self.clahe.apply(l_ch)
        merged = cv2.merge((l_eq, a_ch, b_ch))
        return cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)

    def check_motion_stability(self, bgr: np.ndarray) -> Dict[str, float | bool]:
        """Checks frame-to-frame pixel difference to detect when hand leaves the weighing pan."""
        small = cv2.resize(bgr, (160, 120))
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)

        if self.prev_gray is None or self.prev_gray.shape != gray.shape:
            self.prev_gray = gray
            return {"stable": True, "motion_score": 0.0}

        diff = cv2.absdiff(self.prev_gray, gray)
        self.prev_gray = gray
        motion_score = float(np.mean(diff))
        return {
            "stable": motion_score < 12.0,
            "motion_score": round(motion_score, 2),
        }

    def segment_packets(
        self, bgr: np.ndarray, max_objects: int = 6
    ) -> List[Dict]:
        """
        Segments distinct product packets placed on the weighing platform or table.
        Returns a list of bounding boxes (x, y, w, h) and cropped packet regions.
        """
        h, w = bgr.shape[:2]
        rx1 = int(w * self.roi_norm[0])
        ry1 = int(h * self.roi_norm[1])
        rx2 = int(w * self.roi_norm[2])
        ry2 = int(h * self.roi_norm[3])

        roi_crop = bgr[ry1:ry2, rx1:rx2]
        rh, rw = roi_crop.shape[:2]
        min_area = (rh * rw) * 0.035
        max_area = (rh * rw) * 0.96

        # Combine Canny edges + saturation/value deviation from neutral background
        hsv = cv2.cvtColor(roi_crop, cv2.COLOR_BGR2HSV)
        sat = hsv[:, :, 1]
        val = hsv[:, :, 2]

        gray = cv2.cvtColor(roi_crop, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 35, 120)

        # Mask high-saturation OR high-brightness regions (milk white pouches or colorful snacks)
        _, mask_sat = cv2.threshold(sat, 42, 255, cv2.THRESH_BINARY)
        _, mask_bright = cv2.threshold(val, 175, 255, cv2.THRESH_BINARY)
        combined = cv2.bitwise_or(edges, cv2.bitwise_or(mask_sat, mask_bright))

        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
        closed = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel, iterations=2)

        contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        candidates = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < min_area or area > max_area:
                continue
            bx, by, bw, bh = cv2.boundingRect(cnt)
            if bw < 28 or bh < 28:
                continue
            aspect = bh / float(max(bw, 1))
            if aspect < 0.25 or aspect > 4.0:
                continue

            # Translate back to full frame coordinates
            fx = rx1 + bx
            fy = ry1 + by
            candidates.append({
                "bbox": [int(fx), int(fy), int(bw), int(bh)],
                "area": float(area),
                "crop": bgr[fy : fy + bh, fx : fx + bw].copy(),
            })

        # Sort by area descending and filter heavy overlaps (NMS-style)
        candidates.sort(key=lambda c: c["area"], reverse=True)
        filtered = []
        for cand in candidates:
            cx, cy, cw, ch = cand["bbox"]
            overlapped = False
            for kept in filtered:
                kx, ky, kw, kh = kept["bbox"]
                ix1 = max(cx, kx)
                iy1 = max(cy, ky)
                ix2 = min(cx + cw, kx + kw)
                iy2 = min(cy + ch, ky + kh)
                if ix2 > ix1 and iy2 > iy1:
                    inter = (ix2 - ix1) * (iy2 - iy1)
                    if inter / float(cw * ch) > 0.55:
                        overlapped = True
                        break
            if not overlapped:
                filtered.append(cand)
            if len(filtered) >= max_objects:
                break

        # Fallback: if no distinct contour was isolated, use the central weighing zone crop
        if not filtered:
            pad_x = int(rw * 0.12)
            pad_y = int(rh * 0.12)
            fx = rx1 + pad_x
            fy = ry1 + pad_y
            fw = max(32, rw - 2 * pad_x)
            fh = max(32, rh - 2 * pad_y)
            filtered.append({
                "bbox": [fx, fy, fw, fh],
                "area": float(fw * fh),
                "crop": bgr[fy : fy + fh, fx : fx + fw].copy(),
            })

        return filtered

    def draw_hud_overlay(
        self,
        bgr: np.ndarray,
        detections: List[Dict],
        scale_weight_g: Optional[float] = None,
    ) -> np.ndarray:
        """Draws the Weighing Scale ROI corner brackets and detected packet bounding boxes."""
        annotated = bgr.copy()
        h, w = annotated.shape[:2]

        # Draw Scale Platform ROI corner markers
        rx1 = int(w * self.roi_norm[0])
        ry1 = int(h * self.roi_norm[1])
        rx2 = int(w * self.roi_norm[2])
        ry2 = int(h * self.roi_norm[3])
        corner_len = 24
        roi_color = (180, 210, 80)

        for (px, py, dx, dy) in [
            (rx1, ry1, 1, 1),
            (rx2, ry1, -1, 1),
            (rx1, ry2, 1, -1),
            (rx2, ry2, -1, -1),
        ]:
            cv2.line(annotated, (px, py), (px + dx * corner_len, py), roi_color, 2)
            cv2.line(annotated, (px, py), (px, py + dy * corner_len), roi_color, 2)

        # Draw each detection bounding box & HUD pill
        for det in detections:
            x, y, bw, bh = det["bbox"]
            conf_pct = int(round(det.get("confidence", 0.0) * 100))
            label = f"{det.get('short_name', det.get('name', 'Item'))} ({conf_pct}%)"
            price_str = f"Rs.{int(det.get('selling_price', 0))} | ~{det.get('unit_weight_g', 0)}g"

            box_color = (90, 230, 70) if conf_pct >= 70 else (40, 185, 250)
            cv2.rectangle(annotated, (x, y), (x + bw, y + bh), box_color, 2)

            # Top label background
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.52, 2)
            lbl_y = max(y - 8, th + 10)
            cv2.rectangle(
                annotated,
                (x, lbl_y - th - 8),
                (x + tw + 14, lbl_y + 4),
                box_color,
                -1,
            )
            cv2.putText(
                annotated,
                label,
                (x + 6, lbl_y - 2),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.52,
                (15, 20, 15),
                2,
                cv2.LINE_AA,
            )

            # Bottom weight/price tag
            cv2.putText(
                annotated,
                price_str,
                (x + 6, min(h - 10, y + bh - 8)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (255, 255, 255),
                1,
                cv2.LINE_AA,
            )

        if scale_weight_g is not None:
            w_banner = f"SCALE LOAD: {int(round(scale_weight_g))} g"
            cv2.putText(
                annotated,
                w_banner,
                (rx1 + 10, ry2 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.52,
                (120, 245, 190),
                2,
                cv2.LINE_AA,
            )

        return annotated
