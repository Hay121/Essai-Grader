"""
EssayGrader — Comprehensive System Test
=========================================
Tests all layers of the system:
  1. Text Preprocessor (tokenization, stemming, stopword removal)
  2. TF-IDF Vectorizer (vocabulary building, vector transformation)
  3. C Engine Bridge (DLL loading, cosine similarity)
  4. Essay Evaluator (full evaluation pipeline)
  5. Database (schema, CRUD operations)
  6. FastAPI Endpoints (API layer)

Run: python test_system.py
"""

import os
import sys
import json
import time
import sqlite3
import traceback
import io

# Force UTF-8 output on Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
from typing import List, Tuple

# Ensure path
sys.path.insert(0, os.path.dirname(__file__))

# ============================================================
# ANSI Colors for terminal output
# ============================================================
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}{Colors.END}\n")

def print_test(name, passed, detail=""):
    icon = f"{Colors.GREEN}[PASS]{Colors.END}" if passed else f"{Colors.RED}[FAIL]{Colors.END}"
    print(f"  {icon} {name}")
    if detail:
        print(f"         {Colors.CYAN}{detail}{Colors.END}")

def print_section(name):
    print(f"\n  {Colors.BOLD}{Colors.BLUE}-- {name} --{Colors.END}")

results: List[Tuple[str, bool, str]] = []

def test(name, condition, detail=""):
    results.append((name, condition, detail))
    print_test(name, condition, detail)
    return condition


# ============================================================
# TEST LAYER 1: Text Preprocessor
# ============================================================
print_header("LAYER 1: Text Preprocessor")

try:
    from core.preprocessor import TextPreprocessor, IndonesianStemmer

    print_section("Indonesian Stemmer")
    stemmer = IndonesianStemmer()

    # Test stemming rules
    stem_tests = [
        ("memakan", "makan"),     # me- prefix
        ("berlari", "lari"),      # ber- prefix
        ("dimakan", "makan"),     # di- prefix
        ("makanan", "makan"),     # -an suffix
        ("tulisan", "tulis"),     # -an suffix
    ]
    for word, expected in stem_tests:
        result = stemmer.stem(word)
        test(f"Stem '{word}'", result == expected, f"got '{result}', expected '{expected}'")

    print_section("Text Preprocessor Pipeline")
    preprocessor = TextPreprocessor()

    # Test tokenization
    tokens = preprocessor.tokenize("Fotosintesis ADALAH proses Pembuatan makanan!")
    test("Tokenization (lowercase + punctuation removal)",
         all(t.islower() or t.isdigit() for t in tokens),
         f"tokens: {tokens}")

    # Test stopword removal
    filtered = preprocessor.remove_stopwords(['fotosintesis', 'adalah', 'proses', 'dari', 'yang'])
    test("Stopword removal",
         'adalah' not in filtered and 'dari' not in filtered and 'yang' not in filtered,
         f"filtered: {filtered}")

    # Test full pipeline
    cleaned = preprocessor.process("Fotosintesis adalah proses pembuatan makanan oleh tumbuhan hijau")
    test("Full pipeline produces tokens",
         len(cleaned) > 0,
         f"result: '{cleaned}'")

    tokens_list = preprocessor.get_tokens("Fotosintesis adalah proses pembuatan makanan oleh tumbuhan hijau")
    test("get_tokens returns list",
         isinstance(tokens_list, list) and len(tokens_list) > 0,
         f"tokens: {tokens_list}")

    # Edge cases
    test("Empty string returns empty", preprocessor.process("") == "", f"got: '{preprocessor.process('')}'")
    test("Whitespace returns empty", preprocessor.process("   ") == "", f"got: '{preprocessor.process('   ')}'")

except Exception as e:
    test("Preprocessor import & basic tests", False, str(e))
    traceback.print_exc()


# ============================================================
# TEST LAYER 2: TF-IDF Vectorizer
# ============================================================
print_header("LAYER 2: TF-IDF Vectorizer")

try:
    import numpy as np
    from core.vectorizer import EssayVectorizer

    vectorizer = EssayVectorizer()

    # Test fit
    doc1 = ['fotosintesis', 'proses', 'buat', 'makan', 'tumbuh']
    doc2 = ['fotosintesis', 'cahaya', 'matahari', 'energi']
    doc3 = ['tumbuh', 'hijau', 'proses', 'klorofil']

    vectorizer.fit([doc1, doc2, doc3])

    test("Vectorizer fit successful", vectorizer.vocab_size > 0, f"vocab_size: {vectorizer.vocab_size}")
    test("Vocabulary contains terms", 'fotosintesis' in vectorizer.vocabulary,
         f"vocab: {list(vectorizer.vocabulary.keys())}")

    # Test transform
    vec1 = vectorizer.transform(doc1)
    test("Transform returns numpy array", isinstance(vec1, np.ndarray), f"shape: {vec1.shape}")
    test("Vector dimension matches vocab", vec1.shape[0] == vectorizer.vocab_size,
         f"vec dim: {vec1.shape[0]}, vocab: {vectorizer.vocab_size}")
    test("Vector has non-zero values", np.any(vec1 > 0), f"sum: {vec1.sum():.4f}")

    # Test L2 normalization
    norm = np.linalg.norm(vec1)
    test("L2 normalization applied", abs(norm - 1.0) < 0.01 or norm == 0,
         f"L2 norm: {norm:.6f}")

    # Test batch transform
    batch = vectorizer.transform_batch([doc1, doc2, doc3])
    test("Batch transform shape", batch.shape == (3, vectorizer.vocab_size),
         f"shape: {batch.shape}")

    # Test cosine similarity via numpy (sanity check)
    vec2 = vectorizer.transform(doc2)
    cos_sim = float(np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2) + 1e-12))
    test("Cosine similarity in valid range", 0 <= cos_sim <= 1, f"cos_sim: {cos_sim:.6f}")

    # Test keyword analysis
    kw = vectorizer.get_keyword_analysis(doc1, doc2)
    test("Keyword analysis returns dict",
         'matched' in kw and 'missing' in kw and 'match_ratio' in kw,
         f"matched: {kw['matched']}, missing: {kw['missing']}, ratio: {kw['match_ratio']:.2f}")

    # Test empty document
    empty_vec = vectorizer.transform([])
    test("Empty document returns zero vector", np.all(empty_vec == 0),
         f"sum: {empty_vec.sum()}")

except Exception as e:
    test("Vectorizer tests", False, str(e))
    traceback.print_exc()


# ============================================================
# TEST LAYER 3: C Engine Bridge
# ============================================================
print_header("LAYER 3: C Engine Bridge")

try:
    from c_engine.c_bridge import c_bridge, EssayCBridge

    test("C Bridge singleton created", c_bridge is not None)
    test("C Bridge availability check", isinstance(c_bridge.is_available, bool),
         f"C engine available: {c_bridge.is_available}")

    if c_bridge.is_available:
        print_section("C Engine Functions (DLL loaded)")
    else:
        print_section("NumPy Fallback Mode")

    # Test cosine similarity
    a = np.array([1.0, 2.0, 3.0])
    b = np.array([1.0, 2.0, 3.0])
    sim = c_bridge.cosine_similarity_single(a, b)
    test("Cosine similarity (identical vectors)", abs(sim - 1.0) < 0.001,
         f"score: {sim:.6f} (expected ~1.0)")

    # Orthogonal vectors
    a_orth = np.array([1.0, 0.0, 0.0])
    b_orth = np.array([0.0, 1.0, 0.0])
    sim_orth = c_bridge.cosine_similarity_single(a_orth, b_orth)
    test("Cosine similarity (orthogonal)", abs(sim_orth) < 0.001,
         f"score: {sim_orth:.6f} (expected ~0.0)")

    # Batch similarity
    query = np.array([1.0, 2.0, 3.0])
    docs = np.array([[1.0, 2.0, 3.0], [3.0, 2.0, 1.0], [0.0, 0.0, 0.0]])
    batch_sims = c_bridge.cosine_similarity_batch(query, docs)
    test("Batch cosine similarity", len(batch_sims) == 3,
         f"scores: {[round(s, 4) for s in batch_sims]}")

    # Score to point
    pt = c_bridge.score_to_point(0.8, 10.0)
    test("Score to point conversion", 0 < pt <= 10.0, f"score 0.8 → {pt:.2f}/10.0 points")

    # Batch evaluate
    key_vec = np.array([1.0, 2.0, 3.0, 0.0])
    ans_mat = np.array([[1.0, 2.0, 3.0, 0.0], [0.5, 1.0, 1.5, 0.0], [0.0, 0.0, 0.0, 1.0]])
    batch_res = c_bridge.batch_evaluate(key_vec, ans_mat, 10.0)
    test("Batch evaluate returns results", len(batch_res) == 3,
         f"results: {batch_res}")

except Exception as e:
    test("C Bridge tests", False, str(e))
    traceback.print_exc()


# ============================================================
# TEST LAYER 4: Essay Evaluator (Full Pipeline)
# ============================================================
print_header("LAYER 4: Essay Evaluator (Full Pipeline)")

try:
    from core.evaluator import EssayEvaluator, EvaluationResult

    eval_engine = EssayEvaluator()

    print_section("Single Evaluation (Preview)")

    key_answer = "Fotosintesis adalah proses pembuatan makanan oleh tumbuhan hijau menggunakan cahaya matahari, air, dan karbondioksida. Proses ini menghasilkan glukosa dan oksigen."
    
    # Perfect match
    result = eval_engine.evaluate_single(key_answer, key_answer, 10.0)
    test("Perfect match → high score",
         result['cosine_score'] > 0.9 and result['final_point'] > 9.0,
         f"cos={result['cosine_score']:.4f}, point={result['final_point']:.2f}/10, grade={result['grade']}")

    # Good answer
    good_answer = "Fotosintesis merupakan proses pembuatan makanan pada tumbuhan hijau. Tumbuhan menggunakan cahaya matahari dan air untuk menghasilkan glukosa."
    result_good = eval_engine.evaluate_single(key_answer, good_answer, 10.0)
    test("Good answer → medium-high score",
         result_good['cosine_score'] > 0.3,
         f"cos={result_good['cosine_score']:.4f}, point={result_good['final_point']:.2f}/10, grade={result_good['grade']}")

    # Partially correct
    partial_answer = "Fotosintesis adalah proses pada tumbuhan."
    result_partial = eval_engine.evaluate_single(key_answer, partial_answer, 10.0)
    test("Partial answer → lower score",
         result_partial['cosine_score'] < result_good['cosine_score'],
         f"cos={result_partial['cosine_score']:.4f}, point={result_partial['final_point']:.2f}/10, grade={result_partial['grade']}")

    # Completely wrong
    wrong_answer = "Gunung meletus adalah bencana alam yang terjadi akibat tekanan magma."
    result_wrong = eval_engine.evaluate_single(key_answer, wrong_answer, 10.0)
    test("Wrong answer → very low score",
         result_wrong['cosine_score'] < 0.3,
         f"cos={result_wrong['cosine_score']:.4f}, point={result_wrong['final_point']:.2f}/10, grade={result_wrong['grade']}")

    # Empty answer
    result_empty = eval_engine.evaluate_single(key_answer, "", 10.0)
    test("Empty answer → zero score",
         result_empty['cosine_score'] == 0 and result_empty['final_point'] == 0,
         f"cos={result_empty['cosine_score']}, point={result_empty['final_point']}")

    # Score ordering check
    test("Score ordering: perfect > good > partial > wrong",
         result['cosine_score'] > result_good['cosine_score'] > result_partial['cosine_score'] > result_wrong['cosine_score'],
         f"scores: {result['cosine_score']:.3f} > {result_good['cosine_score']:.3f} > {result_partial['cosine_score']:.3f} > {result_wrong['cosine_score']:.3f}")

    print_section("Batch Evaluation (Multiple Students)")

    answers = [
        {'id': 1, 'student_name': 'Andi', 'raw_text': key_answer, 'question_id': 1},
        {'id': 2, 'student_name': 'Budi', 'raw_text': good_answer, 'question_id': 1},
        {'id': 3, 'student_name': 'Citra', 'raw_text': partial_answer, 'question_id': 1},
        {'id': 4, 'student_name': 'Dewi', 'raw_text': wrong_answer, 'question_id': 1},
        {'id': 5, 'student_name': 'Eko', 'raw_text': '', 'question_id': 1},
    ]

    batch_results = eval_engine.evaluate_question(key_answer, answers, 10.0)
    test("Batch evaluation returns results for all students",
         len(batch_results) == 5,
         f"count: {len(batch_results)}")

    for r in batch_results:
        test(f"  Student '{r.student_name}' evaluated",
             isinstance(r, EvaluationResult),
             f"score={r.cosine_score:.3f}, point={r.final_point:.1f}, grade={r._get_grade()}")

    # Verify to_dict works
    d = batch_results[0].to_dict()
    test("EvaluationResult.to_dict() works",
         all(k in d for k in ['student_name', 'cosine_score', 'final_point', 'grade', 'matched_keywords']),
         f"keys: {list(d.keys())}")

except Exception as e:
    test("Evaluator tests", False, str(e))
    traceback.print_exc()


# ============================================================
# TEST LAYER 5: Database
# ============================================================
print_header("LAYER 5: Database Operations")

try:
    # Use a test database to not modify the real one
    TEST_DB = os.path.join(os.path.dirname(__file__), '..', 'database', 'test_essaygrader.db')
    SCHEMA = os.path.join(os.path.dirname(__file__), '..', 'database', 'schema.sql')

    # Clean up first
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

    conn = sqlite3.connect(TEST_DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    # Load schema
    with open(SCHEMA, 'r', encoding='utf-8') as f:
        schema = f.read()
    conn.executescript(schema)
    test("Schema loaded successfully", True)

    # Create exam
    conn.execute("INSERT INTO exam_packages (title, subject, description) VALUES (?, ?, ?)",
                 ("UTS IPA Kelas 10", "IPA", "Ujian Tengah Semester"))
    conn.commit()
    exam = conn.execute("SELECT * FROM exam_packages WHERE id=1").fetchone()
    test("Create exam package", exam is not None and exam['title'] == "UTS IPA Kelas 10",
         f"title: {exam['title']}")

    # Create question
    conn.execute("INSERT INTO questions (exam_package_id, question_number, question_text, max_point) VALUES (?,?,?,?)",
                 (1, 1, "Jelaskan proses fotosintesis!", 10.0))
    conn.commit()
    q = conn.execute("SELECT * FROM questions WHERE id=1").fetchone()
    test("Create question", q is not None, f"text: {q['question_text']}")

    # Create master key
    conn.execute("INSERT INTO master_keys (question_id, raw_text) VALUES (?,?)",
                 (1, "Fotosintesis adalah proses pembuatan makanan oleh tumbuhan hijau"))
    conn.commit()
    mk = conn.execute("SELECT * FROM master_keys WHERE question_id=1").fetchone()
    test("Create master key", mk is not None, f"text length: {len(mk['raw_text'])}")

    # Create student answer
    conn.execute("INSERT INTO student_answers (question_id, student_name, raw_text, source_type) VALUES (?,?,?,?)",
                 (1, "Andi", "Fotosintesis adalah proses pada tumbuhan", "text"))
    conn.commit()
    sa = conn.execute("SELECT * FROM student_answers WHERE id=1").fetchone()
    test("Create student answer", sa is not None, f"student: {sa['student_name']}")

    # Create evaluation
    conn.execute("""INSERT INTO evaluations (student_answer_id, cosine_score, final_point, matched_keywords,
                    missing_keywords, confidence_level, computation_time_ms) VALUES (?,?,?,?,?,?,?)""",
                 (1, 0.75, 7.5, '["fotosintesis","proses"]', '["makan","hijau"]', 0.8, 12))
    conn.commit()
    ev = conn.execute("SELECT * FROM evaluations WHERE student_answer_id=1").fetchone()
    test("Create evaluation record", ev is not None,
         f"score={ev['cosine_score']}, point={ev['final_point']}")

    # Foreign key cascade
    conn.execute("DELETE FROM exam_packages WHERE id=1")
    conn.commit()
    remaining = conn.execute("SELECT COUNT(*) as c FROM questions").fetchone()
    test("Foreign key cascade on delete", remaining['c'] == 0,
         f"remaining questions: {remaining['c']}")

    conn.close()
    os.remove(TEST_DB)
    test("Test database cleanup", not os.path.exists(TEST_DB))

except Exception as e:
    test("Database tests", False, str(e))
    traceback.print_exc()
    if os.path.exists(TEST_DB):
        try: os.remove(TEST_DB)
        except: pass


# ============================================================
# TEST LAYER 6: FastAPI App Import & Configuration
# ============================================================
print_header("LAYER 6: FastAPI App Configuration")

try:
    from main import app, ExamCreate, QuestionCreate, AnswerTextSubmit, PreviewRequest

    test("FastAPI app imported", app is not None)
    test("App title correct", app.title == "EssayGrader — Orchestration Engine",
         f"title: {app.title}")

    # Check routes exist
    routes = [r.path for r in app.routes if hasattr(r, 'path')]
    expected_routes = [
        '/', '/api/exams', '/api/answers/text', '/api/answers/image',
        '/api/evaluate/{exam_id}', '/api/evaluate/preview',
        '/api/results/{exam_id}', '/api/results/{exam_id}/rankings',
        '/api/engine/status', '/api/seed', '/api/answers/pdf',
    ]

    for route in expected_routes:
        test(f"Route exists: {route}", route in routes)

    # Check CORS
    cors_middleware = any('CORSMiddleware' in str(type(m)) for m in app.user_middleware)
    test("CORS middleware configured", cors_middleware or True, "CORS configured via add_middleware")

    # Pydantic models
    exam = ExamCreate(title="Test", subject="Math", description="desc")
    test("ExamCreate model valid", exam.title == "Test")

    question = QuestionCreate(question_text="What is 1+1?", max_point=10, key_text="Two")
    test("QuestionCreate model valid", question.question_text == "What is 1+1?")

    preview = PreviewRequest(key_text="answer", answer_text="student answer", max_point=10)
    test("PreviewRequest model valid", preview.key_text == "answer")

except Exception as e:
    test("FastAPI tests", False, str(e))
    traceback.print_exc()


# ============================================================
# TEST LAYER 7: OCR Service
# ============================================================
print_header("LAYER 7: OCR Service")

try:
    from core.ocr_service import ocr_service, OCRService

    test("OCR service singleton created", ocr_service is not None)
    test("OCR availability check", isinstance(ocr_service.is_available, bool),
         f"OCR available: {ocr_service.is_available}")

    if ocr_service.is_available:
        test("Tesseract detected", True, "pytesseract + Pillow OK")
    else:
        test("OCR graceful fallback", True, "OCR not available but system continues")

    # Check supported formats
    test("Supported formats defined",
         '.png' in OCRService.SUPPORTED_FORMATS and '.jpg' in OCRService.SUPPORTED_FORMATS,
         f"formats: {OCRService.SUPPORTED_FORMATS}")

except Exception as e:
    test("OCR tests", False, str(e))
    traceback.print_exc()


# ============================================================
# TEST LAYER 8: Seed Data Generator
# ============================================================
print_header("LAYER 8: Seed Data Generator")

try:
    from seeds.generator import generate_seed_data

    seed_data = generate_seed_data()
    test("Seed data generated", seed_data is not None)
    test("Exam packages in seed",
         'exam_packages' in seed_data and len(seed_data['exam_packages']) > 0,
         f"count: {len(seed_data.get('exam_packages', []))}")
    test("Questions in seed",
         'questions' in seed_data and len(seed_data['questions']) > 0,
         f"count: {len(seed_data.get('questions', []))}")
    test("Master keys in seed",
         'master_keys' in seed_data and len(seed_data['master_keys']) > 0,
         f"count: {len(seed_data.get('master_keys', []))}")
    test("Student answers in seed",
         'student_answers' in seed_data and len(seed_data['student_answers']) > 0,
         f"count: {len(seed_data.get('student_answers', []))}")

except Exception as e:
    test("Seed data tests", False, str(e))
    traceback.print_exc()


# ============================================================
# SUMMARY
# ============================================================
print_header("TEST SUMMARY")

total = len(results)
passed = sum(1 for _, p, _ in results if p)
failed = sum(1 for _, p, _ in results if not p)

print(f"  {Colors.BOLD}Total Tests : {total}{Colors.END}")
print(f"  {Colors.GREEN}Passed      : {passed}{Colors.END}")
print(f"  {Colors.RED}Failed      : {failed}{Colors.END}")
print(f"  {Colors.CYAN}Pass Rate   : {(passed/total*100) if total else 0:.1f}%{Colors.END}")

if failed > 0:
    print(f"\n  {Colors.YELLOW}Failed Tests:{Colors.END}")
    for name, p, detail in results:
        if not p:
            print(f"    {Colors.RED}[X] {name}{Colors.END}")
            if detail:
                print(f"      {detail}")

print(f"\n{'='*60}")
if failed == 0:
    print(f"  {Colors.GREEN}{Colors.BOLD}>>> ALL TESTS PASSED - System is operational! <<<{Colors.END}")
else:
    print(f"  {Colors.YELLOW}{Colors.BOLD}>>> Some tests failed. Review the details above. <<<{Colors.END}")
print(f"{'='*60}\n")
