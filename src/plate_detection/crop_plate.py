import cv2
import numpy as np
import uuid
import os
from pathlib import Path
from datetime import datetime


class PlateCropper:
    def __init__(self, output_dir: str = "data/cropped_plates"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def enhance_contrast(self, image: np.ndarray) -> np.ndarray:
        """STTI-96: Apply contrast enhancement and binarization."""
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        # CLAHE contrast enhancement
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        # Binarization using Otsu's threshold
        _, binary = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        return binary

    def crop_plate_region(
        self,
        frame: np.ndarray,
        bbox: tuple,  # (x1, y1, x2, y2)
        violation_id: str = None
    ) -> dict:
        """
        STTI-94/95: Crop license plate using bounding box.
        Returns dict with crop info and saved path.
        """
        x1, y1, x2, y2 = map(int, bbox)

        # Validate bounds
        h, w = frame.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)

        # Extract ROI
        plate_region = frame[y1:y2, x1:x2]

        if plate_region.size == 0:
            raise ValueError("Invalid bounding box: empty region")

        # Enhance for OCR
        processed = self.enhance_contrast(plate_region)

        # STTI-97: Save with unique ID
        unique_id = violation_id or str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"plate_{timestamp}_{unique_id}.png"

        raw_path = self.output_dir / f"raw_{filename}"
        proc_path = self.output_dir / f"proc_{filename}"

        cv2.imwrite(str(raw_path), plate_region)
        cv2.imwrite(str(proc_path), processed)

        return {
            "violation_id": unique_id,
            "bbox": (x1, y1, x2, y2),
            "raw_image_path": str(raw_path),
            "processed_image_path": str(proc_path),
            "dimensions": plate_region.shape[:2],
        }