/**
 * EssayGrader — Core Math Engine Implementation
 * ================================================
 * High-performance matrix operations for essay evaluation.
 *
 * Compile:
 *   Windows: gcc -O3 -shared -o essay_engine.dll essay_engine.c -lm
 *   Linux:   gcc -O3 -shared -fPIC -o essay_engine.so essay_engine.c -lm
 *
 * References:
 *   Salton & Buckley (1988). "Term-weighting in Automatic Text Retrieval."
 *   Berry, Drmač & Jessup (1999). "Matrices, Vector Spaces, and IR."
 */

#include "essay_engine.h"
#include <math.h>
#include <string.h>
#include <stdlib.h>

/* ============================================================
 * VECTOR OPERATIONS
 * ============================================================ */

EXPORT double dot_product(const double *a, const double *b, int n) {
    double sum = 0.0;
    int i;

    /* Loop unrolling for performance (4-way) */
    int n4 = n - (n % 4);
    for (i = 0; i < n4; i += 4) {
        sum += a[i]   * b[i];
        sum += a[i+1] * b[i+1];
        sum += a[i+2] * b[i+2];
        sum += a[i+3] * b[i+3];
    }
    /* Handle remainder */
    for (; i < n; i++) {
        sum += a[i] * b[i];
    }

    return sum;
}


EXPORT double l2_norm(const double *v, int n) {
    double sum = 0.0;
    int i;

    for (i = 0; i < n; i++) {
        sum += v[i] * v[i];
    }

    return sqrt(sum);
}


EXPORT void normalize_vector_l2(double *v, int n) {
    double norm = l2_norm(v, n);

    if (norm < 1e-12) return;  /* Avoid division by zero */

    double inv_norm = 1.0 / norm;
    int i;
    for (i = 0; i < n; i++) {
        v[i] *= inv_norm;
    }
}


/* ============================================================
 * COSINE SIMILARITY
 * ============================================================
 *
 * cos(θ) = (A · B) / (||A|| × ||B||)
 *
 * For L2-normalized vectors: cos(θ) = A · B  (dot product only)
 * ============================================================ */

EXPORT double cosine_similarity(const double *a, const double *b, int n) {
    double dp = dot_product(a, b, n);
    double norm_a = l2_norm(a, n);
    double norm_b = l2_norm(b, n);

    if (norm_a < 1e-12 || norm_b < 1e-12) {
        return 0.0;
    }

    double result = dp / (norm_a * norm_b);

    /* Clamp to [-1, 1] to handle floating point errors */
    if (result > 1.0) result = 1.0;
    if (result < -1.0) result = -1.0;

    return result;
}


EXPORT void cosine_similarity_batch(
    const double *query_vec,
    const double *doc_matrix,
    int n_docs,
    int n_dims,
    double *results,
    int normalized
) {
    int i;

    if (normalized) {
        /* Optimized path: vectors already L2-normalized, cos = dot product */
        for (i = 0; i < n_docs; i++) {
            results[i] = dot_product(
                query_vec,
                doc_matrix + (i * n_dims),
                n_dims
            );
            /* Clamp */
            if (results[i] > 1.0) results[i] = 1.0;
            if (results[i] < -1.0) results[i] = -1.0;
        }
    } else {
        /* Full cosine similarity computation */
        double query_norm = l2_norm(query_vec, n_dims);

        if (query_norm < 1e-12) {
            memset(results, 0, n_docs * sizeof(double));
            return;
        }

        for (i = 0; i < n_docs; i++) {
            const double *doc = doc_matrix + (i * n_dims);
            double dp = dot_product(query_vec, doc, n_dims);
            double doc_norm = l2_norm(doc, n_dims);

            if (doc_norm < 1e-12) {
                results[i] = 0.0;
            } else {
                results[i] = dp / (query_norm * doc_norm);
                if (results[i] > 1.0) results[i] = 1.0;
                if (results[i] < -1.0) results[i] = -1.0;
            }
        }
    }
}


/* ============================================================
 * TF-IDF COMPUTATION
 * ============================================================ */

EXPORT void compute_tf(
    const int *term_indices,
    int n_words,
    int n_vocab,
    double *tf_out
) {
    int i;

    /* Zero the output vector */
    memset(tf_out, 0, n_vocab * sizeof(double));

    if (n_words == 0) return;

    /* Count term frequencies */
    for (i = 0; i < n_words; i++) {
        int idx = term_indices[i];
        if (idx >= 0 && idx < n_vocab) {
            tf_out[idx] += 1.0;
        }
    }

    /* Normalize by total word count: TF(t,d) = freq(t,d) / |d| */
    double inv_n = 1.0 / (double)n_words;
    for (i = 0; i < n_vocab; i++) {
        tf_out[i] *= inv_n;
    }
}


EXPORT void compute_tfidf_vector(
    const double *tf,
    const double *idf,
    int n_terms,
    double *tfidf_out
) {
    int i;
    for (i = 0; i < n_terms; i++) {
        tfidf_out[i] = tf[i] * idf[i];
    }
}


/* ============================================================
 * SCORING
 * ============================================================
 *
 * Converts cosine similarity to a grade point.
 * Uses a smooth mapping that rewards high similarity more.
 *
 * Thresholds:
 *   cos >= 0.8  →  90-100% of max_point  (Excellent)
 *   cos >= 0.6  →  70-89%  of max_point  (Good)
 *   cos >= 0.4  →  50-69%  of max_point  (Fair)
 *   cos >= 0.2  →  25-49%  of max_point  (Poor)
 *   cos <  0.2  →  0-24%   of max_point  (Very Poor)
 * ============================================================ */

EXPORT double score_to_point(double cosine_score, double max_point) {
    double percentage;

    /* Clamp cosine_score to [0, 1] */
    if (cosine_score < 0.0) cosine_score = 0.0;
    if (cosine_score > 1.0) cosine_score = 1.0;

    /*
     * Smooth mapping using adjusted power curve:
     *   percentage = cosine_score^0.7
     * This gives more generous scores for moderate similarity.
     */
    percentage = pow(cosine_score, 0.7);

    return percentage * max_point;
}


EXPORT void batch_evaluate(
    const double *key_vector,
    const double *answer_matrix,
    int n_answers,
    int n_dims,
    double max_point,
    EvalResult *results
) {
    int i;

    for (i = 0; i < n_answers; i++) {
        const double *answer_vec = answer_matrix + (i * n_dims);

        /* Compute cosine similarity */
        double cos_score = cosine_similarity(key_vector, answer_vec, n_dims);

        /* Ensure non-negative (essay similarity shouldn't be negative) */
        if (cos_score < 0.0) cos_score = 0.0;

        results[i].answer_index = i;
        results[i].cosine_score = cos_score;
        results[i].final_point  = score_to_point(cos_score, max_point);
    }
}
