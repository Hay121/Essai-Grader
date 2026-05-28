/**
 * EssayGrader — Core Math Engine (C Library)
 * =============================================
 * High-performance vector operations for essay evaluation.
 * Compiled to .dll (Windows) or .so (Linux) and called via Python ctypes.
 *
 * Functions:
 *   - dot_product:              Compute dot product of two vectors
 *   - l2_norm:                  Compute L2 (Euclidean) norm
 *   - normalize_vector_l2:     Normalize vector to unit length
 *   - cosine_similarity:       Single pair cosine similarity
 *   - cosine_similarity_batch: Batch cosine similarity (1 query vs N docs)
 *   - compute_tf:              Term Frequency computation
 *   - compute_tfidf_vector:    TF-IDF vector from term frequencies
 *   - score_to_point:          Convert cosine score to final grade point
 *
 * Compile:
 *   Windows: gcc -O3 -shared -o essay_engine.dll essay_engine.c -lm
 *   Linux:   gcc -O3 -shared -fPIC -o essay_engine.so essay_engine.c -lm
 *
 * Mathematical Foundation:
 *   Cosine Similarity: cos(θ) = (A · B) / (||A|| × ||B||)
 *   TF(t,d)  = freq(t,d) / max_freq(d)
 *   IDF(t)   = log(N / df(t))
 *   TF-IDF   = TF × IDF
 *
 * References:
 *   Salton & Buckley (1988). "Term-weighting in Automatic Text Retrieval."
 *   Berry, Drmač & Jessup (1999). "Matrices, Vector Spaces, and IR."
 */

#ifndef ESSAY_ENGINE_H
#define ESSAY_ENGINE_H

#ifdef _WIN32
    #define EXPORT __declspec(dllexport)
#else
    #define EXPORT __attribute__((visibility("default")))
#endif

/**
 * Result structure for a single evaluation score.
 */
typedef struct {
    int   answer_index;
    double cosine_score;
    double final_point;
} EvalResult;

/* ============================================================
 * VECTOR OPERATIONS
 * ============================================================ */

/**
 * Compute dot product of two vectors: a · b = Σ(a_i × b_i)
 *
 * @param a     First vector
 * @param b     Second vector
 * @param n     Vector dimension
 * @return      Dot product value
 */
EXPORT double dot_product(const double *a, const double *b, int n);

/**
 * Compute L2 norm: ||v|| = sqrt(Σ(v_i²))
 *
 * @param v     Input vector
 * @param n     Vector dimension
 * @return      L2 norm value
 */
EXPORT double l2_norm(const double *v, int n);

/**
 * Normalize vector to unit length (in-place).
 * After normalization: ||v|| = 1
 *
 * @param v     Vector to normalize (modified in-place)
 * @param n     Vector dimension
 */
EXPORT void normalize_vector_l2(double *v, int n);

/* ============================================================
 * COSINE SIMILARITY
 * ============================================================ */

/**
 * Compute cosine similarity between two vectors.
 *
 * cos(θ) = (a · b) / (||a|| × ||b||)
 *
 * @param a     First vector
 * @param b     Second vector
 * @param n     Vector dimension
 * @return      Cosine similarity ∈ [-1, 1]
 */
EXPORT double cosine_similarity(const double *a, const double *b, int n);

/**
 * Batch cosine similarity: one query vector vs many document vectors.
 *
 * @param query_vec     Query vector (1 × n_dims)
 * @param doc_matrix    Document matrix (n_docs × n_dims), row-major
 * @param n_docs        Number of documents
 * @param n_dims        Vector dimensionality
 * @param results       Output array of similarity scores (pre-allocated, size n_docs)
 * @param normalized    1 if vectors are already L2-normalized, 0 otherwise
 */
EXPORT void cosine_similarity_batch(
    const double *query_vec,
    const double *doc_matrix,
    int n_docs,
    int n_dims,
    double *results,
    int normalized
);

/* ============================================================
 * TF-IDF COMPUTATION
 * ============================================================ */

/**
 * Compute Term Frequency for a single document.
 * TF(t,d) = freq(t,d) / total_terms_in_d
 *
 * @param term_indices  Array of vocabulary indices for each word in document
 * @param n_words       Number of words in document
 * @param n_vocab       Total vocabulary size
 * @param tf_out        Output TF vector (pre-allocated, size n_vocab)
 */
EXPORT void compute_tf(
    const int *term_indices,
    int n_words,
    int n_vocab,
    double *tf_out
);

/**
 * Compute TF-IDF vector from TF and IDF vectors.
 * tfidf[i] = tf[i] × idf[i]
 *
 * @param tf        Term frequency vector
 * @param idf       Inverse document frequency vector
 * @param n_terms   Vocabulary size
 * @param tfidf_out Output TF-IDF vector (pre-allocated)
 */
EXPORT void compute_tfidf_vector(
    const double *tf,
    const double *idf,
    int n_terms,
    double *tfidf_out
);

/* ============================================================
 * SCORING
 * ============================================================ */

/**
 * Convert cosine similarity score to final grade point.
 * Applies threshold-based scaling.
 *
 * @param cosine_score  Raw cosine similarity ∈ [0, 1]
 * @param max_point     Maximum point for this question
 * @return              Final grade point ∈ [0, max_point]
 */
EXPORT double score_to_point(double cosine_score, double max_point);

/**
 * Batch evaluate: compute scores for multiple student answers
 * against a single master key vector.
 *
 * @param key_vector       Master key TF-IDF vector (1 × n_dims)
 * @param answer_matrix    Student answer matrix (n_answers × n_dims), row-major
 * @param n_answers        Number of student answers
 * @param n_dims           Vector dimensionality
 * @param max_point        Maximum point for this question
 * @param results          Output array of EvalResult (pre-allocated, size n_answers)
 */
EXPORT void batch_evaluate(
    const double *key_vector,
    const double *answer_matrix,
    int n_answers,
    int n_dims,
    double max_point,
    EvalResult *results
);

#endif /* ESSAY_ENGINE_H */
