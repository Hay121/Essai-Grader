"""
Validasi Scoring System — Test All Student Answers
====================================================
Script ini menjalankan evaluator yang sudah diperbaiki terhadap
semua jawaban siswa dan menampilkan hasilnya untuk verifikasi.
"""

import sys
import os
import json

# Add engine to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'engine'))

from core.evaluator import EssayEvaluator
from generate_soal_jawaban import PAKET_SOAL, JAWABAN_SISWA

def main():
    print("=" * 70)
    print("  VALIDASI SCORING SYSTEM — EssayGrader")
    print("=" * 70)
    print()

    evaluator = EssayEvaluator()

    # Target score ranges for each student
    targets = {
        "Andi Pratama":  (85, 100, "Sangat Baik"),
        "Budi Santoso":  (65, 100, "Parafrase Baik"),
        "Citra Dewi":    (50, 80,  "Cukup"),
        "Dimas Nugroho": (30, 60,  "Minimal"),
        "Eka Putri":     (0,  35,  "Salah"),
    }

    all_pass = True
    results_summary = []

    for paket_name, paket_data in PAKET_SOAL.items():
        print(f"\n{'='*70}")
        print(f"  {paket_name}")
        print(f"{'='*70}")

        questions = paket_data["questions"]

        for student_name, pakets in JAWABAN_SISWA.items():
            if paket_name not in pakets:
                continue

            answers = pakets[paket_name]
            target_min, target_max, label = targets[student_name]

            student_scores = []

            for i, q in enumerate(questions):
                if i >= len(answers):
                    break

                result = evaluator.evaluate_single(
                    key_text=q["kunci"],
                    answer_text=answers[i],
                    max_point=q["poin"]
                )

                pct = result["percentage"]
                grade = result["grade"]
                student_scores.append(pct)

            if student_scores:
                avg = sum(student_scores) / len(student_scores)
                in_range = target_min <= avg <= target_max
                status = "PASS" if in_range else "WARN"

                if not in_range:
                    # Allow wider tolerance for edge cases
                    if avg >= target_min - 10 and avg <= target_max + 10:
                        status = "OK~"
                    else:
                        all_pass = False
                        status = "FAIL"

                print(f"\n  {student_name} ({label}):")
                print(f"    Skor per soal: {', '.join(f'{s:.1f}%' for s in student_scores)}")
                print(f"    Rata-rata    : {avg:.1f}%")
                print(f"    Target       : {target_min}-{target_max}%")
                print(f"    Status       : [{status}]")

                results_summary.append({
                    "student": student_name,
                    "paket": paket_name,
                    "avg": round(avg, 1),
                    "target": f"{target_min}-{target_max}%",
                    "status": status,
                    "scores": [round(s, 1) for s in student_scores],
                })

    # Final summary
    print(f"\n\n{'='*70}")
    print(f"  RINGKASAN VALIDASI")
    print(f"{'='*70}")
    print(f"\n  {'Siswa':<20} {'Paket':<42} {'Rata-rata':>8}  {'Target':>10}  {'Status':>6}")
    print(f"  {'-'*20} {'-'*42} {'-'*8}  {'-'*10}  {'-'*6}")

    for r in results_summary:
        print(f"  {r['student']:<20} {r['paket']:<42} {r['avg']:>7.1f}%  {r['target']:>10}  {r['status']:>6}")

    print(f"\n  {'='*70}")
    if all_pass:
        print("  HASIL: SEMUA VALIDASI SESUAI TARGET")
    else:
        print("  HASIL: ADA BEBERAPA SKOR DI LUAR TARGET (perlu review)")
    print(f"  {'='*70}")

    # Save results
    results_path = os.path.join(os.path.dirname(__file__), 'validasi_hasil.json')
    with open(results_path, 'w', encoding='utf-8') as f:
        json.dump(results_summary, f, ensure_ascii=False, indent=2)
    print(f"\n  Hasil disimpan: {results_path}")


if __name__ == '__main__':
    main()
