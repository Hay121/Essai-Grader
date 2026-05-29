"""
EssayGrader — Contradiction Detector Module (Directional Semantic Analysis)
============================================================================
Detects fatal semantic contradictions between a key answer and student answer
that lexical matching (TF-IDF) and even SBERT cosine similarity would miss.

Three Detection Layers:
    1. Role Inversion: Subject-Object swap ("A dijajah B" vs "B dijajah A")
    2. Negation Contradiction: Negation flipping facts ("perlu" vs "tidak perlu")
    3. Directional Reversal: Process direction swap ("X → Y" vs "Y → X")

Verdict System:
    CONTRADICTION: Fatal semantic error → score capped at 0.10
    ENTAILMENT:    Correct paraphrase   → score boosted × 1.05
    NEUTRAL:       No directional issue  → score unchanged

Design:
    Fully rule-based using Indonesian regex patterns.
    No external ML dependencies — works in both SBERT and Fallback modes.

References:
    Dagan, Glickman & Magnini (2005). "The PASCAL Recognising Textual Entailment Challenge."
    MacCartney & Manning (2008). "Modeling Semantic Containment and Exclusion in NLP."
"""

import re
import logging
from typing import List, Dict, Tuple, Optional

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
ENTAILMENT_BOOST = 1.05
WARNING_PENALTY = 0.50


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
# DETECTOR 2: Negation Contradiction
# ============================================================
def _detect_negation_contradiction(key_text: str, answer_text: str) -> List[Dict]:
    """
    Detect if the student answer negates a core fact from the key.
    
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
        k_negations = [t for t in k_tokens if t in NEGATION_TOKENS]
        k_has_negation = len(k_negations) > 0
        
        for a_clause in ans_clauses:
            a_norm = _normalize_text(a_clause)
            a_tokens = a_norm.split()
            a_negations = [t for t in a_tokens if t in NEGATION_TOKENS]
            a_has_negation = len(a_negations) > 0
            
            # Check if clauses are about the same topic (significant word overlap)
            k_content = {t for t in k_tokens if t not in NEGATION_TOKENS and len(t) >= 3}
            a_content = {t for t in a_tokens if t not in NEGATION_TOKENS and len(t) >= 3}
            
            if not k_content or not a_content:
                continue
            
            overlap = len(k_content & a_content)
            overlap_ratio = overlap / max(len(k_content), len(a_content))
            
            # Only compare clauses about the same topic (>40% content overlap)
            if overlap_ratio < 0.40:
                continue
            
            # Negation delta: one has negation, other doesn't
            # (or different number of negations → odd means flipped)
            k_neg_count = len(k_negations)
            a_neg_count = len(a_negations)
            neg_delta = abs(k_neg_count - a_neg_count)
            
            if neg_delta % 2 == 1:  # Odd delta = meaning flipped
                # Determine which added/removed negation
                if a_neg_count > k_neg_count:
                    # Answer has MORE negations than key
                    added_negs = [t for t in a_negations if t not in k_negations]
                    neg_word = added_negs[0] if added_negs else a_negations[0]
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
                    # Key has MORE negations than answer
                    removed_negs = [t for t in k_negations if t not in a_negations]
                    neg_word = removed_negs[0] if removed_negs else k_negations[0]
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
# MAIN: Contradiction Analysis Engine
# ============================================================
class ContradictionDetector:
    """
    Directional Semantic Analysis engine for detecting fatal contradictions.
    
    Acts as a post-scoring penalty/bonus layer on top of the existing
    hybrid (SBERT + TF-IDF) scoring pipeline.
    
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
