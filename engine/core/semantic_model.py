"""
EssayGrader — Semantic Model Module (SBERT)
=============================================
Singleton wrapper for Sentence-BERT that provides dense vector
representations for semantic similarity computation.

Architecture:
    Uses the 'paraphrase-multilingual-MiniLM-L12-v2' model which
    supports 50+ languages including Indonesian (Bahasa Indonesia).
    Each sentence is encoded into a 384-dimensional dense vector
    in a semantic space where meaning proximity = vector proximity.

Mathematical Foundation:
    Given key vector k and student vector s (both ∈ ℝ^384):
    Semantic Similarity = cos(θ) = (k · s) / (‖k‖ × ‖s‖)

    Unlike TF-IDF (sparse, lexical), SBERT vectors capture:
    - Paraphrase equivalence ("membuat makanan" ≈ "menghasilkan glukosa")
    - Scientific synonym bridging ("cahaya" ≈ "foton" ≈ "radiasi elektromagnetik")
    - Conceptual similarity across different writing styles

References:
    Reimers & Gurevych (2019). "Sentence-BERT: Sentence Embeddings
    using Siamese BERT-Networks." EMNLP 2019.
"""

import logging
import numpy as np
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)

# Global singleton
_model_instance = None
_model_available = False


class SemanticModel:
    """
    Singleton SBERT wrapper for semantic text understanding.

    Loads the multilingual MiniLM model once into memory and provides
    efficient encoding and similarity computation.

    Usage:
        model = SemanticModel.get_instance()
        if model.is_available:
            sim = model.similarity("tumbuhan membuat makanan",
                                    "proses anabolisme kloroplas")
            # → ~0.85 (high semantic similarity despite zero word overlap)
    """

    # Model configuration
    MODEL_NAME = 'paraphrase-multilingual-MiniLM-L12-v2'
    VECTOR_DIM = 384  # Output dimension of MiniLM

    def __init__(self):
        self._model = None
        self._available = False
        self._load_model()

    @classmethod
    def get_instance(cls) -> 'SemanticModel':
        """Get or create the singleton model instance."""
        global _model_instance
        if _model_instance is None:
            _model_instance = cls()
        return _model_instance

    @property
    def is_available(self) -> bool:
        """Whether the SBERT model is loaded and ready."""
        return self._available

    @property
    def model_name(self) -> str:
        return self.MODEL_NAME

    def _load_model(self):
        """
        Attempt to load the SBERT model.
        Falls back gracefully if dependencies are missing.
        """
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"[SBERT] Loading model: {self.MODEL_NAME}...")
            self._model = SentenceTransformer(self.MODEL_NAME)
            self._available = True
            logger.info(f"[SBERT] ✓ Model loaded successfully ({self.VECTOR_DIM}D vectors)")
        except ImportError:
            logger.warning(
                "[SBERT] ✗ sentence-transformers not installed. "
                "Falling back to TF-IDF only. "
                "Install with: pip install sentence-transformers"
            )
        except Exception as e:
            logger.warning(f"[SBERT] ✗ Failed to load model: {e}")

    def encode(self, text: str) -> Optional[np.ndarray]:
        """
        Encode a single text into a dense semantic vector.

        Args:
            text: Input text (any language supported by MiniLM)

        Returns:
            np.ndarray of shape (384,) or None if model unavailable
        """
        if not self._available or not text or not text.strip():
            return None
        try:
            vector = self._model.encode(text, convert_to_numpy=True,
                                         normalize_embeddings=True)
            return vector.astype(np.float64)
        except Exception as e:
            logger.error(f"[SBERT] Encoding error: {e}")
            return None

    def encode_batch(self, texts: List[str]) -> Optional[np.ndarray]:
        """
        Encode multiple texts into dense vectors (batch processing).

        Args:
            texts: List of input texts

        Returns:
            np.ndarray of shape (n_texts, 384) or None
        """
        if not self._available or not texts:
            return None
        try:
            vectors = self._model.encode(texts, convert_to_numpy=True,
                                          normalize_embeddings=True,
                                          batch_size=32,
                                          show_progress_bar=False)
            return vectors.astype(np.float64)
        except Exception as e:
            logger.error(f"[SBERT] Batch encoding error: {e}")
            return None

    def similarity(self, text_a: str, text_b: str) -> float:
        """
        Compute semantic similarity between two texts.

        Uses cosine similarity on normalized SBERT embeddings.
        Since embeddings are L2-normalized, this is just the dot product.

        Args:
            text_a: First text
            text_b: Second text

        Returns:
            Similarity score ∈ [0, 1] (clamped from [-1, 1])
        """
        vec_a = self.encode(text_a)
        vec_b = self.encode(text_b)

        if vec_a is None or vec_b is None:
            return 0.0

        # Vectors are already L2-normalized, so dot product = cosine similarity
        cos_sim = float(np.dot(vec_a, vec_b))
        return max(0.0, min(1.0, cos_sim))

    def similarity_matrix(self, key_text: str,
                           answer_texts: List[str]) -> List[float]:
        """
        Compute similarity between one key and multiple answers efficiently.

        Args:
            key_text: Master key answer
            answer_texts: List of student answers

        Returns:
            List of similarity scores
        """
        if not self._available:
            return [0.0] * len(answer_texts)

        all_texts = [key_text] + answer_texts
        vectors = self.encode_batch(all_texts)

        if vectors is None:
            return [0.0] * len(answer_texts)

        key_vec = vectors[0]
        scores = []
        for i in range(1, len(vectors)):
            sim = float(np.dot(key_vec, vectors[i]))
            scores.append(max(0.0, min(1.0, sim)))
        return scores

    def get_status(self) -> dict:
        """Get model status information."""
        return {
            'available': self._available,
            'model_name': self.MODEL_NAME,
            'vector_dim': self.VECTOR_DIM,
            'engine': 'sentence-transformers',
        }
