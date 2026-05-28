"""
EssayGrader — OCR Service Module
==================================
Wraps Tesseract OCR for extracting text from uploaded images.
Includes image preprocessing for better OCR accuracy.
"""

from __future__ import annotations

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Try importing OCR dependencies
try:
    from PIL import Image, ImageFilter, ImageEnhance
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False


class OCRService:
    """
    OCR service for extracting text from images of handwritten/typed answers.
    Uses Tesseract OCR with image preprocessing for improved accuracy.
    """

    SUPPORTED_FORMATS = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif', '.webp'}

    def __init__(self, tesseract_cmd: Optional[str] = None, lang: str = 'ind+eng'):
        """
        Args:
            tesseract_cmd: Path to tesseract executable (auto-detected if None)
            lang: OCR language(s) to use (default: Indonesian + English)
        """
        self.lang = lang
        self._available = PIL_AVAILABLE and TESSERACT_AVAILABLE

        if tesseract_cmd and TESSERACT_AVAILABLE:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

        if not PIL_AVAILABLE:
            logger.warning("[OCR] Pillow not installed. OCR unavailable.")
        if not TESSERACT_AVAILABLE:
            logger.warning("[OCR] pytesseract not installed. OCR unavailable.")

    @property
    def is_available(self) -> bool:
        return self._available

    def extract_text(self, image_path: str) -> str:
        """
        Extract text from an image file.

        Args:
            image_path: Absolute path to the image file

        Returns:
            Extracted text string
        """
        if not self._available:
            raise RuntimeError("OCR not available. Install Pillow and pytesseract.")

        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")

        ext = os.path.splitext(image_path)[1].lower()
        if ext not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported format: {ext}")

        try:
            img = Image.open(image_path)
            img = self._preprocess_image(img)
            text = pytesseract.image_to_string(img, lang=self.lang)
            text = text.strip()
            logger.info(f"[OCR] Extracted {len(text)} chars from {os.path.basename(image_path)}")
            return text
        except Exception as e:
            logger.error(f"[OCR] Failed: {e}")
            raise

    def _preprocess_image(self, img: Image.Image) -> Image.Image:
        """Preprocess image for better OCR accuracy."""
        # Convert to grayscale
        if img.mode != 'L':
            img = img.convert('L')
        # Enhance contrast
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.5)
        # Sharpen
        img = img.filter(ImageFilter.SHARPEN)
        # Resize if too small
        w, h = img.size
        if w < 800:
            ratio = 800 / w
            img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)
        return img


# Singleton
ocr_service = OCRService()
