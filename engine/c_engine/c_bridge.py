"""
EssayGrader — C Bridge Module
================================
Python ctypes wrapper for the C shared library (essay_engine.dll/.so).
Provides Python-friendly interface to low-level C matrix operations.

Falls back gracefully to NumPy if the C library is not compiled.
"""

import os
import ctypes
import platform
import numpy as np
from typing import Optional, List, Tuple
import logging

logger = logging.getLogger(__name__)


class CEvalResult(ctypes.Structure):
    """C struct mirror for EvalResult."""
    _fields_ = [
        ('answer_index', ctypes.c_int),
        ('cosine_score', ctypes.c_double),
        ('final_point', ctypes.c_double),
    ]


class EssayCBridge:
    """
    Python bridge to the C shared library for high-performance operations.
    Falls back to NumPy if the C library is unavailable.
    """

    def __init__(self):
        self._lib = None
        self._available = False
        self._load_library()

    def _load_library(self):
        """Attempt to load the compiled C shared library."""
        lib_dir = os.path.dirname(os.path.abspath(__file__))

        system = platform.system()
        if system == 'Windows':
            lib_name = 'essay_engine.dll'
        elif system == 'Linux':
            lib_name = 'essay_engine.so'
        elif system == 'Darwin':
            lib_name = 'essay_engine.dylib'
        else:
            logger.warning(f"[C_BRIDGE] Unsupported platform: {system}")
            return

        lib_path = os.path.join(lib_dir, lib_name)

        if not os.path.exists(lib_path):
            logger.info(f"[C_BRIDGE] Library not found: {lib_path} (using NumPy fallback)")
            return

        try:
            self._lib = ctypes.CDLL(lib_path)
            self._setup_signatures()
            self._available = True
            logger.info(f"[C_BRIDGE] ✓ Loaded C library: {lib_path}")
        except OSError as e:
            logger.warning(f"[C_BRIDGE] Failed to load library: {e}")

    def _setup_signatures(self):
        """Configure C function signatures for ctypes."""
        # dot_product
        self._lib.dot_product.restype = ctypes.c_double
        self._lib.dot_product.argtypes = [
            ctypes.POINTER(ctypes.c_double),
            ctypes.POINTER(ctypes.c_double),
            ctypes.c_int,
        ]

        # l2_norm
        self._lib.l2_norm.restype = ctypes.c_double
        self._lib.l2_norm.argtypes = [
            ctypes.POINTER(ctypes.c_double),
            ctypes.c_int,
        ]

        # normalize_vector_l2
        self._lib.normalize_vector_l2.restype = None
        self._lib.normalize_vector_l2.argtypes = [
            ctypes.POINTER(ctypes.c_double),
            ctypes.c_int,
        ]

        # cosine_similarity (single pair)
        self._lib.cosine_similarity.restype = ctypes.c_double
        self._lib.cosine_similarity.argtypes = [
            ctypes.POINTER(ctypes.c_double),
            ctypes.POINTER(ctypes.c_double),
            ctypes.c_int,
        ]

        # cosine_similarity_batch
        self._lib.cosine_similarity_batch.restype = None
        self._lib.cosine_similarity_batch.argtypes = [
            ctypes.POINTER(ctypes.c_double),
            ctypes.POINTER(ctypes.c_double),
            ctypes.c_int,
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_double),
            ctypes.c_int,
        ]

        # compute_tf
        self._lib.compute_tf.restype = None
        self._lib.compute_tf.argtypes = [
            ctypes.POINTER(ctypes.c_int),
            ctypes.c_int,
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_double),
        ]

        # compute_tfidf_vector
        self._lib.compute_tfidf_vector.restype = None
        self._lib.compute_tfidf_vector.argtypes = [
            ctypes.POINTER(ctypes.c_double),
            ctypes.POINTER(ctypes.c_double),
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_double),
        ]

        # score_to_point
        self._lib.score_to_point.restype = ctypes.c_double
        self._lib.score_to_point.argtypes = [
            ctypes.c_double,
            ctypes.c_double,
        ]

        # batch_evaluate
        self._lib.batch_evaluate.restype = None
        self._lib.batch_evaluate.argtypes = [
            ctypes.POINTER(ctypes.c_double),
            ctypes.POINTER(ctypes.c_double),
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_double,
            ctypes.POINTER(CEvalResult),
        ]

    @property
    def is_available(self) -> bool:
        return self._available

    def _to_c_double_array(self, arr: np.ndarray) -> ctypes.POINTER(ctypes.c_double):
        """Convert NumPy float64 array to C double pointer."""
        arr = np.ascontiguousarray(arr, dtype=np.float64)
        return arr.ctypes.data_as(ctypes.POINTER(ctypes.c_double))

    def _to_c_int_array(self, arr: np.ndarray) -> ctypes.POINTER(ctypes.c_int):
        """Convert NumPy int32 array to C int pointer."""
        arr = np.ascontiguousarray(arr, dtype=np.int32)
        return arr.ctypes.data_as(ctypes.POINTER(ctypes.c_int))

    def cosine_similarity_single(self, a: np.ndarray, b: np.ndarray) -> float:
        """
        Compute cosine similarity between two vectors.

        Args:
            a: First vector (n_dims,)
            b: Second vector (n_dims,)

        Returns:
            Cosine similarity score ∈ [-1, 1]
        """
        if not self._available:
            # NumPy fallback
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            if norm_a < 1e-12 or norm_b < 1e-12:
                return 0.0
            return float(np.dot(a, b) / (norm_a * norm_b))

        n = len(a)
        return self._lib.cosine_similarity(
            self._to_c_double_array(a.flatten()),
            self._to_c_double_array(b.flatten()),
            ctypes.c_int(n),
        )

    def cosine_similarity_batch(self, query: np.ndarray, doc_matrix: np.ndarray,
                                 normalized: bool = False) -> np.ndarray:
        """
        Compute cosine similarity between query and all document vectors.

        Args:
            query: (n_dims,) query vector
            doc_matrix: (n_docs, n_dims) document matrix
            normalized: Whether vectors are L2-normalized

        Returns:
            (n_docs,) array of similarity scores
        """
        if not self._available:
            # NumPy fallback
            if normalized:
                return doc_matrix @ query
            else:
                q_norm = np.linalg.norm(query)
                d_norms = np.linalg.norm(doc_matrix, axis=1)
                dots = doc_matrix @ query
                denom = q_norm * d_norms
                denom[denom < 1e-12] = 1e-12
                return dots / denom

        n_docs, n_dims = doc_matrix.shape
        results = np.zeros(n_docs, dtype=np.float64)

        self._lib.cosine_similarity_batch(
            self._to_c_double_array(query.flatten()),
            self._to_c_double_array(doc_matrix),
            ctypes.c_int(n_docs),
            ctypes.c_int(n_dims),
            self._to_c_double_array(results),
            ctypes.c_int(1 if normalized else 0),
        )

        return results

    def batch_evaluate(self, key_vector: np.ndarray, answer_matrix: np.ndarray,
                        max_point: float) -> List[dict]:
        """
        Batch evaluate student answers against a master key.

        Args:
            key_vector: (n_dims,) master key TF-IDF vector
            answer_matrix: (n_answers, n_dims) student answer TF-IDF matrix
            max_point: Maximum point for this question

        Returns:
            List of {answer_index, cosine_score, final_point} dicts
        """
        if not self._available:
            # NumPy fallback
            results = []
            key_norm = np.linalg.norm(key_vector)
            for i in range(answer_matrix.shape[0]):
                ans = answer_matrix[i]
                ans_norm = np.linalg.norm(ans)
                if key_norm < 1e-12 or ans_norm < 1e-12:
                    cos_score = 0.0
                else:
                    cos_score = float(np.dot(key_vector, ans) / (key_norm * ans_norm))
                cos_score = max(0.0, cos_score)
                final_pt = (cos_score ** 0.7) * max_point
                results.append({
                    'answer_index': i,
                    'cosine_score': round(cos_score, 6),
                    'final_point': round(final_pt, 2),
                })
            return results

        n_answers, n_dims = answer_matrix.shape
        c_results = (CEvalResult * n_answers)()

        self._lib.batch_evaluate(
            self._to_c_double_array(key_vector.flatten()),
            self._to_c_double_array(answer_matrix),
            ctypes.c_int(n_answers),
            ctypes.c_int(n_dims),
            ctypes.c_double(max_point),
            c_results,
        )

        return [
            {
                'answer_index': c_results[i].answer_index,
                'cosine_score': round(c_results[i].cosine_score, 6),
                'final_point': round(c_results[i].final_point, 2),
            }
            for i in range(n_answers)
        ]

    def score_to_point(self, cosine_score: float, max_point: float) -> float:
        """Convert cosine similarity to grade point."""
        if not self._available:
            cs = max(0.0, min(1.0, cosine_score))
            return (cs ** 0.7) * max_point
        return self._lib.score_to_point(
            ctypes.c_double(cosine_score),
            ctypes.c_double(max_point),
        )


# Singleton instance
c_bridge = EssayCBridge()
