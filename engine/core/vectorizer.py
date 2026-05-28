"""
EssayGrader — TF-IDF Vectorizer Module
========================================
Constructs TF-IDF vectors for essay text comparison.

References:
    Salton & Buckley (1988). "Term-weighting in Automatic Text Retrieval."
"""

import numpy as np
from typing import List, Dict, Optional, Set
from collections import Counter
import math
import logging

logger = logging.getLogger(__name__)


class EssayVectorizer:
    """Custom TF-IDF vectorizer for essay evaluation."""

    def __init__(self, min_df=1, use_idf=True, sublinear_tf=True, norm='l2'):
        self.min_df = min_df
        self.use_idf = use_idf
        self.sublinear_tf = sublinear_tf
        self.norm = norm
        self._vocabulary: Dict[str, int] = {}
        self._idf: Optional[np.ndarray] = None
        self._is_fitted = False
        self._n_documents = 0

    @property
    def vocabulary(self): return self._vocabulary

    @property
    def vocab_size(self): return len(self._vocabulary)

    @property
    def feature_names(self):
        if not self._is_fitted: return []
        inv = {v: k for k, v in self._vocabulary.items()}
        return [inv[i] for i in range(len(self._vocabulary))]

    def fit(self, documents: List[List[str]]) -> 'EssayVectorizer':
        """Build vocabulary and IDF from tokenized documents."""
        if not documents:
            raise ValueError("Cannot fit on empty document list.")
        term_doc_freq: Dict[str, int] = Counter()
        for doc_tokens in documents:
            for term in set(doc_tokens):
                term_doc_freq[term] += 1
        vocab_terms = sorted([t for t, df in term_doc_freq.items() if df >= self.min_df])
        self._vocabulary = {term: idx for idx, term in enumerate(vocab_terms)}
        self._n_documents = len(documents)
        if self.use_idf:
            n = len(documents)
            self._idf = np.zeros(len(self._vocabulary))
            for term, idx in self._vocabulary.items():
                df = term_doc_freq.get(term, 0)
                self._idf[idx] = math.log(n / (1 + df)) + 1.0
        else:
            self._idf = np.ones(len(self._vocabulary))
        self._is_fitted = True
        logger.info(f"[VECTORIZER] Vocabulary: {len(self._vocabulary)} terms from {len(documents)} docs")
        return self

    def transform(self, tokens: List[str]) -> np.ndarray:
        """Transform tokens into a TF-IDF vector."""
        if not self._is_fitted:
            raise RuntimeError("Vectorizer not fitted.")
        n_terms = len(self._vocabulary)
        tfidf = np.zeros(n_terms)
        if not tokens: return tfidf
        term_counts = Counter(tokens)
        total = len(tokens)
        for term, count in term_counts.items():
            if term in self._vocabulary:
                idx = self._vocabulary[term]
                tf = count / total
                if self.sublinear_tf:
                    tf = math.log(1 + count)
                tfidf[idx] = tf * self._idf[idx]
        if self.norm == 'l2':
            norm_val = np.linalg.norm(tfidf)
            if norm_val > 1e-12:
                tfidf /= norm_val
        return tfidf

    def transform_detailed(self, tokens: List[str]) -> Dict:
        """
        Transform tokens into TF-IDF vector WITH full computation breakdown.
        Returns raw TF, IDF, and TF-IDF values per term for display.

        Returns:
            Dict with keys:
                'vector': np.ndarray (final TF-IDF vector)
                'terms': List of term details [{term, tf_raw, tf, idf, tfidf, tfidf_normalized}]
                'norm': L2 norm of the unnormalized vector
        """
        if not self._is_fitted:
            raise RuntimeError("Vectorizer not fitted.")
        n_terms = len(self._vocabulary)
        tfidf_raw = np.zeros(n_terms)
        term_details = []

        if not tokens:
            return {'vector': tfidf_raw, 'terms': [], 'norm': 0.0}

        term_counts = Counter(tokens)
        total = len(tokens)
        inv_vocab = {v: k for k, v in self._vocabulary.items()}

        for idx in range(n_terms):
            term = inv_vocab[idx]
            count = term_counts.get(term, 0)
            tf_raw = count / total if total > 0 else 0
            if self.sublinear_tf:
                tf = math.log(1 + count) if count > 0 else 0
            else:
                tf = tf_raw
            idf = self._idf[idx]
            tfidf_val = tf * idf
            tfidf_raw[idx] = tfidf_val

            if count > 0 or True:  # Include all vocab terms
                term_details.append({
                    'term': term,
                    'count': count,
                    'tf_raw': round(tf_raw, 6),
                    'tf': round(tf, 6),
                    'idf': round(idf, 6),
                    'tfidf': round(tfidf_val, 6),
                })

        norm_val = float(np.linalg.norm(tfidf_raw))
        tfidf_normalized = tfidf_raw.copy()
        if self.norm == 'l2' and norm_val > 1e-12:
            tfidf_normalized /= norm_val

        # Add normalized values to term details
        for i, detail in enumerate(term_details):
            detail['tfidf_normalized'] = round(float(tfidf_normalized[i]), 6)

        return {
            'vector': tfidf_normalized,
            'terms': term_details,
            'norm': round(norm_val, 6),
        }

    def transform_batch(self, documents: List[List[str]]) -> np.ndarray:
        """Transform multiple tokenized documents into TF-IDF matrix."""
        matrix = np.zeros((len(documents), len(self._vocabulary)))
        for i, tokens in enumerate(documents):
            matrix[i] = self.transform(tokens)
        return matrix

    def get_keyword_analysis(self, key_tokens: List[str], answer_tokens: List[str]) -> Dict:
        """Analyze keyword matches between master key and student answer."""
        key_set = {t for t in set(key_tokens) if t in self._vocabulary}
        ans_set = {t for t in set(answer_tokens) if t in self._vocabulary}
        matched = key_set & ans_set
        missing = key_set - ans_set
        extra = ans_set - key_set
        total = len(key_set) if key_set else 1
        return {
            'matched': sorted(matched), 'missing': sorted(missing),
            'extra': sorted(extra), 'match_ratio': len(matched) / total,
            'total_key_terms': len(key_set), 'total_answer_terms': len(ans_set),
        }

    def get_projection_score(self, key_vector: np.ndarray, answer_vector: np.ndarray) -> float:
        """
        Compute asymmetric projection score: proj = (s · k) / ||k||²

        Unlike standard cosine similarity which divides by ||A||×||B||,
        this projection-based score only normalizes by the key vector's
        magnitude. This means:
        - Long student answers are NOT penalized (no ||B|| divisor)
        - As long as the answer contains the key components, score stays high
        - Score is clamped to [0, 1] for safety

        Mathematical Foundation:
            Standard Cosine:  cos(θ) = (A·B) / (||A|| × ||B||)
            Projection Score: proj   = (s·k) / ||k||²

        Args:
            key_vector: TF-IDF vector of the master key (already L2-normalized)
            answer_vector: TF-IDF vector of student answer (already L2-normalized)

        Returns:
            Projection score ∈ [0, 1]
        """
        norm_k_sq = float(np.dot(key_vector, key_vector))
        if norm_k_sq < 1e-12:
            return 0.0
        proj = float(np.dot(answer_vector, key_vector)) / norm_k_sq
        return max(0.0, min(1.0, proj))

    def get_stats(self):
        if not self._is_fitted: return {'status': 'not_fitted'}
        return {'status': 'fitted', 'vocab_size': len(self._vocabulary),
                'n_documents': self._n_documents}
