-- ============================================================
-- ESSAYGRADER: Sistem Koreksi Jawaban Esai Otomatis
-- Database Schema v1.0 (SQLite Compatible)
-- ============================================================
-- Mathematical Foundation:
--   Cosine Similarity: cos(θ) = (A·B) / (||A|| ||B||)
--   TF-IDF Weighting:  w(t,d) = tf(t,d) × log(N/df(t))
--
-- References:
--   Salton & Buckley (1988) "Term-weighting in Automatic Text Retrieval"
--   Deerwester et al. (1990) "Indexing by Latent Semantic Analysis"
-- ============================================================

-- ------------------------------------------------------------
-- TABLE: exam_packages
-- Stores exam sessions / packages (e.g., UTS IPA Kelas 10).
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS exam_packages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    subject     TEXT NOT NULL DEFAULT 'Umum',
    description TEXT,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------------
-- TABLE: questions
-- Stores individual essay questions and their max point value.
-- Each question belongs to one exam_package.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS questions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_package_id INTEGER NOT NULL,
    question_number INTEGER NOT NULL,
    question_text   TEXT NOT NULL,
    max_point       REAL NOT NULL DEFAULT 10.0,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (exam_package_id) REFERENCES exam_packages(id) ON DELETE CASCADE
);

-- ------------------------------------------------------------
-- TABLE: master_keys
-- Stores the correct answer text and its TF-IDF vector (cached).
-- The vector_json column stores the pre-computed TF-IDF vector
-- to avoid recomputation on every evaluation.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS master_keys (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id     INTEGER NOT NULL UNIQUE,
    raw_text        TEXT NOT NULL,
    cleaned_text    TEXT,
    vector_json     TEXT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
);

-- ------------------------------------------------------------
-- TABLE: student_answers
-- Stores raw student answers (typed or OCR-extracted).
-- Each row links to one question from one student.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS student_answers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id     INTEGER NOT NULL,
    student_name    TEXT NOT NULL,
    raw_text        TEXT NOT NULL DEFAULT '',
    cleaned_text    TEXT,
    source_type     TEXT DEFAULT 'text' CHECK(source_type IN ('text', 'ocr', 'image')),
    image_path      TEXT,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
);

-- ------------------------------------------------------------
-- TABLE: evaluations
-- Stores the final grading result computed by the C math engine.
-- cosine_score is the raw cos(θ) value ∈ [0, 1].
-- final_point = cosine_score × max_point (from questions table).
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS evaluations (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    student_answer_id   INTEGER NOT NULL UNIQUE,
    cosine_score        REAL NOT NULL DEFAULT 0.0,
    final_point         REAL NOT NULL DEFAULT 0.0,
    matched_keywords    TEXT,
    missing_keywords    TEXT,
    confidence_level    REAL DEFAULT 0.0,
    computation_time_ms INTEGER DEFAULT 0,
    evaluated_at        DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (student_answer_id) REFERENCES student_answers(id) ON DELETE CASCADE
);

-- ------------------------------------------------------------
-- INDEXES for query performance
-- ------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_questions_exam ON questions(exam_package_id);
CREATE INDEX IF NOT EXISTS idx_master_keys_question ON master_keys(question_id);
CREATE INDEX IF NOT EXISTS idx_student_answers_question ON student_answers(question_id);
CREATE INDEX IF NOT EXISTS idx_student_answers_student ON student_answers(student_name);
CREATE INDEX IF NOT EXISTS idx_evaluations_answer ON evaluations(student_answer_id);
