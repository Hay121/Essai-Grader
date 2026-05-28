"""
EssayGrader — FastAPI Backend (Layer 2: Orchestration)
=======================================================
REST API for managing exams, questions, answers, and evaluations.
Connects the frontend with the math engine and database.

Endpoints:
    GET  /                              — Health check
    POST /api/exams                     — Create exam package
    GET  /api/exams                     — List all exams
    GET  /api/exams/{id}                — Get exam details + questions
    DELETE /api/exams/{id}              — Delete exam
    POST /api/exams/{id}/questions      — Add question + master key
    POST /api/answers/text              — Submit text answer
    POST /api/answers/bulk              — Submit all answers for a student
    POST /api/answers/image             — Submit image answer (OCR)
    POST /api/answers/pdf               — Submit PDF answer
    POST /api/evaluate/{exam_id}        — Run evaluation
    POST /api/evaluate/preview          — Live preview single answer
    GET  /api/results/{exam_id}         — Get evaluation results
    GET  /api/results/{exam_id}/rankings— Student rankings
    GET  /api/engine/status             — Engine status
    GET  /api/stats                     — Dashboard statistics

References:
    Salton & Buckley (1988). "Term-weighting in Automatic Text Retrieval."
"""

import os
import sys
import json
import time
import sqlite3
import logging
from typing import Optional, List
from contextlib import contextmanager

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

# Import core modules
sys.path.insert(0, os.path.dirname(__file__))
from core.evaluator import EssayEvaluator

# PDF extraction — try multiple libraries
PDF_EXTRACTOR = None
try:
    import pdfplumber
    PDF_EXTRACTOR = 'pdfplumber'
    logger.info("[PDF] ✓ pdfplumber available")
except ImportError:
    pass

if not PDF_EXTRACTOR:
    try:
        import PyPDF2
        PDF_EXTRACTOR = 'pypdf2'
        logger.info("[PDF] ✓ PyPDF2 available (fallback)")
    except ImportError:
        pass

if not PDF_EXTRACTOR:
    logger.warning("[PDF] No PDF library available. PDF upload disabled.")

# ============================================================
# DATABASE
# ============================================================
DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'database', 'essaygrader.db')
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), '..', 'database', 'schema.sql')
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), '..', 'uploads')

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)


@contextmanager
def get_db():
    """Get a database connection with row_factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Initialize database from schema."""
    # Reset Database on every run
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
            logger.info("[DB] Previous database deleted (Auto-Reset)")
        except Exception as e:
            logger.warning(f"[DB] Failed to delete previous database: {e}")

    if not os.path.exists(SCHEMA_PATH):
        logger.warning(f"[DB] Schema not found: {SCHEMA_PATH}")
        return
    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        schema = f.read()
    with get_db() as conn:
        conn.executescript(schema)
    logger.info("[DB] ✓ Database initialized")


def extract_pdf_text(filepath: str) -> str:
    """Extract text from PDF using available library."""
    if PDF_EXTRACTOR == 'pdfplumber':
        import pdfplumber
        text = ""
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text.strip()
    elif PDF_EXTRACTOR == 'pypdf2':
        import PyPDF2
        text = ""
        with open(filepath, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text.strip()
    else:
        raise RuntimeError("No PDF extraction library available")


# ============================================================
# PYDANTIC MODELS
# ============================================================
class ExamCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    subject: str = Field('Umum', max_length=100)
    description: str = Field('', max_length=500)

class QuestionCreate(BaseModel):
    question_text: str = Field(..., min_length=1)
    max_point: float = Field(10.0, ge=1.0, le=100.0)
    key_text: str = Field(..., min_length=1)

class AnswerTextSubmit(BaseModel):
    question_id: int
    student_name: str = Field(..., min_length=1, max_length=100)
    raw_text: str = Field('')

class BulkAnswerItem(BaseModel):
    question_id: int
    raw_text: str = Field('')

class BulkAnswerSubmit(BaseModel):
    student_name: str = Field(..., min_length=1, max_length=100)
    answers: List[BulkAnswerItem]

class BatchAnswerSubmit(BaseModel):
    question_id: int
    answers: List[dict] = Field(...)  # [{student_name, raw_text}]

class PreviewRequest(BaseModel):
    key_text: str
    answer_text: str
    max_point: float = Field(10.0, ge=1.0, le=100.0)


# ============================================================
# FASTAPI APP
# ============================================================
app = FastAPI(
    title="EssayGrader — Orchestration Engine",
    description="Automated essay grading via TF-IDF + Cosine Similarity",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

evaluator = EssayEvaluator()


@app.on_event("startup")
async def startup():
    logger.info("=" * 60)
    logger.info("  ESSAYGRADER — Orchestration Engine v2.0.0 (Hybrid)")
    logger.info("  SBERT + Keyword Check Grading System")
    logger.info("=" * 60)
    init_db()
    
    # Warmup SBERT model
    from core.semantic_model import SemanticModel
    logger.info("Warming up Semantic Model (SBERT)...")
    SemanticModel.get_instance()
    logger.info("Semantic Model ready.")


# ============================================================
# ENDPOINTS
# ============================================================
@app.get("/")
async def root():
    return {"name": "EssayGrader Engine", "version": "2.0.0", "status": "operational",
            "algorithm": "TF-IDF + Cosine Similarity"}


# --- STATS ---
@app.get("/api/stats")
async def get_stats():
    """Get dashboard statistics: total exams, questions, and answers."""
    with get_db() as conn:
        exam_count = conn.execute("SELECT COUNT(*) as c FROM exam_packages").fetchone()['c']
        question_count = conn.execute("SELECT COUNT(*) as c FROM questions").fetchone()['c']
        answer_count = conn.execute("SELECT COUNT(*) as c FROM student_answers").fetchone()['c']
        return {
            "exam_count": exam_count,
            "question_count": question_count,
            "answer_count": answer_count,
        }


# --- EXAMS ---
@app.post("/api/exams")
async def create_exam(req: ExamCreate):
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO exam_packages (title, subject, description) VALUES (?, ?, ?)",
            (req.title, req.subject, req.description))
        return {"id": cur.lastrowid, "message": "Exam created"}


@app.get("/api/exams")
async def list_exams():
    with get_db() as conn:
        rows = conn.execute("""
            SELECT e.*, COUNT(q.id) as question_count
            FROM exam_packages e LEFT JOIN questions q ON q.exam_package_id = e.id
            GROUP BY e.id ORDER BY e.created_at DESC
        """).fetchall()
        return {"exams": [dict(r) for r in rows]}


@app.get("/api/exams/{exam_id}")
async def get_exam(exam_id: int):
    with get_db() as conn:
        exam = conn.execute("SELECT * FROM exam_packages WHERE id=?", (exam_id,)).fetchone()
        if not exam:
            raise HTTPException(404, "Exam not found")
        questions = conn.execute("""
            SELECT q.*, mk.raw_text as key_text
            FROM questions q LEFT JOIN master_keys mk ON mk.question_id = q.id
            WHERE q.exam_package_id=? ORDER BY q.question_number
        """, (exam_id,)).fetchall()
        return {"exam": dict(exam), "questions": [dict(q) for q in questions]}


@app.delete("/api/exams/{exam_id}")
async def delete_exam(exam_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM exam_packages WHERE id=?", (exam_id,))
        return {"message": "Exam deleted"}


# --- QUESTIONS ---
@app.post("/api/exams/{exam_id}/questions")
async def add_question(exam_id: int, req: QuestionCreate):
    with get_db() as conn:
        exam = conn.execute("SELECT id FROM exam_packages WHERE id=?", (exam_id,)).fetchone()
        if not exam:
            raise HTTPException(404, "Exam not found")
        # Get next question number
        last = conn.execute(
            "SELECT MAX(question_number) as n FROM questions WHERE exam_package_id=?",
            (exam_id,)).fetchone()
        q_num = (last['n'] or 0) + 1
        cur = conn.execute(
            "INSERT INTO questions (exam_package_id, question_number, question_text, max_point) VALUES (?,?,?,?)",
            (exam_id, q_num, req.question_text, req.max_point))
        q_id = cur.lastrowid
        conn.execute(
            "INSERT INTO master_keys (question_id, raw_text) VALUES (?,?)",
            (q_id, req.key_text))
        return {"question_id": q_id, "question_number": q_num}


# --- ANSWERS ---
@app.post("/api/answers/text")
async def submit_text_answer(req: AnswerTextSubmit):
    with get_db() as conn:
        q = conn.execute("SELECT id FROM questions WHERE id=?", (req.question_id,)).fetchone()
        if not q:
            raise HTTPException(404, "Question not found")
        cur = conn.execute(
            "INSERT INTO student_answers (question_id, student_name, raw_text, source_type) VALUES (?,?,?,?)",
            (req.question_id, req.student_name, req.raw_text, 'text'))
        return {"answer_id": cur.lastrowid}


@app.post("/api/answers/bulk")
async def submit_bulk_answers(req: BulkAnswerSubmit):
    """Submit all answers for a student at once (one answer per question)."""
    with get_db() as conn:
        ids = []
        for ans in req.answers:
            q = conn.execute("SELECT id FROM questions WHERE id=?", (ans.question_id,)).fetchone()
            if not q:
                raise HTTPException(404, f"Question {ans.question_id} not found")
            cur = conn.execute(
                "INSERT INTO student_answers (question_id, student_name, raw_text, source_type) VALUES (?,?,?,?)",
                (ans.question_id, req.student_name, ans.raw_text, 'text'))
            ids.append(cur.lastrowid)
        return {"answer_ids": ids, "count": len(ids), "student_name": req.student_name}


@app.post("/api/answers/batch")
async def submit_batch_answers(req: BatchAnswerSubmit):
    with get_db() as conn:
        q = conn.execute("SELECT id FROM questions WHERE id=?", (req.question_id,)).fetchone()
        if not q:
            raise HTTPException(404, "Question not found")
        ids = []
        for ans in req.answers:
            cur = conn.execute(
                "INSERT INTO student_answers (question_id, student_name, raw_text, source_type) VALUES (?,?,?,?)",
                (req.question_id, ans.get('student_name', 'Unknown'), ans.get('raw_text', ''), 'text'))
            ids.append(cur.lastrowid)
        return {"answer_ids": ids, "count": len(ids)}


@app.post("/api/answers/image")
async def submit_image_answer(
    question_id: int = Form(...),
    student_name: str = Form(...),
    file: UploadFile = File(...)
):
    """Image upload endpoint — dinonaktifkan."""
    raise HTTPException(503, "Fitur upload gambar dinonaktifkan. Silakan gunakan input teks manual.")


# --- EVALUATION ---
@app.post("/api/evaluate/preview")
async def preview_evaluation(req: PreviewRequest):
    """Live preview: evaluate a single answer without saving."""
    result = evaluator.evaluate_single(req.key_text, req.answer_text, req.max_point)
    return result


@app.post("/api/evaluate/{exam_id}")
async def evaluate_exam(exam_id: int):
    """Run evaluation for all answers in an exam."""
    start = time.time()
    with get_db() as conn:
        questions = conn.execute("""
            SELECT q.id, q.max_point, mk.raw_text as key_text
            FROM questions q JOIN master_keys mk ON mk.question_id = q.id
            WHERE q.exam_package_id=?
        """, (exam_id,)).fetchall()

        if not questions:
            raise HTTPException(404, "No questions found for this exam")

        total_evaluated = 0
        all_results = []

        for q in questions:
            answers = conn.execute(
                "SELECT id, student_name, raw_text FROM student_answers WHERE question_id=?",
                (q['id'],)).fetchall()

            if not answers:
                continue

            answer_list = [{'id': a['id'], 'student_name': a['student_name'],
                           'raw_text': a['raw_text'], 'question_id': q['id']} for a in answers]

            results = evaluator.evaluate_question(q['key_text'], answer_list, q['max_point'])

            for r in results:
                # Upsert evaluation
                conn.execute("DELETE FROM evaluations WHERE student_answer_id=?", (r.answer_id,))
                conn.execute("""
                    INSERT INTO evaluations (student_answer_id, cosine_score, final_point,
                        matched_keywords, missing_keywords, confidence_level, computation_time_ms)
                    VALUES (?,?,?,?,?,?,?)
                """, (r.answer_id, r.cosine_score, r.final_point,
                      json.dumps(r.matched_keywords), json.dumps(r.missing_keywords),
                      r.confidence, r.computation_time_ms))
                all_results.append(r.to_dict())
                total_evaluated += 1

    elapsed = int((time.time() - start) * 1000)
    return {"evaluated": total_evaluated, "latency_ms": elapsed, "results": all_results}


# --- RESULTS ---
@app.get("/api/results/{exam_id}")
async def get_results(exam_id: int):
    with get_db() as conn:
        rows = conn.execute("""
            SELECT sa.student_name, sa.raw_text as answer_text,
                   q.question_number, q.question_text, q.max_point,
                   mk.raw_text as key_text,
                   e.cosine_score, e.final_point, e.matched_keywords,
                   e.missing_keywords, e.confidence_level
            FROM evaluations e
            JOIN student_answers sa ON sa.id = e.student_answer_id
            JOIN questions q ON q.id = sa.question_id
            JOIN master_keys mk ON mk.question_id = q.id
            WHERE q.exam_package_id=?
            ORDER BY sa.student_name, q.question_number
        """, (exam_id,)).fetchall()

        results = []
        for r in rows:
            d = dict(r)
            d['matched_keywords'] = json.loads(d['matched_keywords'] or '[]')
            d['missing_keywords'] = json.loads(d['missing_keywords'] or '[]')
            results.append(d)
        return {"results": results, "total": len(results)}


@app.get("/api/results/{exam_id}/rankings")
async def get_rankings(exam_id: int):
    with get_db() as conn:
        rows = conn.execute("""
            SELECT sa.student_name,
                   SUM(e.final_point) as total_score,
                   SUM(q.max_point) as max_possible,
                   AVG(e.cosine_score) as avg_cosine,
                   COUNT(e.id) as questions_answered
            FROM evaluations e
            JOIN student_answers sa ON sa.id = e.student_answer_id
            JOIN questions q ON q.id = sa.question_id
            WHERE q.exam_package_id=?
            GROUP BY sa.student_name
            ORDER BY total_score DESC
        """, (exam_id,)).fetchall()

        rankings = []
        for i, r in enumerate(rows):
            d = dict(r)
            d['rank'] = i + 1
            d['percentage'] = round(d['total_score'] / d['max_possible'] * 100, 1) if d['max_possible'] else 0
            rankings.append(d)
        return {"rankings": rankings}


# --- ENGINE STATUS ---
@app.get("/api/engine/status")
async def engine_status():
    try:
        from c_engine.c_bridge import c_bridge as cb
        c_status = "loaded" if cb.is_available else "numpy_fallback"
    except Exception:
        c_status = "numpy_fallback"
        
    try:
        from core.semantic_model import SemanticModel
        sbert_status = SemanticModel.get_instance().get_status()
        scoring_mode = "hybrid" if sbert_status.get('available') else "fallback"
    except Exception:
        sbert_status = {"available": False, "error": "failed_to_load"}
        scoring_mode = "fallback"
        
    return {
        "status": "operational",
        "c_engine": c_status,
        "scoring_mode": scoring_mode,
        "sbert": sbert_status,
        "ocr": "disabled",
        "pdf": PDF_EXTRACTOR or "unavailable",
    }


# --- PDF UPLOAD ---
@app.post("/api/answers/pdf")
async def submit_pdf_answer(
    question_id: int = Form(...),
    student_name: str = Form(...),
    file: UploadFile = File(...)
):
    """Upload a PDF file, extract text, and save as student answer."""
    if not PDF_EXTRACTOR:
        raise HTTPException(503, "Ekstraksi PDF tidak tersedia. "
                                 "Silakan gunakan input manual atau install pdfplumber/PyPDF2.")

    ext = os.path.splitext(file.filename or '')[1].lower()
    if ext != '.pdf':
        raise HTTPException(400, "Hanya file PDF yang diterima")

    # Save file
    filename = f"q{question_id}_{student_name}_{int(time.time())}.pdf"
    filepath = os.path.join(UPLOAD_DIR, filename)
    content = await file.read()
    with open(filepath, 'wb') as f:
        f.write(content)

    # Extract text from PDF
    try:
        extracted_text = extract_pdf_text(filepath)
    except Exception as e:
        logger.error(f"[PDF] Extraction failed: {e}")
        raise HTTPException(500, f"Gagal mengekstrak teks dari PDF: {str(e)}")

    if not extracted_text:
        extracted_text = "(Tidak dapat mengekstrak teks dari PDF)"

    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO student_answers (question_id, student_name, raw_text, source_type, image_path) VALUES (?,?,?,?,?)",
            (question_id, student_name, extracted_text, 'ocr', filepath))
        return {"answer_id": cur.lastrowid, "extracted_text": extracted_text, "source": "pdf"}


# --- ANSWERS MANAGEMENT ---
@app.get("/api/answers/{question_id}")
async def get_answers(question_id: int):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM student_answers WHERE question_id=? ORDER BY student_name",
            (question_id,)).fetchall()
        return {"answers": [dict(r) for r in rows]}


# ============================================================
# MAIN
# ============================================================
if __name__ == '__main__':
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
