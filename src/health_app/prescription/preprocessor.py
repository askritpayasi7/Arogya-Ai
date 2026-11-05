from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from typing import Optional, Union

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


@dataclass
class PreprocessedPrescription:
    original_pil: Image.Image
    processed_pil: Image.Image
    skew_angle: float
    width: int
    height: int


class ImagePreprocessor:
    """Preprocesses handwritten or printed prescription images for optimal vision OCR."""

    @classmethod
    def load_image(cls, source: Union[bytes, str, Image.Image]) -> Image.Image:
        """Load image into a RGB PIL Image from bytes, path, or existing PIL object."""
        if isinstance(source, Image.Image):
            return source.convert("RGB")
        if isinstance(source, bytes):
            return Image.open(io.BytesIO(source)).convert("RGB")
        if isinstance(source, str):
            return Image.open(source).convert("RGB")
        raise ValueError(f"Unsupported image source type: {type(source)}")

    @classmethod
    def pil_to_bgr(cls, image: Image.Image) -> np.ndarray:
        rgb = np.array(image.convert("RGB"))
        return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

    @classmethod
    def bgr_to_pil(cls, bgr: np.ndarray) -> Image.Image:
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        return Image.fromarray(rgb)

    @classmethod
    def estimate_skew_angle(cls, gray: np.ndarray) -> float:
        """Estimate rotation angle using light binary threshold of dark ink contours."""
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
        coords = np.column_stack(np.where(binary > 0))
        if len(coords) < 50:
            return 0.0
        rect = cv2.minAreaRect(coords.astype(np.float32))
        angle = rect[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        if abs(angle) > 15:
            return 0.0
        return float(angle)

    @classmethod
    def rotate_image(cls, image_bgr: np.ndarray, angle: float) -> np.ndarray:
        """Rotate BGR image around its center by angle degrees with white background fill."""
        if abs(angle) < 0.2:
            return image_bgr
        h, w = image_bgr.shape[:2]
        center = (w / 2.0, h / 2.0)
        matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        return cv2.warpAffine(
            image_bgr,
            matrix,
            (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(255, 255, 255),
        )

    @classmethod
    def enhance_contrast(cls, gray: np.ndarray, clip_limit: float = 2.0) -> np.ndarray:
        """Apply Contrast Limited Adaptive Histogram Equalization."""
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8, 8))
        return clahe.apply(gray)

    @classmethod
    def preprocess(cls, source: Union[bytes, str, Image.Image]) -> PreprocessedPrescription:
        """Deskew and enhance prescription image while preserving natural stroke geometry."""
        original_pil = cls.load_image(source)
        bgr = cls.pil_to_bgr(original_pil)
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

        skew_angle = cls.estimate_skew_angle(gray)
        deskewed_bgr = cls.rotate_image(bgr, skew_angle)

        # CLAHE on luminance in LAB color space to preserve color while boosting ink contrast
        lab = cv2.cvtColor(deskewed_bgr, cv2.COLOR_BGR2LAB)
        l, a, b_chan = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        cl = clahe.apply(l)
        enhanced_lab = cv2.merge((cl, a, b_chan))
        enhanced_bgr = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)

        processed_pil = cls.bgr_to_pil(enhanced_bgr)
        return PreprocessedPrescription(
            original_pil=original_pil,
            processed_pil=processed_pil,
            skew_angle=skew_angle,
            width=processed_pil.width,
            height=processed_pil.height,
        )
