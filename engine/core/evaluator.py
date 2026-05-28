"""
EssayGrader — Essay Evaluator Module (Hybrid Edition)
======================================================
Core evaluation pipeline combining Semantic (SBERT) and Lexical (TF-IDF)
scoring for accurate, fair essay grading.

Hybrid Scoring Architecture:
    When SBERT is available (Primary Mode):
        Score = w1 × SBERT_Similarity + w2 × Semantic_Keyword_Score
        - SBERT_Similarity: dense vector cosine similarity (captures meaning)
        - Semantic_Keyword_Score: per-concept SBERT matching (ensures coverage)

    When SBERT is unavailable (Fallback Mode):
        Score = Asymmetric Projection Score (TF-IDF)
        proj = (s · k) / ||k||²
        - Does NOT penalize verbose answers (no ||B|| divisor)
        - Only checks how well student covers the key concepts

    Final Point = (Score ^ power) × max_point

Pipeline:
    1. Preprocess all texts (stopword removal, stemming, synonym normalization)
    2. Build unified vocabulary from keys + answers
    3. Transform to TF-IDF vectors
    4. Compute SBERT semantic similarity (if available)
    5. Compute semantic keyword score (per-concept matching)
    6. Combine scores via hybrid formula
    7. Convert similarity → grade points

References:
    Reimers & Gurevych (2019). "Sentence-BERT: Sentence Embeddings
    using Siamese BERT-Networks." EMNLP 2019.
    Salton & Buckley (1988). "Term-weighting in Automatic Text Retrieval."
"""

import re
import numpy as np
import time
import logging
from typing import List, Dict, Optional, Tuple

from .preprocessor import TextPreprocessor
from .vectorizer import EssayVectorizer
from .semantic_model import SemanticModel

logger = logging.getLogger(__name__)

# ============================================================
# HYBRID SCORING WEIGHTS
# ============================================================
# w1: Weight for SBERT sentence-level semantic similarity
# w2: Weight for semantic keyword coverage (per-concept check)
WEIGHT_SBERT = 0.7
WEIGHT_KEYWORD = 0.3

# Power curve exponent for final scoring
# 0.7 = slightly generous (rewards partial correctness)
# 1.0 = linear (strict proportional)
SCORE_POWER = 0.7

# Threshold for semantic keyword match (SBERT cosine similarity)
# A concept segment is considered "matched" if sim >= this threshold
SEMANTIC_KEYWORD_THRESHOLD = 0.55

# Try to import C bridge
try:
    from c_engine.c_bridge import c_bridge
    C_ENGINE_AVAILABLE = c_bridge.is_available
except ImportError:
    C_ENGINE_AVAILABLE = False
    c_bridge = None


class EvaluationResult:
    """Result of evaluating a single student answer."""

    def __init__(self, student_name: str, question_id: int, answer_id: int,
                 cosine_score: float, final_point: float, max_point: float,
                 matched_keywords: List[str], missing_keywords: List[str],
                 confidence: float, computation_time_ms: int):
        self.student_name = student_name
        self.question_id = question_id
        self.answer_id = answer_id
        self.cosine_score = round(cosine_score, 6)
        self.final_point = round(final_point, 2)
        self.max_point = max_point
        self.matched_keywords = matched_keywords
        self.missing_keywords = missing_keywords
        self.confidence = round(confidence, 4)
        self.computation_time_ms = computation_time_ms
        self.percentage = round((final_point / max_point * 100) if max_point > 0 else 0, 1)

    def to_dict(self):
        return {
            'student_name': self.student_name,
            'question_id': self.question_id,
            'answer_id': self.answer_id,
            'cosine_score': self.cosine_score,
            'final_point': self.final_point,
            'max_point': self.max_point,
            'percentage': self.percentage,
            'matched_keywords': self.matched_keywords,
            'missing_keywords': self.missing_keywords,
            'confidence': self.confidence,
            'computation_time_ms': self.computation_time_ms,
            'grade': self._get_grade(),
        }

    def _get_grade(self) -> str:
        if self.percentage >= 85: return 'A'
        if self.percentage >= 75: return 'B'
        if self.percentage >= 60: return 'C'
        if self.percentage >= 40: return 'D'
        return 'E'


# ============================================================
# HELPER: Split key text into concept segments
# ============================================================
def _split_into_concepts(text: str) -> List[str]:
    """
    Split a key answer into meaningful concept segments.

    Splits on sentence boundaries (., ;, !) and clause boundaries (,)
    then filters out segments that are too short to be meaningful.

    Example:
        "Fotosintesis adalah proses pembuatan makanan oleh tumbuhan hijau,
         menggunakan cahaya matahari, air, dan karbondioksida.
         Proses ini menghasilkan glukosa dan oksigen."
        →
        ["Fotosintesis adalah proses pembuatan makanan oleh tumbuhan hijau",
         "menggunakan cahaya matahari",
         "air dan karbondioksida",
         "Proses ini menghasilkan glukosa dan oksigen"]
    """
    if not text or not text.strip():
        return []

    # Split on sentence-level delimiters first
    sentences = re.split(r'[.;!?\n]+', text)

    concepts = []
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        # For longer sentences, split on commas to get finer concepts
        if len(sentence.split()) > 8:
            parts = re.split(r',\s*', sentence)
            for part in parts:
                part = part.strip()
                # Filter out very short connector-only segments
                if len(part.split()) >= 3:
                    concepts.append(part)
                elif concepts and len(part.split()) >= 1:
                    # Append short fragments to previous concept
                    concepts[-1] = concepts[-1] + ', ' + part
        else:
            if len(sentence.split()) >= 2:
                concepts.append(sentence)

    return concepts if concepts else [text.strip()]


class EssayEvaluator:
    """
    Core essay evaluation engine with Hybrid Scoring.

    Orchestrates the full pipeline from raw text to graded scores,
    combining SBERT semantic understanding with keyword coverage analysis.
    """

    def __init__(self):
        self.preprocessor = TextPreprocessor()
        self.vectorizer = EssayVectorizer()
        self._is_ready = False

    @property
    def is_ready(self): return self._is_ready

    # ============================================================
    # SEMANTIC KEYWORD SCORING
    # ============================================================
    def _compute_semantic_keyword_score(
        self, key_text: str, answer_text: str,
        semantic_model: 'SemanticModel'
    ) -> Tuple[float, List[str], List[str]]:
        """
        Compute semantic keyword coverage by checking if each concept
        in the key answer is semantically present in the student answer.

        Instead of exact token matching, this uses SBERT to check if
        each concept segment from the key answer has a semantic match
        in the student's full response.

        Args:
            key_text: Master key answer (original text)
            answer_text: Student answer (original text)
            semantic_model: SBERT model instance

        Returns:
            (score, matched_concepts, missing_concepts)
            score ∈ [0, 1]: ratio of concepts covered
        """
        if not answer_text or not answer_text.strip():
            concepts = _split_into_concepts(key_text)
            return 0.0, [], [c[:50] for c in concepts]

        concepts = _split_into_concepts(key_text)
        if not concepts:
            return 0.0, [], []

        matched = []
        missing = []

        # Encode all concepts + the full answer in one batch for efficiency
        all_texts = concepts + [answer_text]
        vectors = semantic_model.encode_batch(all_texts)

        if vectors is None:
            # SBERT encoding failed, return 0
            return 0.0, [], [c[:50] for c in concepts]

        answer_vec = vectors[-1]  # Last vector is the answer
        concept_vecs = vectors[:-1]  # All others are concepts

        for i, concept in enumerate(concepts):
            # Cosine similarity between concept and full answer
            sim = float(np.dot(concept_vecs[i], answer_vec))
            sim = max(0.0, min(1.0, sim))

            # Truncate concept text for display
            display_text = concept[:50] + ('...' if len(concept) > 50 else '')

            if sim >= SEMANTIC_KEYWORD_THRESHOLD:
                matched.append(display_text)
            else:
                missing.append(display_text)

        total = len(concepts)
        score = len(matched) / total if total > 0 else 0.0

        return score, matched, missing

    def _compute_lexical_keyword_score(
        self, key_tokens: List[str], ans_tokens: List[str]
    ) -> Tuple[float, List[str], List[str]]:
        """
        Compute lexical keyword coverage (fallback when SBERT unavailable).
        Uses stemmed token matching via the vectorizer.
        """
        kw = self.vectorizer.get_keyword_analysis(key_tokens, ans_tokens)
        return kw['match_ratio'], kw['matched'], kw['missing']

    # ============================================================
    # BATCH EVALUATION (Multiple Students, One Question)
    # ============================================================
    def evaluate_question(self, key_text: str, answers: List[Dict],
                          max_point: float = 10.0) -> List[EvaluationResult]:
        """
        Evaluate all student answers for a single question.

        Args:
            key_text: Master key answer text
            answers: List of {id, student_name, raw_text, question_id}
            max_point: Maximum point for this question

        Returns:
            List of EvaluationResult objects
        """
        start_time = time.time()

        # Step 1: Preprocess
        key_tokens = self.preprocessor.get_tokens(key_text)
        answer_data = []
        for ans in answers:
            tokens = self.preprocessor.get_tokens(ans.get('raw_text', ''))
            answer_data.append({
                'id': ans.get('id', 0),
                'student_name': ans.get('student_name', 'Unknown'),
                'tokens': tokens,
                'raw_text': ans.get('raw_text', ''),
                'question_id': ans.get('question_id', 0),
            })

        if not key_tokens:
            logger.warning("[EVALUATOR] Master key is empty after preprocessing")
            return []

        # Step 2: Build vocabulary from ALL texts
        all_docs = [key_tokens] + [a['tokens'] for a in answer_data]
        self.vectorizer.fit(all_docs)

        # Step 3: Transform to TF-IDF vectors
        key_vector = self.vectorizer.transform(key_tokens)
        answer_vectors = []
        for a in answer_data:
            answer_vectors.append(self.vectorizer.transform(a['tokens']))

        if not answer_vectors:
            return []

        answer_matrix = np.array(answer_vectors)

        # Step 4: Get Semantic Model
        semantic_model = SemanticModel.get_instance()
        sbert_available = semantic_model.is_available

        # Compute SBERT similarity for all answers at once
        sbert_scores = [0.0] * len(answer_data)
        if sbert_available:
            sbert_scores = semantic_model.similarity_matrix(
                key_text, [a['raw_text'] for a in answer_data]
            )

        # Step 5: Compute Hybrid Score for each answer
        results = []
        for i, a in enumerate(answer_data):
            ans_vec = answer_matrix[i]
            raw_text = a['raw_text']

            if sbert_available:
                # === HYBRID MODE ===
                # Component 1: SBERT sentence-level similarity
                semantic_score = sbert_scores[i]

                # Component 2: Semantic keyword coverage
                kw_score, kw_matched, kw_missing = \
                    self._compute_semantic_keyword_score(
                        key_text, raw_text, semantic_model
                    )

                # Hybrid combination
                cos_score = (WEIGHT_SBERT * semantic_score) + (WEIGHT_KEYWORD * kw_score)

            else:
                # === FALLBACK MODE: Asymmetric Projection ===
                # Use projection score instead of standard cosine
                cos_score = self.vectorizer.get_projection_score(key_vector, ans_vec)

                # Lexical keyword analysis
                kw_score, kw_matched, kw_missing = \
                    self._compute_lexical_keyword_score(key_tokens, a['tokens'])

            # Clamp to [0, 1]
            cos_score = max(0.0, min(1.0, cos_score))

            # Convert to point with power curve
            final_pt = (cos_score ** SCORE_POWER) * max_point

            # Clamp final point
            final_pt = max(0.0, min(max_point, final_pt))

            # Confidence calculation
            if len(a['tokens']) == 0:
                confidence = 0.0
            else:
                len_ratio = min(len(a['tokens']) / max(len(key_tokens), 1), 2.0) / 2.0
                if sbert_available:
                    # High SBERT score + keyword coverage = high confidence
                    confidence = (semantic_score * 0.5 + kw_score * 0.3 + len_ratio * 0.2)
                else:
                    confidence = (kw_score * 0.7 + len_ratio * 0.3)

            comp_time = int((time.time() - start_time) * 1000)

            results.append(EvaluationResult(
                student_name=a['student_name'],
                question_id=a['question_id'],
                answer_id=a['id'],
                cosine_score=cos_score,
                final_point=final_pt,
                max_point=max_point,
                matched_keywords=kw_matched,
                missing_keywords=kw_missing,
                confidence=confidence,
                computation_time_ms=comp_time,
            ))

        self._is_ready = True
        total_time = int((time.time() - start_time) * 1000)
        mode = "Hybrid (SBERT + Semantic Keywords)" if sbert_available else "Fallback (TF-IDF Projection)"
        logger.info(f"[EVALUATOR] Evaluated {len(results)} answers in {total_time}ms [{mode}]")
        return results

    # ============================================================
    # SINGLE EVALUATION (Live Preview with full process breakdown)
    # ============================================================
    def evaluate_single(self, key_text: str, answer_text: str,
                        max_point: float = 10.0) -> Dict:
        """
        Quick evaluation of a single answer (for live preview).
        Returns full computation breakdown for displaying the linear algebra process.
        """
        key_tokens = self.preprocessor.get_tokens(key_text)
        ans_tokens = self.preprocessor.get_tokens(answer_text)

        if not key_tokens:
            return {'cosine_score': 0, 'final_point': 0, 'max_point': max_point,
                    'percentage': 0, 'grade': 'E', 'matched': [], 'missing': [],
                    'process': None}

        self.vectorizer.fit([key_tokens, ans_tokens])

        # Get detailed TF-IDF breakdown
        key_detailed = self.vectorizer.transform_detailed(key_tokens)
        ans_detailed = self.vectorizer.transform_detailed(ans_tokens)

        key_vec = key_detailed['vector']
        ans_vec = ans_detailed['vector']

        # Get SBERT score
        semantic_model = SemanticModel.get_instance()
        sbert_available = semantic_model.is_available
        semantic_score = semantic_model.similarity(key_text, answer_text) if sbert_available else 0.0

        # Compute lexical cosine similarity (for display purposes)
        dot_product = float(np.dot(key_vec, ans_vec))
        norm_k = float(np.linalg.norm(key_vec))
        norm_a = float(np.linalg.norm(ans_vec))

        if norm_k < 1e-12 or norm_a < 1e-12:
            lexical_score = 0.0
        else:
            lexical_score = dot_product / (norm_k * norm_a)
        lexical_score = max(0.0, lexical_score)

        # Compute projection score (for fallback / display)
        projection_score = self.vectorizer.get_projection_score(key_vec, ans_vec)

        # Compute keyword analysis
        if sbert_available:
            # Semantic keyword matching
            keyword_score, kw_matched, kw_missing = \
                self._compute_semantic_keyword_score(
                    key_text, answer_text, semantic_model
                )
        else:
            # Lexical keyword matching
            kw_analysis = self.vectorizer.get_keyword_analysis(key_tokens, ans_tokens)
            keyword_score = kw_analysis['match_ratio']
            kw_matched = kw_analysis['matched']
            kw_missing = kw_analysis['missing']

        # Compute final hybrid/fallback score
        if sbert_available:
            cos = (WEIGHT_SBERT * semantic_score) + (WEIGHT_KEYWORD * keyword_score)
        else:
            cos = projection_score  # Use asymmetric projection for fallback

        # Clamp
        cos = max(0.0, min(1.0, cos))

        pt = (cos ** SCORE_POWER) * max_point
        pt = max(0.0, min(max_point, pt))
        pct = (pt / max_point * 100) if max_point > 0 else 0

        grade = 'A' if pct >= 85 else 'B' if pct >= 75 else 'C' if pct >= 60 else 'D' if pct >= 40 else 'E'

        # Build the linear algebra process data
        vocabulary = self.vectorizer.feature_names

        # Build TF-IDF comparison table
        tfidf_table = []
        for i, term in enumerate(vocabulary):
            key_entry = key_detailed['terms'][i] if i < len(key_detailed['terms']) else {}
            ans_entry = ans_detailed['terms'][i] if i < len(ans_detailed['terms']) else {}
            tfidf_table.append({
                'term': term,
                'key_tf': key_entry.get('tf', 0),
                'key_idf': key_entry.get('idf', 0),
                'key_tfidf': key_entry.get('tfidf', 0),
                'key_tfidf_norm': key_entry.get('tfidf_normalized', 0),
                'ans_tf': ans_entry.get('tf', 0),
                'ans_idf': ans_entry.get('idf', 0),
                'ans_tfidf': ans_entry.get('tfidf', 0),
                'ans_tfidf_norm': ans_entry.get('tfidf_normalized', 0),
                'product': round(key_entry.get('tfidf_normalized', 0) * ans_entry.get('tfidf_normalized', 0), 6),
            })

        process = {
            'step1_preprocessing': {
                'key_original': key_text,
                'key_tokens': key_tokens,
                'answer_original': answer_text,
                'answer_tokens': ans_tokens,
            },
            'step2_vocabulary': vocabulary,
            'step3_tfidf_table': tfidf_table,
            'step4_vectors': {
                'key_vector': [round(float(v), 6) for v in key_vec],
                'answer_vector': [round(float(v), 6) for v in ans_vec],
                'key_norm': round(norm_k, 6),
                'answer_norm': round(norm_a, 6),
            },
            'step5_hybrid_scoring': {
                'semantic_score': round(semantic_score, 4),
                'keyword_score': round(keyword_score, 4),
                'keyword_type': 'semantic' if sbert_available else 'lexical',
                'weight_sbert': WEIGHT_SBERT,
                'weight_keyword': WEIGHT_KEYWORD,
                'lexical_score_fallback': round(lexical_score, 4),
                'projection_score_fallback': round(projection_score, 4),
                'is_hybrid': sbert_available,
                'cosine_score': round(cos, 6),
                'formula': (
                    f"Nilai Dasar = ({WEIGHT_SBERT} × {round(semantic_score, 4)}) + "
                    f"({WEIGHT_KEYWORD} × {round(keyword_score, 4)}) = {round(cos, 4)}"
                    if sbert_available else
                    f"Menggunakan Proyeksi Vektor Asimetris (s·k / ||k||²) = {round(projection_score, 4)}"
                ),
            },
            'step6_scoring': {
                'cosine_score': round(cos, 6),
                'power': SCORE_POWER,
                'max_point': max_point,
                'final_point': round(pt, 2),
                'percentage': round(pct, 1),
                'formula': f"Nilai Akhir = ({round(cos, 4)})^{SCORE_POWER} × {max_point} = {round(pt, 2)}",
            },
        }

        return {
            'cosine_score': round(cos, 6), 'final_point': round(pt, 2),
            'max_point': max_point, 'percentage': round(pct, 1), 'grade': grade,
            'matched': kw_matched, 'missing': kw_missing,
            'key_cleaned': ' '.join(key_tokens), 'answer_cleaned': ' '.join(ans_tokens),
            'vocab_size': self.vectorizer.vocab_size,
            'process': process,
        }
