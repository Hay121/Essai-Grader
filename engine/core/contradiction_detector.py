"""
EssayGrader — Contradiction Detector Module (Deep Semantic Analysis)
=====================================================================
Detects fatal semantic contradictions between a key answer and student answer
that lexical matching (TF-IDF) and even SBERT cosine similarity would miss.

Seven Detection Layers:
    1. Role Inversion: Subject-Object swap ("A dijajah B" vs "B dijajah A")
    2. Negation Contradiction: Negation flipping facts ("perlu" vs "tidak perlu")
       — Enhanced with multi-word negation and implicit negation detection
    3. Directional Reversal: Process direction swap ("X → Y" vs "Y → X")
    4. Antonym Substitution: Keyword replaced by antonym ("naik" vs "turun")
    5. Causal/Temporal Inversion: Cause-effect or time order reversed
    6. Quantifier/Modal Contradiction: Scope or obligation flipped
    7. SBERT Deep Semantic: Embedding-based contradiction for implicit cases

Verdict System:
    CONTRADICTION: Fatal semantic error → score capped at 0.10
    ENTAILMENT:    Correct paraphrase   → score boosted × 1.05
    NEUTRAL:       No directional issue  → score unchanged

Design:
    Layers 1–6 are rule-based using Indonesian regex patterns + lexical lookup.
    Layer 7 uses SBERT embeddings (optional, graceful fallback if unavailable).
    No required external ML dependencies — works in both SBERT and Fallback modes.

References:
    Dagan, Glickman & Magnini (2005). "The PASCAL Recognising Textual Entailment Challenge."
    MacCartney & Manning (2008). "Modeling Semantic Containment and Exclusion in NLP."
"""

import re
import logging
from typing import List, Dict, Tuple, Optional, Set

logger = logging.getLogger(__name__)


# ============================================================
# CONSTANTS: Indonesian Linguistic Markers
# ============================================================

# Negation words that flip the truth value of a statement
NEGATION_WORDS = {
    'tidak', 'bukan', 'tanpa', 'belum', 'tak', 'jangan',
    'tiada', 'bukan', 'bukanlah', 'tidaklah', 'takkan',
    'tidak pernah', 'belum pernah', 'tidak bisa', 'tidak dapat',
    'non', 'anti', 'nir',
}

# Single-token negation for fast lookup
NEGATION_TOKENS = {
    'tidak', 'bukan', 'tanpa', 'belum', 'tak', 'jangan',
    'tiada', 'bukanlah', 'tidaklah', 'takkan', 'non', 'anti', 'nir',
}

# Multi-word negation phrases (detected as a unit)
MULTIWORD_NEGATION = [
    'tidak pernah', 'belum pernah', 'tidak bisa', 'tidak dapat',
    'tidak mampu', 'tidak mungkin', 'tidak boleh', 'tidak perlu',
    'tidak harus', 'belum tentu', 'belum bisa', 'belum dapat',
    'tidak akan', 'tidak lagi', 'tidak ada', 'bukan merupakan',
    'bukan termasuk', 'tanpa harus', 'tanpa perlu', 'tanpa adanya',
    'bebas dari', 'terbebas dari', 'lepas dari', 'terlepas dari',
    'jauh dari', 'terbatas pada',
]

# Implicit negation phrases — phrases that negate without using negation words
IMPLICIT_NEGATION_PHRASES = [
    ('dapat tumbuh tanpa', 'memerlukan'),
    ('bisa hidup tanpa', 'membutuhkan'),
    ('tidak bergantung pada', 'bergantung pada'),
    ('bebas dari', 'terikat oleh'),
    ('opsional', 'wajib'),
    ('sukarela', 'wajib'),
    ('pilihan', 'keharusan'),
]

# Passive voice markers (di- prefix verbs indicate Object-first structure)
PASSIVE_MARKERS = re.compile(
    r'\b(dijajah|dikuasai|diperintah|dijual|dibeli|dimakan|diminum|'
    r'dibuat|diciptakan|dihasilkan|diubah|dikonversi|ditransformasi|'
    r'dikalahkan|diserang|dibantu|diajarkan|dididik|diberi|diberikan|'
    r'dipengaruhi|disebabkan|ditimbulkan|dipicu|diakibatkan|'
    r'dihancurkan|dirusak|dibangun|diperbaiki|dilindungi|dijaga|'
    r'ditanam|dipanen|diolah|diproses|dikonsumsi|digunakan|'
    r'dikirim|diterima|diambil|disimpan|ditaruh|diletakkan|'
    r'diproduksi|didistribusikan|diekspor|diimpor|'
    r'di\w+kan|di\w+i)\b',
    re.IGNORECASE
)

# Prepositions that mark the Agent in passive constructions
AGENT_MARKERS = {'oleh', 'kepada', 'terhadap', 'pada'}

# Direction/conversion markers
DIRECTION_PATTERNS = [
    # "X diubah menjadi Y", "X berubah menjadi Y"
    re.compile(r'(.+?)\s+(?:diubah|berubah|dikonversi|ditransformasi|dirubah)\s+(?:menjadi|jadi|ke)\s+(.+)', re.IGNORECASE),
    # "dari X menjadi Y", "dari X ke Y"
    re.compile(r'dari\s+(.+?)\s+(?:menjadi|jadi|ke|menuju)\s+(.+)', re.IGNORECASE),
    # "X menjadi Y"
    re.compile(r'(.+?)\s+(?:menjadi|berubah jadi|berubah ke)\s+(.+)', re.IGNORECASE),
    # "mengubah X menjadi Y", "mengkonversi X ke Y"
    re.compile(r'(?:mengubah|merubah|mengkonversi|mentransformasi)\s+(.+?)\s+(?:menjadi|jadi|ke)\s+(.+)', re.IGNORECASE),
]

# Passive voice pattern: "[Object] di-[verb] oleh [Subject]"
PASSIVE_SVO_PATTERN = re.compile(
    r'(.+?)\s+(di\w+)\s+(?:oleh|sama)\s+(.+)',
    re.IGNORECASE
)

# Active voice pattern: "[Subject] me-[verb] [Object]"
ACTIVE_SVO_PATTERN = re.compile(
    r'(.+?)\s+(me\w+|ber\w+)\s+(.+)',
    re.IGNORECASE
)

# Penalty and boost constants
CONTRADICTION_SCORE_CAP = 0.10
ENTAILMENT_BOOST = 1.05  # Restored to 1.05 so the UI visibly increases the score for valid paraphrases
WARNING_PENALTY = 0.50


# ============================================================
# LAYER 4: Antonym Pairs Dictionary (100+ pairs)
# ============================================================
# Each tuple: (word_a, word_b) — using word_a in place of word_b
# (or vice versa) reverses the meaning of a statement.
ANTONYM_PAIRS = [
    # --- Adjektiva Umum ---
    ('besar', 'kecil'), ('tinggi', 'rendah'), ('panjang', 'pendek'),
    ('luas', 'sempit'), ('tebal', 'tipis'), ('berat', 'ringan'),
    ('cepat', 'lambat'), ('kuat', 'lemah'), ('keras', 'lunak'),
    ('panas', 'dingin'), ('basah', 'kering'), ('terang', 'gelap'),
    ('banyak', 'sedikit'), ('lebar', 'sempit'), ('dalam', 'dangkal'),
    ('kasar', 'halus'), ('tajam', 'tumpul'), ('padat', 'renggang'),

    # --- Adjektiva Abstrak ---
    ('baik', 'buruk'), ('bagus', 'jelek'), ('benar', 'salah'),
    ('positif', 'negatif'), ('untung', 'rugi'), ('sukses', 'gagal'),
    ('berhasil', 'gagal'), ('mudah', 'sulit'), ('sederhana', 'kompleks'),
    ('maju', 'mundur'), ('modern', 'kuno'), ('baru', 'lama'),
    ('muda', 'tua'), ('hidup', 'mati'), ('sehat', 'sakit'),
    ('aman', 'bahaya'), ('damai', 'perang'), ('kaya', 'miskin'),
    ('mahal', 'murah'), ('rajin', 'malas'), ('pintar', 'bodoh'),
    ('jujur', 'bohong'), ('adil', 'curang'), ('setia', 'khianat'),

    # --- Verba/Aksi ---
    ('naik', 'turun'), ('masuk', 'keluar'), ('datang', 'pergi'),
    ('buka', 'tutup'), ('mulai', 'selesai'), ('hidup', 'mati'),
    ('bangun', 'hancur'), ('tumbuh', 'menyusut'), ('muncul', 'hilang'),
    ('menang', 'kalah'), ('maju', 'mundur'), ('dorong', 'tarik'),
    ('tambah', 'kurang'), ('naik', 'turun'), ('meningkat', 'menurun'),
    ('mempercepat', 'memperlambat'), ('memperbesar', 'memperkecil'),
    ('membuat', 'menghancurkan'), ('membangun', 'merusak'),
    ('menerima', 'menolak'), ('setuju', 'menolak'), ('menyetujui', 'menentang'),
    ('mendukung', 'menentang'), ('mengizinkan', 'melarang'),
    ('menguntungkan', 'merugikan'), ('membantu', 'menghambat'),
    ('memperkuat', 'melemahkan'), ('menyatukan', 'memecah'),
    ('menambah', 'mengurangi'), ('memproduksi', 'mengonsumsi'),
    ('mengekspor', 'mengimpor'), ('mengirim', 'menerima'),
    ('memberi', 'mengambil'), ('menyerap', 'melepaskan'),
    ('menghasilkan', 'menghabiskan'), ('menyimpan', 'membuang'),
    ('melindungi', 'menyerang'), ('mempertahankan', 'menyerahkan'),
    ('menjajah', 'dijajah'),

    # --- Sains / IPA ---
    ('terbarukan', 'tak terbarukan'), ('organik', 'anorganik'),
    ('biotik', 'abiotik'), ('aerob', 'anaerob'),
    ('prokariotik', 'eukariotik'), ('autotrof', 'heterotrof'),
    ('endoterm', 'eksoterm'), ('katabolisme', 'anabolisme'),
    ('oksidasi', 'reduksi'), ('asam', 'basa'),
    ('produsen', 'konsumen'), ('predator', 'mangsa'),
    ('parasit', 'inang'), ('simbiosis', 'kompetisi'),
    ('fotosintesis', 'respirasi'), ('inspirasi', 'ekspirasi'),
    ('kondensasi', 'evaporasi'), ('mencair', 'membeku'),
    ('menyerap', 'memantulkan'), ('menguap', 'mengembun'),

    # --- IPS / Kenegaraan ---
    ('demokrasi', 'otoriter'), ('merdeka', 'terjajah'),
    ('penjajah', 'terjajah'), ('sentralisasi', 'desentralisasi'),
    ('ekspansi', 'kontraksi'), ('inflasi', 'deflasi'),
    ('surplus', 'defisit'), ('impor', 'ekspor'),
    ('hak', 'kewajiban'), ('wajib', 'sukarela'),
    ('legal', 'ilegal'), ('resmi', 'tidak resmi'),
    ('persatuan', 'perpecahan'), ('toleransi', 'intoleransi'),
    ('kemerdekaan', 'penjajahan'),

    # --- Kata Sifat Ukuran / Kuantitas ---
    ('mayoritas', 'minoritas'), ('maksimal', 'minimal'),
    ('optimal', 'suboptimal'), ('lengkap', 'tidak lengkap'),
    ('total', 'parsial'), ('absolut', 'relatif'),
    ('permanen', 'sementara'), ('umum', 'khusus'),
]

# Build fast lookup sets from antonym pairs
_ANTONYM_MAP: Dict[str, Set[str]] = {}
for _a, _b in ANTONYM_PAIRS:
    _a_lower, _b_lower = _a.lower(), _b.lower()
    _ANTONYM_MAP.setdefault(_a_lower, set()).add(_b_lower)
    _ANTONYM_MAP.setdefault(_b_lower, set()).add(_a_lower)


# ============================================================
# LAYER 5: Causal & Temporal Markers
# ============================================================

# Causal markers — words/phrases indicating cause-effect relationships
CAUSAL_MARKERS = [
    re.compile(r'(.+?)\s+(?:menyebabkan|mengakibatkan|memicu|menimbulkan|menghasilkan|membuat|menjadikan)\s+(.+)', re.IGNORECASE),
    re.compile(r'(?:karena|sebab|akibat|lantaran|disebabkan)\s+(.+?)[,;]\s*(?:maka|sehingga|akibatnya|hasilnya)?\s*(.+)', re.IGNORECASE),
    re.compile(r'(.+?)\s+(?:sehingga|akibatnya|maka|oleh karena itu|karenanya)\s+(.+)', re.IGNORECASE),
    re.compile(r'(?:akibat|dampak|efek|konsekuensi|hasil)\s+(?:dari\s+)?(.+?)\s+(?:adalah|yaitu|ialah|berupa)\s+(.+)', re.IGNORECASE),
]

# Temporal markers — words indicating sequential ordering
TEMPORAL_BEFORE_WORDS = {
    'sebelum', 'sebelumnya', 'seprior', 'pra', 'mendahului',
    'lebih dahulu', 'lebih dulu', 'terlebih dahulu',
    'awalnya', 'mulanya', 'pada awalnya',
}
TEMPORAL_AFTER_WORDS = {
    'sesudah', 'setelah', 'selepas', 'pasca', 'seusai',
    'kemudian', 'selanjutnya', 'berikutnya', 'setelahnya',
    'akhirnya', 'pada akhirnya',
}

# Temporal reversal patterns
TEMPORAL_PATTERNS = [
    re.compile(r'(sebelum|sebelumnya|pra|mendahului)\s+(.+?)[,;]\s*(.+)', re.IGNORECASE),
    re.compile(r'(sesudah|setelah|selepas|pasca|seusai)\s+(.+?)[,;]\s*(.+)', re.IGNORECASE),
    re.compile(r'(.+?)\s+(mendahului|mendahulukan|lebih dahulu dari(?:pada)?)\s+(.+)', re.IGNORECASE),
    re.compile(r'(.+?)\s+(sebelum|sesudah|setelah)\s+(.+)', re.IGNORECASE),
]


# ============================================================
# LAYER 6: Quantifier & Modal Groups
# ============================================================

# Quantifier contradiction pairs — group A contradicts group B
QUANTIFIER_CONTRADICTIONS = [
    ({'semua', 'seluruh', 'setiap', 'segala', 'segenap', 'tiap'},
     {'tidak semua', 'hanya beberapa', 'sebagian', 'beberapa', 'hanya sebagian', 'tidak setiap', 'tidak seluruh'}),
    ({'selalu', 'senantiasa', 'terus', 'selamanya', 'sepanjang waktu'},
     {'tidak pernah', 'jarang', 'kadang', 'sesekali', 'tidak selalu', 'jarang sekali'}),
    ({'pasti', 'tentu', 'pasti akan', 'sudah pasti'},
     {'belum tentu', 'mungkin', 'tidak pasti', 'belum pasti'}),
]

# Modal contradiction pairs — obligation/permission reversed
MODAL_CONTRADICTIONS = [
    ({'wajib', 'harus', 'mesti', 'perlu', 'diharuskan', 'diwajibkan', 'diperlukan'},
     {'tidak wajib', 'tidak harus', 'tidak perlu', 'opsional', 'sukarela', 'tidak diwajibkan', 'boleh tidak', 'bebas'}),
    ({'boleh', 'diperbolehkan', 'diizinkan', 'diperkenankan', 'berhak'},
     {'dilarang', 'tidak boleh', 'tidak diperbolehkan', 'tidak diizinkan', 'haram', 'terlarang', 'tidak berhak'}),
    ({'mampu', 'bisa', 'dapat', 'sanggup', 'kapabel'},
     {'tidak mampu', 'tidak bisa', 'tidak dapat', 'tidak sanggup', 'mustahil'}),
]


# ============================================================
# HELPER: Text Normalization for Comparison
# ============================================================
def _normalize_text(text: str) -> str:
    """Normalize text for comparison: lowercase, strip extra whitespace."""
    if not text:
        return ''
    text = text.lower().strip()
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _extract_clauses(text: str) -> List[str]:
    """Split text into clauses for per-clause analysis."""
    if not text:
        return []
    # Split on sentence and clause boundaries
    clauses = re.split(r'[.;!?\n]+', text)
    result = []
    for clause in clauses:
        clause = clause.strip()
        if len(clause.split()) >= 3:  # At least 3 words
            result.append(clause)
    return result if result else [text.strip()]


def _extract_entities(text: str) -> List[str]:
    """
    Extract potential entity names (proper nouns, key nouns) from text.
    Uses capitalization and common patterns.
    """
    # Find capitalized words (potential proper nouns)
    entities = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', text)
    
    # Also extract from lowercase text using common entity contexts
    lower_text = text.lower()
    # Entities near agent/patient markers
    for marker in ['oleh', 'kepada', 'terhadap']:
        pattern = re.compile(rf'{marker}\s+(\w+(?:\s+\w+)?)', re.IGNORECASE)
        matches = pattern.findall(lower_text)
        entities.extend(matches)
    
    # Entities as subjects (start of clause before verb)
    for pattern in [PASSIVE_SVO_PATTERN, ACTIVE_SVO_PATTERN]:
        match = pattern.search(text)
        if match:
            entities.append(match.group(1).strip())
            entities.append(match.group(3).strip())
    
    # Deduplicate and clean
    cleaned = []
    seen = set()
    for e in entities:
        e_clean = e.strip().lower()
        if e_clean and e_clean not in seen and len(e_clean) >= 2:
            # Filter out common non-entity words
            if e_clean not in NEGATION_TOKENS and e_clean not in AGENT_MARKERS:
                cleaned.append(e_clean)
                seen.add(e_clean)
    
    return cleaned


def _get_content_words(text: str, min_len: int = 3) -> Set[str]:
    """Extract meaningful content words from normalized text, excluding negation tokens."""
    tokens = _normalize_text(text).split()
    return {t for t in tokens if t not in NEGATION_TOKENS and len(t) >= min_len}


def _clause_topic_overlap(k_clause: str, a_clause: str, threshold: float = 0.45) -> Tuple[bool, float]:
    """
    Check if two clauses discuss the same topic via content word overlap.
    Returns (is_same_topic, overlap_ratio).
    """
    k_content = _get_content_words(k_clause)
    a_content = _get_content_words(a_clause)
    if not k_content or not a_content:
        return False, 0.0
    overlap = len(k_content & a_content)
    ratio = overlap / max(len(k_content), len(a_content))
    return ratio >= threshold, ratio


def _subjects_are_different(k_clause: str, a_clause: str) -> bool:
    """
    Check if two clauses discuss different subjects/entities.
    Prevents false positives like "prokariotik tidak X" vs "eukariotik X".
    """
    k_content = _get_content_words(k_clause)
    a_content = _get_content_words(a_clause)
    if not k_content or not a_content:
        return False

    k_unique = k_content - a_content
    a_unique = a_content - k_content

    # If both have unique significant words (>= 4 chars), likely different subjects
    k_sig = {w for w in k_unique if len(w) >= 4}
    a_sig = {w for w in a_unique if len(w) >= 4}

    return bool(k_sig and a_sig)


# ============================================================
# DETECTOR 1: Role Inversion (Subject-Object Swap)
# ============================================================
def _detect_role_inversion(key_text: str, answer_text: str) -> List[Dict]:
    """
    Detect if the student answer swaps subject and object roles.
    
    Example:
        Key:    "Indonesia dijajah oleh Belanda"
        Answer: "Belanda dijajah oleh Indonesia"
        → FATAL: Actor roles are inverted
    """
    findings = []
    key_norm = _normalize_text(key_text)
    ans_norm = _normalize_text(answer_text)
    
    # Extract SVO triples from passive constructions
    key_passives = _extract_passive_triples(key_text)
    ans_passives = _extract_passive_triples(answer_text)
    
    # Check for role inversions in passive constructions
    for k_triple in key_passives:
        k_patient, k_verb_root, k_agent = k_triple
        for a_triple in ans_passives:
            a_patient, a_verb_root, a_agent = a_triple
            
            # Check if the verb is similar (same root)
            if _verbs_match(k_verb_root, a_verb_root):
                # Check if actors swapped positions
                k_patient_norm = k_patient.lower().strip()
                k_agent_norm = k_agent.lower().strip()
                a_patient_norm = a_patient.lower().strip()
                a_agent_norm = a_agent.lower().strip()
                
                # Patient and Agent swapped?
                if (_fuzzy_entity_match(k_patient_norm, a_agent_norm) and
                    _fuzzy_entity_match(k_agent_norm, a_patient_norm)):
                    findings.append({
                        'type': 'ROLE_INVERSION',
                        'description': (
                            f"Peran aktor terbalik: "
                            f"Kunci menyatakan '{k_patient}' di-{k_verb_root} oleh '{k_agent}', "
                            f"tetapi jawaban menyatakan '{a_patient}' di-{a_verb_root} oleh '{a_agent}'"
                        ),
                        'severity': 'FATAL',
                        'confidence': 0.95,
                    })
    
    # Also check active voice patterns
    key_actives = _extract_active_triples(key_text)
    ans_actives = _extract_active_triples(answer_text)
    
    for k_triple in key_actives:
        k_agent, k_verb_root, k_patient = k_triple
        for a_triple in ans_actives:
            a_agent, a_verb_root, a_patient = a_triple
            
            if _verbs_match(k_verb_root, a_verb_root):
                k_agent_norm = k_agent.lower().strip()
                k_patient_norm = k_patient.lower().strip()
                a_agent_norm = a_agent.lower().strip()
                a_patient_norm = a_patient.lower().strip()
                
                if (_fuzzy_entity_match(k_agent_norm, a_patient_norm) and
                    _fuzzy_entity_match(k_patient_norm, a_agent_norm)):
                    findings.append({
                        'type': 'ROLE_INVERSION',
                        'description': (
                            f"Peran aktor terbalik: "
                            f"Kunci menyatakan '{k_agent}' me-{k_verb_root} '{k_patient}', "
                            f"tetapi jawaban menyatakan '{a_agent}' me-{a_verb_root} '{a_patient}'"
                        ),
                        'severity': 'FATAL',
                        'confidence': 0.90,
                    })
    
    # Cross-check: passive key vs active answer (and vice versa)
    for k_triple in key_passives:
        k_patient, k_verb_root, k_agent = k_triple
        for a_triple in ans_actives:
            a_agent, a_verb_root, a_patient = a_triple
            
            if _verbs_match(k_verb_root, a_verb_root):
                # In correct paraphrase: passive patient = active patient, passive agent = active agent
                # In inversion: passive patient = active agent AND passive agent = active patient
                k_patient_norm = k_patient.lower().strip()
                k_agent_norm = k_agent.lower().strip()
                a_agent_norm = a_agent.lower().strip()
                a_patient_norm = a_patient.lower().strip()
                
                # Check if it's a CORRECT paraphrase (passive ↔ active same meaning)
                if (_fuzzy_entity_match(k_patient_norm, a_patient_norm) and
                    _fuzzy_entity_match(k_agent_norm, a_agent_norm)):
                    # This is correct! "X dijajah oleh Y" == "Y menjajah X"
                    # Not a contradiction
                    pass
                elif (_fuzzy_entity_match(k_patient_norm, a_agent_norm) and
                      _fuzzy_entity_match(k_agent_norm, a_patient_norm)):
                    # Inverted! "X dijajah oleh Y" but answer says "X menjajah Y"
                    findings.append({
                        'type': 'ROLE_INVERSION',
                        'description': (
                            f"Peran aktor terbalik (pasif→aktif): "
                            f"Kunci menyatakan '{k_patient}' di-{k_verb_root} oleh '{k_agent}', "
                            f"tetapi jawaban menyatakan '{a_agent}' me-{a_verb_root} '{a_patient}' "
                            f"(yang berarti '{k_patient}' justru pelaku, bukan penerima)"
                        ),
                        'severity': 'FATAL',
                        'confidence': 0.90,
                    })
    
    return findings


def _extract_passive_triples(text: str) -> List[Tuple[str, str, str]]:
    """
    Extract (Patient, VerbRoot, Agent) triples from passive sentences.
    Pattern: [Patient] di-[verb] oleh [Agent]
    """
    triples = []
    clauses = _extract_clauses(text)
    
    for clause in clauses:
        # Pattern: X di[verb](kan/i) oleh Y
        match = re.search(
            r'(.+?)\s+di(\w+?)(?:kan|i)?\s+(?:oleh|sama)\s+(.+)',
            clause, re.IGNORECASE
        )
        if match:
            patient = match.group(1).strip()
            verb_root = match.group(2).strip()
            agent = match.group(3).strip()
            # Clean agent: take only up to next clause boundary
            agent = re.split(r'\s+(?:dan|serta|selama|sejak|pada|di|ke|dari|untuk|agar|supaya|karena|sehingga|ketika|yang)', agent, maxsplit=1)[0].strip()
            if len(patient) >= 2 and len(agent) >= 2:
                triples.append((patient, verb_root, agent))
    
    return triples


def _extract_active_triples(text: str) -> List[Tuple[str, str, str]]:
    """
    Extract (Agent, VerbRoot, Patient) triples from active sentences.
    Pattern: [Agent] me-[verb] [Patient]
    Also handles: [Agent] me-[verb] [Object] kepada [Recipient]
    """
    triples = []
    clauses = _extract_clauses(text)
    
    for clause in clauses:
        # Pattern 1: X me[verb](kan/i) Y kepada/terhadap Z
        # In this case, the key relationship is Agent(X) -> Recipient(Z)
        match_kepada = re.search(
            r'(.+?)\s+(?:me|mem|men|meng|meny)(\w+?)(?:kan|i)?\s+(.+?)\s+(?:kepada|terhadap|pada|ke)\s+(.+)',
            clause, re.IGNORECASE
        )
        if match_kepada:
            agent = match_kepada.group(1).strip()
            verb_root = match_kepada.group(2).strip()
            obj = match_kepada.group(3).strip()
            recipient = match_kepada.group(4).strip()
            # Clean recipient
            recipient = re.split(r'\s+(?:dan|serta|selama|sejak|untuk|agar|supaya|karena|sehingga|ketika|yang)', recipient, maxsplit=1)[0].strip()
            if len(agent) >= 2 and len(recipient) >= 2:
                # Store as (Agent, verb, Recipient) — the directional pair
                triples.append((agent, verb_root, recipient))
            continue
        
        # Pattern 2: X me[verb](kan/i) Y (standard active)
        match = re.search(
            r'(.+?)\s+(?:me|mem|men|meng|meny)(\w+?)(?:kan|i)?\s+(.+)',
            clause, re.IGNORECASE
        )
        if match:
            agent = match.group(1).strip()
            verb_root = match.group(2).strip()
            patient = match.group(3).strip()
            # Clean patient: take only up to next clause boundary
            patient = re.split(r'\s+(?:dan|serta|selama|sejak|pada|di|ke|dari|untuk|agar|supaya|karena|sehingga|ketika|yang|kepada|terhadap)', patient, maxsplit=1)[0].strip()
            if len(agent) >= 2 and len(patient) >= 2:
                triples.append((agent, verb_root, patient))
    
    return triples


def _verbs_match(verb1: str, verb2: str) -> bool:
    """Check if two verb roots refer to the same action."""
    v1 = verb1.lower().strip()
    v2 = verb2.lower().strip()
    
    if v1 == v2:
        return True
    
    # Check if one is a substring of the other (handles affixed forms)
    if v1 in v2 or v2 in v1:
        return True
    
    # Check synonym groups for verb equivalence
    VERB_SYNONYMS = [
        {'jajah', 'kuasai', 'kuasa', 'perintah', 'takluk', 'taklukkan', 'duduki', 'kolonisasi'},
        {'serang', 'gempur', 'invasi', 'agresi', 'serbuan', 'serbu'},
        {'kalah', 'takluk', 'tunduk'},
        {'menang', 'unggul', 'juara'},
        {'ubah', 'konversi', 'transformasi', 'rubah', 'alih'},
        {'buat', 'hasilkan', 'produksi', 'cipta', 'ciptakan'},
        {'makan', 'konsumsi', 'santap', 'lahap'},
        {'ajar', 'didik', 'latih'},
        {'jual', 'dagang', 'niaga'},
        {'beli', 'borong'},
        {'kirim', 'antar', 'hantarkan'},
        {'terima', 'dapat', 'peroleh'},
    ]
    
    for group in VERB_SYNONYMS:
        if v1 in group and v2 in group:
            return True
    
    return False


def _fuzzy_entity_match(entity1: str, entity2: str) -> bool:
    """
    Check if two entity strings refer to the same entity.
    Uses substring matching and common variations.
    """
    e1 = entity1.lower().strip()
    e2 = entity2.lower().strip()
    
    if not e1 or not e2:
        return False
    
    if e1 == e2:
        return True
    
    # One is substring of the other
    if e1 in e2 or e2 in e1:
        return True
    
    # Token overlap: if >60% of tokens overlap
    t1 = set(e1.split())
    t2 = set(e2.split())
    if t1 and t2:
        overlap = len(t1 & t2)
        max_len = max(len(t1), len(t2))
        if overlap / max_len >= 0.6:
            return True
    
    return False


# ============================================================
# DETECTOR 2: Negation Contradiction (ENHANCED)
# ============================================================
def _detect_negation_contradiction(key_text: str, answer_text: str) -> List[Dict]:
    """
    Detect if the student answer negates a core fact from the key.
    
    ENHANCED version with:
    - Multi-word negation detection ("tidak pernah", "belum bisa", etc.)
    - Implicit negation phrases ("tanpa harus", "bebas dari", etc.)
    - Double negation handling (two negations = positive, not contradiction)
    - Subject consistency guard (different subjects ≠ contradiction)
    
    Example:
        Key:    "Tumbuhan hijau memerlukan cahaya matahari"
        Answer: "Tumbuhan hijau tidak memerlukan cahaya matahari"
        → FATAL: Negation flips the fact
    """
    findings = []
    
    key_clauses = _extract_clauses(key_text)
    ans_clauses = _extract_clauses(answer_text)
    
    for k_clause in key_clauses:
        k_norm = _normalize_text(k_clause)
        k_tokens = k_norm.split()

        # Count single-word negations
        k_single_negs = [t for t in k_tokens if t in NEGATION_TOKENS]

        # Count multi-word negations in the raw normalized text
        k_multi_negs = [mw for mw in MULTIWORD_NEGATION if mw in k_norm]

        # Effective negation count: multi-word phrases already contain the single
        # token, so count them as the primary signal.  Each multi-word phrase
        # counts as one negation unit.
        k_neg_count = len(k_multi_negs) if k_multi_negs else len(k_single_negs)
        k_has_negation = k_neg_count > 0
        
        for a_clause in ans_clauses:
            a_norm = _normalize_text(a_clause)
            a_tokens = a_norm.split()

            a_single_negs = [t for t in a_tokens if t in NEGATION_TOKENS]
            a_multi_negs = [mw for mw in MULTIWORD_NEGATION if mw in a_norm]
            a_neg_count = len(a_multi_negs) if a_multi_negs else len(a_single_negs)
            a_has_negation = a_neg_count > 0
            
            # Require high topic overlap to ensure same-topic comparison
            same_topic, overlap_ratio = _clause_topic_overlap(k_clause, a_clause, threshold=0.55)
            if not same_topic:
                continue

            
            # --- Check 1: Explicit negation delta ---
            neg_delta = abs(k_neg_count - a_neg_count)
            
            if neg_delta % 2 == 1:  # Odd delta = meaning flipped
                if a_neg_count > k_neg_count:
                    neg_word = a_multi_negs[0] if a_multi_negs else (a_single_negs[0] if a_single_negs else 'tidak')
                    findings.append({
                        'type': 'NEGATION',
                        'description': (
                            f"Negasi fatal: Jawaban menambahkan '{neg_word}' yang membalik fakta. "
                            f"Kunci: \"{k_clause.strip()}\", "
                            f"Jawaban: \"{a_clause.strip()}\""
                        ),
                        'severity': 'FATAL',
                        'confidence': 0.90,
                    })
                elif k_neg_count > a_neg_count:
                    neg_word = k_multi_negs[0] if k_multi_negs else (k_single_negs[0] if k_single_negs else 'tidak')
                    findings.append({
                        'type': 'NEGATION',
                        'description': (
                            f"Negasi fatal: Kunci menggunakan '{neg_word}' tetapi jawaban menghilangkannya, "
                            f"membalik makna. "
                            f"Kunci: \"{k_clause.strip()}\", "
                            f"Jawaban: \"{a_clause.strip()}\""
                        ),
                        'severity': 'FATAL',
                        'confidence': 0.85,
                    })
            
            # --- Check 2: Implicit negation via antonym phrases ---
            # Even without explicit negation tokens, certain phrase pairs contradict
            # Example: "memerlukan cahaya" vs "dapat tumbuh tanpa cahaya"
            if neg_delta == 0 and not findings:
                for impl_neg, impl_pos in IMPLICIT_NEGATION_PHRASES:
                    # Key uses positive form, answer uses implicit negation
                    if impl_pos in k_norm and impl_neg in a_norm:
                        findings.append({
                            'type': 'NEGATION',
                            'description': (
                                f"Negasi implisit: Kunci menyatakan '{impl_pos}' "
                                f"tetapi jawaban menggunakan '{impl_neg}' yang bermakna sebaliknya. "
                                f"Kunci: \"{k_clause.strip()}\", "
                                f"Jawaban: \"{a_clause.strip()}\""
                            ),
                            'severity': 'FATAL',
                            'confidence': 0.80,
                        })
                    # Reverse: key uses negation, answer removes it
                    elif impl_neg in k_norm and impl_pos in a_norm:
                        findings.append({
                            'type': 'NEGATION',
                            'description': (
                                f"Negasi implisit: Kunci menyatakan '{impl_neg}' "
                                f"tetapi jawaban menggunakan '{impl_pos}' yang bermakna sebaliknya. "
                                f"Kunci: \"{k_clause.strip()}\", "
                                f"Jawaban: \"{a_clause.strip()}\""
                            ),
                            'severity': 'FATAL',
                            'confidence': 0.80,
                        })
    
    return findings


# ============================================================
# DETECTOR 3: Directional Reversal
# ============================================================
def _detect_direction_reversal(key_text: str, answer_text: str) -> List[Dict]:
    """
    Detect if the student answer reverses the direction of a conversion/process.
    
    Example:
        Key:    "Energi cahaya diubah menjadi energi kimia"
        Answer: "Energi kimia diubah menjadi energi cahaya"
        → FATAL: Direction of conversion is reversed
    """
    findings = []
    
    key_directions = _extract_directions(key_text)
    ans_directions = _extract_directions(answer_text)
    
    for k_dir in key_directions:
        k_source, k_target = k_dir
        for a_dir in ans_directions:
            a_source, a_target = a_dir
            
            # Check if source and target are swapped
            if (_fuzzy_entity_match(k_source, a_target) and
                _fuzzy_entity_match(k_target, a_source)):
                findings.append({
                    'type': 'DIRECTION_REVERSAL',
                    'description': (
                        f"Arah proses terbalik: "
                        f"Kunci menyatakan '{k_source}' -> '{k_target}', "
                        f"tetapi jawaban menyatakan '{a_source}' -> '{a_target}'"
                    ),
                    'severity': 'FATAL',
                    'confidence': 0.95,
                })
    
    return findings


def _extract_directions(text: str) -> List[Tuple[str, str]]:
    """
    Extract (Source, Target) direction pairs from text.
    Patterns: "dari X ke Y", "X menjadi Y", "X diubah menjadi Y"
    """
    directions = []
    clauses = _extract_clauses(text)
    
    for clause in clauses:
        for pattern in DIRECTION_PATTERNS:
            match = pattern.search(clause)
            if match:
                source = match.group(1).strip()
                target = match.group(2).strip()
                # Clean: remove trailing clause connectors
                target = re.split(
                    r'\s+(?:dan|serta|selama|karena|sehingga|yang|untuk|dalam|pada)',
                    target, maxsplit=1
                )[0].strip()
                if len(source) >= 2 and len(target) >= 2:
                    directions.append((source, target))
                break  # Use first matching pattern per clause
    
    return directions


# ============================================================
# DETECTOR 4: Antonym Substitution (NEW)
# ============================================================
def _detect_antonym_contradiction(key_text: str, answer_text: str) -> List[Dict]:
    """
    Detect if the student answer replaces a keyword with its antonym.
    
    Example:
        Key:    "Indonesia menggunakan energi terbarukan"
        Answer: "Indonesia menggunakan energi tak terbarukan"
        → FATAL: Antonym substitution reverses the meaning
    
    Example:
        Key:    "Fotosintesis menghasilkan oksigen"
        Answer: "Fotosintesis menghabiskan oksigen"
        → FATAL: 'menghasilkan' ↔ 'menghabiskan' are antonyms
    """
    findings = []
    
    key_clauses = _extract_clauses(key_text)
    ans_clauses = _extract_clauses(answer_text)
    
    for k_clause in key_clauses:
        k_norm = _normalize_text(k_clause)
        k_tokens = k_norm.split()
        
        for a_clause in ans_clauses:
            a_norm = _normalize_text(a_clause)
            a_tokens = a_norm.split()
            
            # Require same-topic overlap
            same_topic, overlap_ratio = _clause_topic_overlap(k_clause, a_clause, threshold=0.45)
            if not same_topic:
                continue
            
            # Find antonym pairs between key and answer
            antonym_hits = []
            
            # Single-token antonyms
            k_set = set(k_tokens)
            a_set = set(a_tokens)
            
            for k_tok in k_set:
                if k_tok in _ANTONYM_MAP:
                    for ant in _ANTONYM_MAP[k_tok]:
                        if ant in a_set and ant not in k_set:
                            # Found: key has word X, answer has antonym Y (and key doesn't also have Y)
                            antonym_hits.append((k_tok, ant))
            
            # Multi-token antonym check (e.g., "tak terbarukan")
            for (word_a, word_b) in ANTONYM_PAIRS:
                wa, wb = word_a.lower(), word_b.lower()
                # Check if key contains word_a and answer contains word_b (or vice versa)
                if ' ' in wa or ' ' in wb:
                    # Multi-word antonym
                    if wa in k_norm and wb in a_norm and wa not in a_norm:
                        antonym_hits.append((wa, wb))
                    elif wb in k_norm and wa in a_norm and wb not in a_norm:
                        antonym_hits.append((wb, wa))
            
            # Deduplicate
            seen_pairs = set()
            unique_hits = []
            for (w1, w2) in antonym_hits:
                pair_key = tuple(sorted([w1, w2]))
                if pair_key not in seen_pairs:
                    seen_pairs.add(pair_key)
                    unique_hits.append((w1, w2))
            
            for (k_word, a_word) in unique_hits:
                findings.append({
                    'type': 'ANTONYM_SUBSTITUTION',
                    'description': (
                        f"Substitusi antonim: Kunci menggunakan '{k_word}' "
                        f"tetapi jawaban menggunakan antonimnya '{a_word}', membalik makna. "
                        f"Kunci: \"{k_clause.strip()}\", "
                        f"Jawaban: \"{a_clause.strip()}\""
                    ),
                    'severity': 'FATAL',
                    'confidence': 0.88,
                })
    
    return findings


# ============================================================
# DETECTOR 5: Causal / Temporal Inversion (NEW)
# ============================================================
def _detect_causal_temporal_inversion(key_text: str, answer_text: str) -> List[Dict]:
    """
    Detect if the student answer reverses a cause-effect relationship
    or inverts the temporal ordering of events.
    
    Example (Causal):
        Key:    "Hujan menyebabkan banjir"
        Answer: "Banjir menyebabkan hujan"
        → FATAL: Cause and effect are swapped
    
    Example (Temporal):
        Key:    "Sebelum merdeka, Indonesia dijajah Belanda"
        Answer: "Sesudah merdeka, Indonesia dijajah Belanda"
        → FATAL: Temporal relationship is inverted
    """
    findings = []
    
    # --- Part A: Causal Inversion ---
    key_causal = _extract_causal_pairs(key_text)
    ans_causal = _extract_causal_pairs(answer_text)
    
    for k_cause, k_effect in key_causal:
        for a_cause, a_effect in ans_causal:
            # Check if cause and effect are swapped
            if (_fuzzy_entity_match(k_cause, a_effect) and
                _fuzzy_entity_match(k_effect, a_cause)):
                findings.append({
                    'type': 'CAUSAL_INVERSION',
                    'description': (
                        f"Hubungan sebab-akibat terbalik: "
                        f"Kunci menyatakan '{k_cause}' menyebabkan '{k_effect}', "
                        f"tetapi jawaban menyatakan '{a_cause}' menyebabkan '{a_effect}'"
                    ),
                    'severity': 'FATAL',
                    'confidence': 0.90,
                })
    
    # --- Part B: Temporal Inversion ---
    key_clauses = _extract_clauses(key_text)
    ans_clauses = _extract_clauses(answer_text)
    
    for k_clause in key_clauses:
        k_norm = _normalize_text(k_clause)
        
        # Check if key clause has a temporal marker
        k_temporal_type = None  # 'before' or 'after'
        k_temporal_word = None
        
        for word in TEMPORAL_BEFORE_WORDS:
            if word in k_norm:
                k_temporal_type = 'before'
                k_temporal_word = word
                break
        
        if not k_temporal_type:
            for word in TEMPORAL_AFTER_WORDS:
                if word in k_norm:
                    k_temporal_type = 'after'
                    k_temporal_word = word
                    break
        
        if not k_temporal_type:
            continue
        
        for a_clause in ans_clauses:
            a_norm = _normalize_text(a_clause)
            
            # Require same-topic overlap
            same_topic, _ = _clause_topic_overlap(k_clause, a_clause, threshold=0.40)
            if not same_topic:
                continue
            
            # Check if answer has the OPPOSITE temporal marker
            a_temporal_type = None
            a_temporal_word = None
            
            for word in TEMPORAL_BEFORE_WORDS:
                if word in a_norm:
                    a_temporal_type = 'before'
                    a_temporal_word = word
                    break
            
            if not a_temporal_type:
                for word in TEMPORAL_AFTER_WORDS:
                    if word in a_norm:
                        a_temporal_type = 'after'
                        a_temporal_word = word
                        break
            
            if a_temporal_type and a_temporal_type != k_temporal_type:
                findings.append({
                    'type': 'TEMPORAL_INVERSION',
                    'description': (
                        f"Urutan waktu terbalik: "
                        f"Kunci menggunakan '{k_temporal_word}' (bermakna {'sebelum' if k_temporal_type == 'before' else 'sesudah'}), "
                        f"tetapi jawaban menggunakan '{a_temporal_word}' (bermakna {'sebelum' if a_temporal_type == 'before' else 'sesudah'}). "
                        f"Kunci: \"{k_clause.strip()}\", "
                        f"Jawaban: \"{a_clause.strip()}\""
                    ),
                    'severity': 'FATAL',
                    'confidence': 0.88,
                })
    
    return findings


def _extract_causal_pairs(text: str) -> List[Tuple[str, str]]:
    """
    Extract (Cause, Effect) pairs from text using causal marker patterns.
    """
    pairs = []
    clauses = _extract_clauses(text)
    
    for clause in clauses:
        for pattern in CAUSAL_MARKERS:
            match = pattern.search(clause)
            if match:
                cause = match.group(1).strip()
                effect = match.group(2).strip()
                # Clean
                effect = re.split(
                    r'\s+(?:dan|serta|selama|yang|untuk|dalam|pada)',
                    effect, maxsplit=1
                )[0].strip()
                if len(cause) >= 2 and len(effect) >= 2:
                    pairs.append((cause, effect))
                break
    
    return pairs


# ============================================================
# DETECTOR 6: Quantifier / Modal Contradiction (NEW)
# ============================================================
def _detect_quantifier_modal_contradiction(key_text: str, answer_text: str) -> List[Dict]:
    """
    Detect if the student answer changes a quantifier or modal word
    to its opposite, reversing the scope or obligation.
    
    Example (Quantifier):
        Key:    "Semua warga negara wajib membayar pajak"
        Answer: "Hanya beberapa warga negara wajib membayar pajak"
        → FATAL: Quantifier "semua" → "hanya beberapa"
    
    Example (Modal):
        Key:    "Warga negara wajib membayar pajak"
        Answer: "Warga negara tidak perlu membayar pajak"
        → FATAL: Modal "wajib" → "tidak perlu"
    """
    findings = []
    
    key_clauses = _extract_clauses(key_text)
    ans_clauses = _extract_clauses(answer_text)
    
    for k_clause in key_clauses:
        k_norm = _normalize_text(k_clause)
        
        for a_clause in ans_clauses:
            a_norm = _normalize_text(a_clause)
            
            # Require same-topic overlap
            same_topic, _ = _clause_topic_overlap(k_clause, a_clause, threshold=0.45)
            if not same_topic:
                continue
            
            # --- Check quantifier contradictions ---
            for group_a, group_b in QUANTIFIER_CONTRADICTIONS:
                k_has_a = any(q in k_norm for q in group_a)
                k_has_b = any(q in k_norm for q in group_b)
                a_has_a = any(q in a_norm for q in group_a)
                a_has_b = any(q in a_norm for q in group_b)
                
                k_quant_a = next((q for q in group_a if q in k_norm), None)
                k_quant_b = next((q for q in group_b if q in k_norm), None)
                a_quant_a = next((q for q in group_a if q in a_norm), None)
                a_quant_b = next((q for q in group_b if q in a_norm), None)
                
                if k_has_a and a_has_b and not k_has_b:
                    findings.append({
                        'type': 'QUANTIFIER_CONTRADICTION',
                        'description': (
                            f"Kuantitas terbalik: Kunci menggunakan '{k_quant_a}' "
                            f"tetapi jawaban menggunakan '{a_quant_b}' yang bermakna berlawanan. "
                            f"Kunci: \"{k_clause.strip()}\", "
                            f"Jawaban: \"{a_clause.strip()}\""
                        ),
                        'severity': 'FATAL',
                        'confidence': 0.88,
                    })
                elif k_has_b and a_has_a and not k_has_a:
                    findings.append({
                        'type': 'QUANTIFIER_CONTRADICTION',
                        'description': (
                            f"Kuantitas terbalik: Kunci menggunakan '{k_quant_b}' "
                            f"tetapi jawaban menggunakan '{a_quant_a}' yang bermakna berlawanan. "
                            f"Kunci: \"{k_clause.strip()}\", "
                            f"Jawaban: \"{a_clause.strip()}\""
                        ),
                        'severity': 'FATAL',
                        'confidence': 0.88,
                    })
            
            # --- Check modal contradictions ---
            for group_a, group_b in MODAL_CONTRADICTIONS:
                k_has_a = any(m in k_norm for m in group_a)
                k_has_b = any(m in k_norm for m in group_b)
                a_has_a = any(m in a_norm for m in group_a)
                a_has_b = any(m in a_norm for m in group_b)
                
                k_modal_a = next((m for m in group_a if m in k_norm), None)
                k_modal_b = next((m for m in group_b if m in k_norm), None)
                a_modal_a = next((m for m in group_a if m in a_norm), None)
                a_modal_b = next((m for m in group_b if m in a_norm), None)
                
                if k_has_a and a_has_b and not k_has_b:
                    findings.append({
                        'type': 'MODAL_CONTRADICTION',
                        'description': (
                            f"Modalitas terbalik: Kunci menggunakan '{k_modal_a}' "
                            f"tetapi jawaban menggunakan '{a_modal_b}' yang bermakna berlawanan. "
                            f"Kunci: \"{k_clause.strip()}\", "
                            f"Jawaban: \"{a_clause.strip()}\""
                        ),
                        'severity': 'FATAL',
                        'confidence': 0.85,
                    })
                elif k_has_b and a_has_a and not k_has_a:
                    findings.append({
                        'type': 'MODAL_CONTRADICTION',
                        'description': (
                            f"Modalitas terbalik: Kunci menggunakan '{k_modal_b}' "
                            f"tetapi jawaban menggunakan '{a_modal_a}' yang bermakna berlawanan. "
                            f"Kunci: \"{k_clause.strip()}\", "
                            f"Jawaban: \"{a_clause.strip()}\""
                        ),
                        'severity': 'FATAL',
                        'confidence': 0.85,
                    })
    
    return findings


# ============================================================
# DETECTOR 7: SBERT Deep Semantic Contradiction (NEW)
# ============================================================
def _detect_deep_semantic_contradiction(key_text: str, answer_text: str) -> List[Dict]:
    """
    Use SBERT embeddings to detect contradictions that escape rule-based
    detectors.  Strategy:
    
    1. Compute clause-level similarity between key and answer clauses.
    2. For clause pairs with HIGH surface similarity (>0.70) but that
       contain known semantic reversal signals (negation, antonym, direction
       word inversion), flag as contradiction.
    3. For clause pairs where answer clause embedding is CLOSER to a
       negated version of the key clause than to the key clause itself,
       flag as deep semantic contradiction.
    
    This detector gracefully returns [] when SBERT is unavailable.
    """
    findings = []
    
    # Attempt to import semantic model
    try:
        from .semantic_model import SemanticModel
        model = SemanticModel.get_instance()
        if not model.is_available:
            return []
    except Exception:
        return []
    
    key_clauses = _extract_clauses(key_text)
    ans_clauses = _extract_clauses(answer_text)
    
    if not key_clauses or not ans_clauses:
        return []
    
    # Strategy: For each key clause, create a negated version, then
    # check if the answer clause is semantically closer to the negated
    # version than to the original.
    negation_prefixes = ['Tidak benar bahwa ', 'Bukan berarti bahwa ']
    
    for k_clause in key_clauses:
        k_clause_clean = k_clause.strip()
        if len(k_clause_clean.split()) < 4:
            continue
        
        # Create negated versions of the key clause
        negated_versions = [
            f"{prefix}{k_clause_clean.lower()}" for prefix in negation_prefixes
        ]
        
        # Batch encode: [original_key, negated_key1, negated_key2, answer_clauses...]
        all_texts = [k_clause_clean] + negated_versions + [c.strip() for c in ans_clauses]
        
        try:
            import numpy as np
            vectors = model.encode_batch(all_texts)
            if vectors is None:
                continue
            
            k_vec = vectors[0]
            neg_vecs = vectors[1:1 + len(negated_versions)]
            ans_vecs = vectors[1 + len(negated_versions):]
            
            for i, a_clause in enumerate(ans_clauses):
                a_vec = ans_vecs[i]
                
                # Similarity to original key clause
                sim_original = float(np.dot(k_vec, a_vec))
                sim_original = max(0.0, min(1.0, sim_original))
                
                # Similarity to negated key clause (take max across negation variants)
                sim_negated = max(
                    float(np.dot(neg_vec, a_vec)) for neg_vec in neg_vecs
                )
                sim_negated = max(0.0, min(1.0, sim_negated))
                
                # Contradiction signal: answer is closer to the negated meaning
                # than to the original, AND both similarities are reasonably high
                # (indicating the topic is the same, just direction is flipped)
                margin = sim_negated - sim_original
                
                if (margin > 0.04 and 
                    sim_negated > 0.55 and 
                    sim_original > 0.35 and
                    sim_original < 0.80):
                    # Double-check with topic overlap to avoid noise
                    same_topic, overlap = _clause_topic_overlap(k_clause, a_clause, threshold=0.30)
                    if same_topic:
                        findings.append({
                            'type': 'DEEP_SEMANTIC_CONTRADICTION',
                            'description': (
                                f"Kontradiksi semantik mendalam: Jawaban secara makna lebih dekat ke negasi kunci "
                                f"(sim_negasi={sim_negated:.3f}) daripada ke kunci asli (sim_asli={sim_original:.3f}). "
                                f"Kunci: \"{k_clause_clean}\", "
                                f"Jawaban: \"{a_clause.strip()}\""
                            ),
                            'severity': 'FATAL',
                            'confidence': round(min(0.85, 0.70 + margin), 2),
                        })
        except Exception as e:
            logger.warning(f"[CONTRADICTION] SBERT deep analysis error: {e}")
            continue
    
    return findings


# ============================================================
# MAIN: Contradiction Analysis Engine
# ============================================================
class ContradictionDetector:
    """
    Deep Semantic Analysis engine for detecting fatal contradictions.
    
    Acts as a post-scoring penalty/bonus layer on top of the existing
    hybrid (SBERT + TF-IDF) scoring pipeline.
    
    Seven detection layers:
        1. Role Inversion (Subject-Object swap)
        2. Negation Contradiction (enhanced with multi-word + implicit)
        3. Direction Reversal (process direction swap)
        4. Antonym Substitution (keyword replaced by antonym)
        5. Causal / Temporal Inversion (cause-effect or time order swap)
        6. Quantifier / Modal Contradiction (scope or obligation flip)
        7. SBERT Deep Semantic (embedding-based implicit contradiction)
    
    Usage:
        detector = ContradictionDetector()
        result = detector.analyze("Indonesia dijajah Belanda",
                                   "Belanda dijajah Indonesia")
        # → verdict: "CONTRADICTION", penalty_factor: 0.0
    """
    
    def __init__(self):
        self._detectors = [
            ('role_inversion', _detect_role_inversion),
            ('negation', _detect_negation_contradiction),
            ('direction_reversal', _detect_direction_reversal),
            ('antonym_substitution', _detect_antonym_contradiction),
            ('causal_temporal', _detect_causal_temporal_inversion),
            ('quantifier_modal', _detect_quantifier_modal_contradiction),
            ('deep_semantic', _detect_deep_semantic_contradiction),
        ]
    
    def analyze(self, key_text: str, answer_text: str) -> Dict:
        """
        Run all contradiction detectors on the key-answer pair.
        
        Args:
            key_text: Master key answer text (original, unprocessed)
            answer_text: Student answer text (original, unprocessed)
        
        Returns:
            Dict with keys:
                verdict: "CONTRADICTION" | "ENTAILMENT" | "NEUTRAL"
                confidence: float 0.0–1.0
                penalty_factor: float 0.0–1.0 (multiplied with score)
                details: List of finding dicts
                fatal_count: number of FATAL findings
                warning_count: number of WARNING findings
        """
        if not key_text or not answer_text:
            return self._neutral_result()
        
        if not key_text.strip() or not answer_text.strip():
            return self._neutral_result()
        
        all_findings = []
        
        for detector_name, detector_fn in self._detectors:
            try:
                findings = detector_fn(key_text, answer_text)
                all_findings.extend(findings)
            except Exception as e:
                logger.warning(
                    f"[CONTRADICTION] Detector '{detector_name}' error: {e}"
                )
        
        # Deduplicate findings by description similarity
        all_findings = self._deduplicate_findings(all_findings)
        
        # Count severities
        fatal_count = sum(1 for f in all_findings if f.get('severity') == 'FATAL')
        warning_count = sum(1 for f in all_findings if f.get('severity') == 'WARNING')
        
        # Determine verdict based on findings
        if fatal_count >= 2:
            # Multiple fatal findings → high confidence contradiction
            verdict = 'CONTRADICTION'
            confidence = min(0.99, max(f.get('confidence', 0.5) for f in all_findings))
            penalty_factor = 0.0  # Score will be capped at CONTRADICTION_SCORE_CAP
        elif fatal_count == 1:
            # Single fatal finding → contradiction (still severe)
            verdict = 'CONTRADICTION'
            confidence = all_findings[0].get('confidence', 0.80) if all_findings else 0.80
            penalty_factor = 0.0  # Score will be capped at CONTRADICTION_SCORE_CAP
        elif warning_count >= 2:
            # Multiple warnings → treat as contradiction
            verdict = 'CONTRADICTION'
            confidence = 0.70
            penalty_factor = WARNING_PENALTY
        elif warning_count == 1:
            # Single warning → neutral with slight penalty
            verdict = 'NEUTRAL'
            confidence = 0.50
            penalty_factor = 0.75  # 25% penalty
        else:
            # No findings → check for entailment signals
            return self._check_entailment(key_text, answer_text)
        
        return {
            'verdict': verdict,
            'confidence': round(confidence, 4),
            'penalty_factor': penalty_factor,
            'details': all_findings,
            'fatal_count': fatal_count,
            'warning_count': warning_count,
        }
    
    def _deduplicate_findings(self, findings: List[Dict]) -> List[Dict]:
        """Remove duplicate or overlapping findings."""
        if len(findings) <= 1:
            return findings
        
        unique = []
        seen_descriptions = set()
        
        for f in findings:
            desc = f.get('description', '')
            # Create a simplified key for deduplication
            # (same type + same key/answer clause pair = likely duplicate)
            desc_key = (f.get('type', ''), desc[:80])
            if desc_key not in seen_descriptions:
                seen_descriptions.add(desc_key)
                unique.append(f)
        
        return unique
    
    def _check_entailment(self, key_text: str, answer_text: str) -> Dict:
        """
        Check if the answer is a valid paraphrase/expansion of the key.
        No contradiction detected — check for positive entailment signals.
        
        Entailment signals:
        - Answer uses different words but same logical direction
        - Answer is more scientific/detailed than key
        - Answer preserves all entity relationships
        """
        key_norm = _normalize_text(key_text)
        ans_norm = _normalize_text(answer_text)
        
        # Simple heuristic: if answer uses significantly different vocabulary
        # but no contradiction was found, it could be a paraphrase
        k_tokens = set(key_norm.split())
        a_tokens = set(ans_norm.split())
        
        if not k_tokens or not a_tokens:
            return self._neutral_result()
        
        # Vocabulary overlap ratio
        overlap = len(k_tokens & a_tokens)
        total_unique = len(k_tokens | a_tokens)
        vocab_overlap = overlap / total_unique if total_unique > 0 else 0
        
        # If low word overlap but no contradiction → likely paraphrase
        if vocab_overlap < 0.40 and len(a_tokens) >= len(k_tokens) * 0.5:
            return {
                'verdict': 'ENTAILMENT',
                'confidence': 0.60,
                'penalty_factor': ENTAILMENT_BOOST,
                'details': [{
                    'type': 'PARAPHRASE',
                    'description': (
                        f"Jawaban menggunakan kalimat berbeda "
                        f"(tumpang tindih kata: {round(vocab_overlap * 100, 1)}%) "
                        f"tanpa kontradiksi terdeteksi — kemungkinan parafrase valid"
                    ),
                    'severity': 'INFO',
                }],
                'fatal_count': 0,
                'warning_count': 0,
            }
        
        return self._neutral_result()
    
    def _neutral_result(self) -> Dict:
        """Return a neutral result (no contradiction, no entailment)."""
        return {
            'verdict': 'NEUTRAL',
            'confidence': 0.0,
            'penalty_factor': 1.0,  # No change to score
            'details': [],
            'fatal_count': 0,
            'warning_count': 0,
        }
    
    def apply_penalty(self, score: float, analysis: Dict) -> float:
        """
        Apply the contradiction penalty/boost to a hybrid score.
        
        Args:
            score: Original hybrid score (0.0 - 1.0)
            analysis: Result from analyze()
        
        Returns:
            Adjusted score (0.0 - 1.0)
        """
        verdict = analysis.get('verdict', 'NEUTRAL')
        penalty_factor = analysis.get('penalty_factor', 1.0)
        
        if verdict == 'CONTRADICTION':
            if penalty_factor <= 0.0:
                # Fatal contradiction: hard cap
                return min(score, CONTRADICTION_SCORE_CAP)
            else:
                # Warning-level: apply proportional penalty
                return min(score * penalty_factor, score)
        
        elif verdict == 'ENTAILMENT':
            # Boost for valid paraphrase (capped at 1.0)
            return min(score * penalty_factor, 1.0)
        
        else:
            # Neutral: apply any minor penalty
            if penalty_factor < 1.0:
                return score * penalty_factor
            return score
