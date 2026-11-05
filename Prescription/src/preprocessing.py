"""Gentle image preprocessing for handwritten prescriptions.

The goal is readability, not a binary stamp. Heavy thresholding can wipe out
thin handwriting, so the image sent to Gemini is deskewed while preserving color
and handwriting stroke subtleties. Adaptive thresholding is kept as a preview for humans.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image


@dataclass
class PreprocessResult:
    original_bgr: np.ndarray
    grayscale: np.ndarray
    clahe: np.ndarray
    deskewed: np.ndarray
    thresholded: np.ndarray
    model_input: np.ndarray
    skew_angle: float


def pil_to_bgr(image: Image.Image) -> np.ndarray:
    rgb = np.array(image.convert("RGB"))
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def bgr_to_pil(image_bgr: np.ndarray) -> Image.Image:
    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    return Image.fromarray(rgb)


def to_grayscale(image_bgr: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)


def apply_clahe(gray: np.ndarray, clip_limit: float = 2.0) -> np.ndarray:
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8, 8))
    return clahe.apply(gray)


def _estimate_skew_angle(gray: np.ndarray) -> float:
    """Estimate rotation using a light binary mask of dark ink."""
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    coords = np.column_stack(np.where(binary > 0))
    if len(coords) < 50:
        return 0.0
    rectangle = cv2.minAreaRect(coords.astype(np.float32))
    angle = rectangle[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    if abs(angle) > 15:
        return 0.0
    return float(angle)


def deskew(gray: np.ndarray) -> tuple[np.ndarray, float]:
    angle = _estimate_skew_angle(gray)
    if abs(angle) < 0.3:
        return gray, 0.0
    height, width = gray.shape[:2]
    center = (width // 2, height // 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(
        gray,
        matrix,
        (width, height),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )
    return rotated, angle


def rotate_bgr(image_bgr: np.ndarray, angle: float) -> np.ndarray:
    if abs(angle) < 0.3:
        return image_bgr
    height, width = image_bgr.shape[:2]
    center = (width // 2, height // 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(
        image_bgr,
        matrix,
        (width, height),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )


def adaptive_threshold(gray: np.ndarray) -> np.ndarray:
    blurred = cv2.GaussianBlur(gray, (3, 3), 0)
    return cv2.adaptiveThreshold(
        blurred,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        10,
    )


def preprocess_prescription(image: Image.Image) -> PreprocessResult:
    original_bgr = pil_to_bgr(image)
    grayscale = to_grayscale(original_bgr)
    clahe = apply_clahe(grayscale)
    deskewed, angle = deskew(clahe)
    thresholded = adaptive_threshold(deskewed)
    model_input = rotate_bgr(original_bgr, angle)
    return PreprocessResult(
        original_bgr=original_bgr,
        grayscale=grayscale,
        clahe=clahe,
        deskewed=deskewed,
        thresholded=thresholded,
        model_input=model_input,
        skew_angle=angle,
    )
