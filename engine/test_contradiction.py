# -*- coding: utf-8 -*-
"""
Test Suite: Contradiction Detector - Directional Semantic Analysis
===================================================================
Tests the three detection layers:
  1. Role Inversion (Subject-Object swap)
  2. Negation Contradiction
  3. Directional Reversal
Plus entailment and neutral cases.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from core.contradiction_detector import ContradictionDetector

detector = ContradictionDetector()

# ============================================================
# TEST CASES
# ============================================================
test_cases = [
    # --- ROLE INVERSION ---
    {
        'name': 'Inversi Peran: Indonesia-Belanda (pasif)',
        'key': 'Indonesia dijajah oleh Belanda selama 350 tahun',
        'answer': 'Belanda dijajah oleh Indonesia selama 350 tahun',
        'expected_verdict': 'CONTRADICTION',
        'expected_max_score': 0.10,
    },
    {
        'name': 'Inversi Peran: Jepang-Indonesia (pasif)',
        'key': 'Indonesia diserang oleh Jepang pada tahun 1942',
        'answer': 'Jepang diserang oleh Indonesia pada tahun 1942',
        'expected_verdict': 'CONTRADICTION',
        'expected_max_score': 0.10,
    },
    {
        'name': 'Inversi Peran: Guru-Murid (aktif)',
        'key': 'Guru mengajarkan ilmu kepada murid',
        'answer': 'Murid mengajarkan ilmu kepada guru',
        'expected_verdict': 'CONTRADICTION',
        'expected_max_score': 0.10,
    },
    
    # --- NEGATION ---
    {
        'name': 'Negasi: Memerlukan vs Tidak Memerlukan',
        'key': 'Tumbuhan hijau memerlukan cahaya matahari untuk fotosintesis',
        'answer': 'Tumbuhan hijau tidak memerlukan cahaya matahari untuk fotosintesis',
        'expected_verdict': 'CONTRADICTION',
        'expected_max_score': 0.10,
    },
    {
        'name': 'Negasi: Bisa vs Tidak Bisa',
        'key': 'Manusia bisa hidup tanpa air selama tiga hari',
        'answer': 'Manusia tidak bisa hidup tanpa air selama tiga hari',
        'expected_verdict': 'CONTRADICTION',
        'expected_max_score': 0.10,
    },
    
    # --- DIRECTIONAL REVERSAL ---
    {
        'name': 'Arah Terbalik: Energi cahaya -> kimia',
        'key': 'Energi cahaya diubah menjadi energi kimia dalam fotosintesis',
        'answer': 'Energi kimia diubah menjadi energi cahaya dalam fotosintesis',
        'expected_verdict': 'CONTRADICTION',
        'expected_max_score': 0.10,
    },
    {
        'name': 'Arah Terbalik: dari X ke Y',
        'key': 'Air berubah dari cair menjadi gas saat dipanaskan',
        'answer': 'Air berubah dari gas menjadi cair saat dipanaskan',
        'expected_verdict': 'CONTRADICTION',
        'expected_max_score': 0.10,
    },
    
    # --- ENTAILMENT (Parafrase Valid) ---
    {
        'name': 'Parafrase: Fotosintesis (kalimat berbeda, makna sama)',
        'key': 'Fotosintesis menghasilkan oksigen dan glukosa',
        'answer': 'Proses pembuatan makanan oleh tumbuhan menghasilkan O2 dan gula',
        'expected_verdict': 'ENTAILMENT',
        'expected_max_score': 1.0,
    },
    
    # --- NEUTRAL ---
    {
        'name': 'Netral: Jawaban sama persis',
        'key': 'Air mendidih pada suhu 100 derajat Celsius',
        'answer': 'Air mendidih pada suhu 100 derajat Celsius',
        'expected_verdict': 'NEUTRAL',
        'expected_max_score': 1.0,
    },
    {
        'name': 'Netral: Jawaban parsial tapi tidak kontradiktif',
        'key': 'Fotosintesis memerlukan cahaya matahari, air, dan karbondioksida',
        'answer': 'Fotosintesis memerlukan cahaya matahari dan air',
        'expected_verdict': 'NEUTRAL',
        'expected_max_score': 1.0,
    },
]


# ============================================================
# RUN TESTS
# ============================================================
def run_tests():
    print("=" * 70)
    print("  TEST: Contradiction Detector - Directional Semantic Analysis")
    print("=" * 70)
    
    passed = 0
    failed = 0
    
    for i, tc in enumerate(test_cases):
        result = detector.analyze(tc['key'], tc['answer'])
        verdict = result['verdict']
        
        # Check if applying penalty would cap score properly
        test_score = 0.95  # Simulate a high lexical score
        adjusted = detector.apply_penalty(test_score, result)
        
        verdict_ok = verdict == tc['expected_verdict']
        score_ok = adjusted <= tc['expected_max_score'] + 0.01  # Small tolerance
        
        status = "[PASS]" if (verdict_ok and score_ok) else "[FAIL]"
        
        if verdict_ok and score_ok:
            passed += 1
        else:
            failed += 1
        
        print(f"\n{'-' * 70}")
        print(f"  Test {i+1}: {tc['name']}")
        print(f"  Status: {status}")
        print(f"  Kunci   : {tc['key']}")
        print(f"  Jawaban : {tc['answer']}")
        print(f"  Verdict : {verdict} (expected: {tc['expected_verdict']}) {'OK' if verdict_ok else 'FAIL'}")
        print(f"  Score   : 0.95 -> {round(adjusted, 4)} (max: {tc['expected_max_score']}) {'OK' if score_ok else 'FAIL'}")
        
        if result['details']:
            for d in result['details']:
                print(f"  Detail  : [{d['type']}] {d['description']}")
        
        if not (verdict_ok and score_ok):
            print(f"  >>> EXPECTED: verdict={tc['expected_verdict']}, max_score={tc['expected_max_score']}")
            print(f"  >>> GOT:      verdict={verdict}, score={round(adjusted, 4)}")
            print(f"  >>> Full result: {result}")
    
    print(f"\n{'=' * 70}")
    print(f"  RESULTS: {passed} passed, {failed} failed, {len(test_cases)} total")
    print(f"{'=' * 70}")
    
    return failed == 0


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
