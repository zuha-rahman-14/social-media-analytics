"""
Image Tamper Detection — CNN + ELA Pipeline

Methods:
  1. Error Level Analysis (ELA)    — JPEG re-compression inconsistencies
  2. Noise Pattern Analysis         — region-by-region noise variance (splicing)
  3. EXIF Metadata Analysis         — editing software traces
  4. CNN Classification             — fine-tuned EfficientNetB3 (production)

Training datasets:
  - CASIA 2.0 Image Tampering Detection Dataset
  - Columbia Uncompressed Image Splicing Dataset
  - NIST Nimble 2016

To use your trained model: place it at models/cnn_tamper_detector.h5
"""
import os
import io
import logging
import numpy as np
from PIL import Image, ImageFilter, ImageChops

logger = logging.getLogger(__name__)


class ImageTamperDetector:
    TAMPER_THRESHOLD = 0.65
    ELA_QUALITY = 90
    IMG_SIZE = (224, 224)

    def __init__(self, model_path=None):
        self.model = None
        self.model_path = model_path or os.path.join('models', 'cnn_tamper_detector.h5')
        self._load_model()

    def _load_model(self):
        """Load trained CNN. Falls back to ELA heuristics if unavailable."""
        try:
            import tensorflow as tf
            if os.path.exists(self.model_path):
                self.model = tf.keras.models.load_model(self.model_path)
                logger.info(f"CNN model loaded: {self.model_path}")
            else:
                logger.warning("CNN model not found — using ELA heuristic pipeline.")
        except ImportError:
            logger.warning("TensorFlow not installed — using ELA heuristic pipeline.")

    def detect(self, image_path):
        """
        Analyze image for tampering.
        Returns: (confidence_score: float 0-1, label: str)
        Labels: 'Authentic', 'Suspicious', 'Likely Tampered'
        """
        if not os.path.exists(image_path):
            return 0.0, "Error: File Not Found"
        try:
            img = Image.open(image_path).convert('RGB')
        except Exception:
            return 0.0, "Error: Cannot Open"

        ela_score = self._ela_analysis(img)
        noise_score = self._noise_analysis(img)
        meta_score = self._metadata_analysis(image_path)

        if self.model:
            cnn_score = self._cnn_predict(img)
            final = 0.50 * cnn_score + 0.30 * ela_score + 0.15 * noise_score + 0.05 * meta_score
        else:
            final = 0.50 * ela_score + 0.35 * noise_score + 0.15 * meta_score

        final = float(np.clip(final, 0.0, 1.0))
        return round(final, 4), self._to_label(final)

    def _ela_analysis(self, img):
        """
        Error Level Analysis: detect compression inconsistencies.
        Tampered regions show higher ELA values than authentic regions.
        """
        try:
            buf = io.BytesIO()
            img.save(buf, 'JPEG', quality=self.ELA_QUALITY)
            buf.seek(0)
            resaved = Image.open(buf).convert('RGB')
            diff = ImageChops.difference(img.resize(resaved.size), resaved)
            arr = np.array(diff, dtype=np.float32)
            score = np.clip(
                arr.mean() / 15.0 * 0.4 + arr.std() / 20.0 * 0.4 + arr.max() / 255.0 * 0.2,
                0, 1
            )
            return float(score)
        except Exception:
            return 0.3

    def _noise_analysis(self, img):
        """
        Detect inconsistent noise patterns — hallmark of image splicing.
        Compares noise variance across image quadrants.
        """
        try:
            gray = np.array(img.convert('L'), dtype=np.float32)
            blurred = np.array(
                img.convert('L').filter(ImageFilter.GaussianBlur(2)), dtype=np.float32
            )
            noise = np.abs(gray - blurred)
            h, w = noise.shape
            quads = [
                noise[:h//2, :w//2], noise[:h//2, w//2:],
                noise[h//2:, :w//2], noise[h//2:, w//2:]
            ]
            variance = float(np.std([q.mean() for q in quads]))
            return float(np.clip(variance / 8.0, 0, 1))
        except Exception:
            return 0.2

    def _metadata_analysis(self, image_path):
        """Check EXIF for editing software traces (Photoshop, GIMP, etc.)."""
        try:
            from PIL.ExifTags import TAGS
            img = Image.open(image_path)
            exif = img._getexif() if hasattr(img, '_getexif') and img._getexif() else {}
            if not exif:
                return 0.4  # Missing EXIF is mildly suspicious
            editors = [
                'photoshop', 'gimp', 'lightroom', 'affinity', 'snapseed',
                'facetune', 'picsart', 'canva', 'meitu', 'vsco'
            ]
            for val in exif.values():
                if isinstance(val, str) and any(e in val.lower() for e in editors):
                    return 0.85
            return 0.1
        except Exception:
            return 0.3

    def _cnn_predict(self, img):
        """
        CNN forward pass.
        Input shape:  (1, 224, 224, 3) — float32, normalized 0-1
        Output:       tampered class probability (index 1)

        Fine-tuning target: EfficientNetB3 / ResNet50 on CASIA2 + Columbia datasets.
        """
        try:
            import tensorflow as tf
            arr = np.array(img.resize(self.IMG_SIZE), dtype=np.float32) / 255.0
            arr = np.expand_dims(arr, 0)
            preds = self.model.predict(arr, verbose=0)
            return float(preds[0][1])
        except Exception as e:
            logger.error(f"CNN predict error: {e}")
            return 0.5

    def generate_ela_map(self, image_path, save_path):
        """
        Save amplified ELA difference map for visual inspection.
        Bright regions = likely edited areas.
        """
        try:
            img = Image.open(image_path).convert('RGB')
            buf = io.BytesIO()
            img.save(buf, 'JPEG', quality=self.ELA_QUALITY)
            buf.seek(0)
            resaved = Image.open(buf).convert('RGB')
            diff = ImageChops.difference(img, resaved)
            amplified = np.clip(np.array(diff, np.float32) * 10, 0, 255).astype(np.uint8)
            Image.fromarray(amplified).save(save_path)
            return True
        except Exception as e:
            logger.error(f"ELA map error: {e}")
            return False

    @staticmethod
    def _to_label(score):
        if score < 0.35:
            return 'Authentic'
        elif score < 0.65:
            return 'Suspicious'
        return 'Likely Tampered'