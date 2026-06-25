"""
Generate Ujicoba Kontradiksi Kompleks
======================================
Script ini menguji keandalan sistem deteksi kontradiksi baru pada kalimat yang kompleks,
lalu menghasilkan report dalam format HTML dan PDF.
"""

import sys
import os
import json
import subprocess

# Add engine to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'engine'))

from core.contradiction_detector import ContradictionDetector

# ============================================================
# DATA: SOAL UJICOBA
# ============================================================

UJICOBA_DATA = [
    {
        "id": 1,
        "subject": "Biologi",
        "soal": "Jelaskan peran fotosintesis dan respirasi dalam siklus karbon!",
        "kunci": "Fotosintesis menyerap karbondioksida dan menghasilkan oksigen. Sebaliknya, respirasi menyerap oksigen dan menghasilkan karbondioksida.",
        "jawaban_test": [
            {
                "label": "Tepat / Parafrase",
                "text": "Tumbuhan melakukan fotosintesis dengan mengambil karbondioksida lalu mengeluarkan oksigen. Sementara itu, proses respirasi membutuhkan oksigen dan mengeluarkan karbondioksida.",
                "expected": "NEUTRAL / ENTAILMENT"
            },
            {
                "label": "Antonym Substitution (Fatal)",
                "text": "Fotosintesis menyerap karbondioksida dan menghabiskan oksigen. Sebaliknya, respirasi menyerap oksigen dan menghasilkan karbondioksida.",
                "expected": "CONTRADICTION"
            },
            {
                "label": "Direction Reversal (Fatal)",
                "text": "Fotosintesis menyerap oksigen dan menghasilkan karbondioksida. Sebaliknya, respirasi menyerap karbondioksida dan menghasilkan oksigen.",
                "expected": "CONTRADICTION"
            },
            {
                "label": "Implicit Negation (Fatal)",
                "text": "Fotosintesis dapat berlangsung tanpa menyerap karbondioksida dan tetap menghasilkan oksigen.",
                "expected": "CONTRADICTION"
            }
        ]
    },
    {
        "id": 2,
        "subject": "Sejarah",
        "soal": "Jelaskan hubungan sebab-akibat antara Perang Dunia 2 dan Kemerdekaan Indonesia!",
        "kunci": "Kekalahan Jepang dalam Perang Dunia 2 menyebabkan terjadinya kekosongan kekuasaan (vacuum of power). Hal ini dimanfaatkan oleh para pemuda Indonesia untuk segera memproklamasikan kemerdekaan.",
        "jawaban_test": [
            {
                "label": "Tepat / Parafrase",
                "text": "Karena Jepang kalah di PD 2, terjadilah kekosongan kekuasaan di Indonesia. Kesempatan ini dipakai pemuda untuk mempercepat proklamasi kemerdekaan.",
                "expected": "NEUTRAL / ENTAILMENT"
            },
            {
                "label": "Causal Inversion (Fatal)",
                "text": "Proklamasi kemerdekaan Indonesia oleh para pemuda menyebabkan kekalahan Jepang dalam Perang Dunia 2 dan terjadinya kekosongan kekuasaan.",
                "expected": "CONTRADICTION"
            },
            {
                "label": "Temporal Inversion (Fatal)",
                "text": "Sesudah para pemuda memproklamasikan kemerdekaan, terjadilah kekalahan Jepang dalam Perang Dunia 2 yang memicu kekosongan kekuasaan.",
                "expected": "CONTRADICTION"
            },
            {
                "label": "Role Inversion (Fatal)",
                "text": "Kekalahan Jepang dimanfaatkan oleh penjajah Belanda untuk segera memproklamasikan kemerdekaan.",
                "expected": "CONTRADICTION"
            }
        ]
    },
    {
        "id": 3,
        "subject": "PKN",
        "soal": "Jelaskan hakikat kewajiban warga negara dalam membayar pajak!",
        "kunci": "Semua warga negara yang telah memenuhi syarat wajib membayar pajak. Pajak merupakan kontribusi wajib kepada negara yang akan digunakan untuk kesejahteraan rakyat.",
        "jawaban_test": [
            {
                "label": "Tepat / Parafrase",
                "text": "Setiap warga yang memenuhi kriteria diharuskan membayar pajak. Dana pajak adalah sumbangan wajib bagi negara untuk mendanai kesejahteraan masyarakat.",
                "expected": "NEUTRAL / ENTAILMENT"
            },
            {
                "label": "Quantifier Contradiction (Fatal)",
                "text": "Hanya beberapa warga negara yang telah memenuhi syarat wajib membayar pajak demi kesejahteraan rakyat.",
                "expected": "CONTRADICTION"
            },
            {
                "label": "Modal Contradiction (Fatal)",
                "text": "Semua warga negara yang telah memenuhi syarat boleh memilih untuk tidak membayar pajak karena sifatnya opsional.",
                "expected": "CONTRADICTION"
            },
            {
                "label": "Deep Semantic Contradiction (Fatal)",
                "text": "Warga negara bebas dari keharusan menyetorkan pajak kepada negara, karena kesejahteraan rakyat ditanggung pemerintah.",
                "expected": "CONTRADICTION"
            }
        ]
    }
]

def generate_report_html(results):
    html = '''<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Laporan Ujicoba Deteksi Kontradiksi Kompleks</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
        
        :root {
            --primary: #1a365d;
            --accent: #3182ce;
            --bg: #ffffff;
            --text: #1a202c;
            --border: #e2e8f0;
            --danger: #e53e3e;
            --success: #38a169;
            --warning: #d69e2e;
        }

        body {
            font-family: 'Inter', sans-serif;
            line-height: 1.6;
            color: var(--text);
            max-width: 210mm;
            margin: 0 auto;
            padding: 20mm;
            background: var(--bg);
        }

        h1 { color: var(--primary); border-bottom: 2px solid var(--primary); padding-bottom: 10px; }
        h2 { color: var(--accent); margin-top: 30px; }
        
        .soal-card {
            background: #f7fafc;
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 30px;
        }

        .kunci-box {
            background: #ebf8ff;
            border-left: 4px solid var(--accent);
            padding: 10px 15px;
            margin: 15px 0;
            font-weight: 500;
        }

        .test-case {
            background: white;
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 15px;
            margin-bottom: 15px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }

        .test-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
            font-weight: 600;
        }

        .badge {
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.85em;
            color: white;
        }

        .badge-contradiction { background: var(--danger); }
        .badge-entailment { background: var(--success); }
        .badge-neutral { background: var(--warning); }

        .answer-text { margin-bottom: 10px; font-style: italic; }
        
        .findings {
            background: #fff5f5;
            border: 1px solid #fed7d7;
            padding: 10px;
            border-radius: 4px;
            font-size: 0.9em;
        }

        .finding-item { margin-bottom: 5px; }
        .finding-type { font-weight: 600; color: var(--danger); }
        
        @media print {
            body { padding: 0; }
            .soal-card { page-break-inside: avoid; }
            .test-case { page-break-inside: avoid; }
        }
    </style>
</head>
<body>
    <h1>Laporan Ujicoba Deteksi Kontradiksi Kompleks</h1>
    <p>Pengujian algoritma <em>Deep Semantic Contradiction Detection</em> pada 7 layer analisis baru.</p>
'''

    for soal_res in results:
        html += f'''
    <div class="soal-card">
        <h2>Soal {soal_res["id"]} ({soal_res["subject"]})</h2>
        <p><strong>Pertanyaan:</strong> {soal_res["soal"]}</p>
        <div class="kunci-box">
            <strong>Kunci Jawaban:</strong><br>
            {soal_res["kunci"]}
        </div>
        
        <h3>Hasil Analisis Jawaban Siswa:</h3>
'''
        for test in soal_res["tests"]:
            verdict = test["result"]["verdict"]
            badge_class = f"badge-{verdict.lower()}"
            
            html += f'''
        <div class="test-case">
            <div class="test-header">
                <span>Kasus Uji: {test["label"]}</span>
                <span class="badge {badge_class}">Verdict: {verdict}</span>
            </div>
            <div class="answer-text">"{test["text"]}"</div>
'''
            if test["result"]["details"]:
                html += '<div class="findings"><strong>Temuan:</strong><ul>'
                for detail in test["result"]["details"]:
                    html += f'<li class="finding-item"><span class="finding-type">[{detail["type"]}]</span> {detail["description"]}</li>'
                html += '</ul></div>'
            elif verdict == "ENTAILMENT":
                html += '<div class="findings" style="background: #f0fff4; border-color: #c6f6d5;"><span style="color: #2f855a; font-weight: 600;">Valid Paraphrase</span> - Tidak ditemukan kontradiksi.</div>'
            
            html += '</div>'
            
        html += '</div>'

    html += '</body></html>'
    return html

def try_convert_to_pdf(html_path, pdf_path):
    chrome_paths = [
        r'C:\Program Files\Google\Chrome\Application\chrome.exe',
        r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
        os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe'),
    ]
    edge_paths = [
        r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
        r'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
    ]

    browser_path = None
    for p in chrome_paths + edge_paths:
        if os.path.exists(p):
            browser_path = p
            break

    if not browser_path:
        return False

    try:
        abs_html = os.path.abspath(html_path)
        file_url = f'file:///{abs_html.replace(os.sep, "/")}'

        cmd = [
            browser_path, '--headless', '--disable-gpu', '--no-sandbox',
            '--disable-software-rasterizer',
            '--run-all-compositor-stages-before-draw',
            '--virtual-time-budget=10000',
            f'--print-to-pdf={pdf_path}',
            '--print-to-pdf-no-header',
            '--no-pdf-header-footer',
            file_url
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 1000
    except Exception as e:
        print(f"Browser error: {e}")
        return False

def main():
    print("="*60)
    print("MENGUJI DETEKSI KONTRADIKSI KOMPLEKS")
    print("="*60)
    
    detector = ContradictionDetector()
    results = []

    # Run tests
    for data in UJICOBA_DATA:
        print(f"\n[{data['subject']}] Menganalisis Soal {data['id']}...")
        soal_res = {
            "id": data["id"],
            "subject": data["subject"],
            "soal": data["soal"],
            "kunci": data["kunci"],
            "tests": []
        }
        
        for test in data["jawaban_test"]:
            print(f"  -> Uji: {test['label']}")
            analysis = detector.analyze(data["kunci"], test["text"])
            soal_res["tests"].append({
                "label": test["label"],
                "text": test["text"],
                "expected": test["expected"],
                "result": analysis
            })
            
            status = "[PASS]" if analysis["verdict"] in test["expected"] else "[FAIL]"
            print(f"     Verdict: {analysis['verdict']} | {status}")
            for d in analysis.get('details', []):
                print(f"       - [{d['type']}] {d['description'][:80]}...")
                
        results.append(soal_res)

    # Generate HTML
    base_dir = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(base_dir, 'laporan_ujicoba_kontradiksi.html')
    pdf_path = os.path.join(base_dir, 'laporan_ujicoba_kontradiksi.pdf')
    
    print("\nMenyimpan laporan HTML...")
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(generate_report_html(results))
    print(f"OK: {html_path}")

    # Generate PDF
    print("\nMengkonversi ke PDF...")
    if try_convert_to_pdf(html_path, pdf_path):
        print(f"OK: PDF berhasil dibuat: {pdf_path}")
    else:
        print(f"WARNING: Gagal membuat PDF otomatis. Buka {html_path} dan Print ke PDF.")

if __name__ == '__main__':
    main()
