/**
 * EssayGrader — Main Application Controller v3.0
 * Features:
 *   - Per-student answer input (all questions at once)
 *   - Linear algebra process display in Live Preview
 *   - Dashboard stats via /api/stats
 *   - No seed data
 */
const App = (() => {
    // State
    let currentView = 'packages';
    let currentExamId = null;
    let exams = [];
    let currentQuestions = []; // Questions for selected exam in answers view

    // ============================================================
    // INIT
    // ============================================================
    function init() {
        updateDatetime();
        setInterval(updateDatetime, 1000);
        checkEngine();
        loadDashboard();

        // Nav buttons
        document.querySelectorAll('.nav-item').forEach(btn => {
            btn.addEventListener('click', () => navigate(btn.dataset.view));
        });

        setupEventListeners();
    }

    function setupEventListeners() {
        // Welcome Screen
        const btnContinue = document.getElementById('btnContinue');
        if (btnContinue) {
            btnContinue.addEventListener('click', () => {
                const welcomeScreen = document.getElementById('welcomeScreen');
                if (welcomeScreen) {
                    welcomeScreen.classList.add('slide-up');
                    setTimeout(() => welcomeScreen.classList.add('hidden'), 800);
                }
            });
        }

        // Create exam form
        const examForm = document.getElementById('createExamForm');
        if (examForm) examForm.addEventListener('submit', handleCreateExam);

        // Close detail
        const closeBtn = document.getElementById('closeDetailBtn');
        if (closeBtn) closeBtn.addEventListener('click', closeExamDetail);

        // Add question form
        const qForm = document.getElementById('addQuestionForm');
        if (qForm) qForm.addEventListener('submit', handleAddQuestion);

        // Submit answer form
        const aForm = document.getElementById('submitAnswerForm');
        if (aForm) aForm.addEventListener('submit', handleSubmitAnswer);

        // Exam select on answers page
        const ansExamSel = document.getElementById('answerExamSelect');
        if (ansExamSel) ansExamSel.addEventListener('change', handleAnswerExamChange);

        // Evaluate
        const evalExamSel = document.getElementById('evalExamSelect');
        if (evalExamSel) evalExamSel.addEventListener('change', handleEvalExamChange);
        const evalBtn = document.getElementById('evaluateBtn');
        if (evalBtn) evalBtn.addEventListener('click', handleEvaluate);

        // Preview toggle
        const previewToggle = document.getElementById('previewToggle');
        if (previewToggle) previewToggle.addEventListener('click', togglePreview);
        const previewBtn = document.getElementById('previewBtn');
        if (previewBtn) previewBtn.addEventListener('click', handlePreview);
    }

    // ============================================================
    // NAVIGATION
    // ============================================================
    function navigate(view) {
        currentView = view;

        document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.view-panel').forEach(p => p.classList.remove('active'));

        const btn = document.querySelector(`.nav-item[data-view="${view}"]`);
        const panel = document.getElementById(`view-${view}`);
        if (btn) btn.classList.add('active');
        if (panel) panel.classList.add('active');

        switch (view) {
            case 'packages': loadDashboard(); break;
            case 'answers': loadAnswersView(); break;
            case 'results': loadResultsView(); break;
        }
    }

    // ============================================================
    // DASHBOARD / PACKAGES
    // ============================================================
    async function loadDashboard() {
        try {
            const data = await API.listExams();
            exams = data.exams || [];
            renderExamList(exams);
            updateStats();
        } catch (e) {
            renderExamList([]);
        }
    }

    function renderExamList(list) {
        const container = document.getElementById('examList');
        if (!container) return;

        if (!list.length) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">
                        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20"/></svg>
                    </div>
                    <p>Belum ada paket ujian. Buat paket baru untuk memulai.</p>
                </div>`;
            return;
        }

        container.innerHTML = '<div class="exam-grid">' + list.map(e => `
            <div class="exam-card ${currentExamId === e.id ? 'selected' : ''}" onclick="App.openExam(${e.id})">
                <div class="exam-card-subject">${e.subject || 'Umum'}</div>
                <div class="exam-card-title">${e.title}</div>
                <div class="exam-card-meta">${e.question_count || 0} soal${e.description ? ' · ' + e.description : ''}</div>
            </div>
        `).join('') + '</div>';
    }

    async function updateStats() {
        const setVal = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
        try {
            const stats = await API.getStats();
            setVal('statExams', stats.exam_count || 0);
            setVal('statQuestions', stats.question_count || 0);
            setVal('statStudents', stats.answer_count || 0);
        } catch {
            setVal('statExams', exams.length);
        }
    }

    // ============================================================
    // EXAM DETAIL (INLINE)
    // ============================================================
    function openExam(examId) {
        currentExamId = examId;
        loadExamDetail(examId);
        renderExamList(exams);
    }

    function closeExamDetail() {
        currentExamId = null;
        document.getElementById('examDetailSection').classList.add('hidden');
        renderExamList(exams);
    }

    async function loadExamDetail(examId) {
        const section = document.getElementById('examDetailSection');
        const container = document.getElementById('examDetailContent');
        if (!section || !container) return;

        section.classList.remove('hidden');
        container.innerHTML = '<div class="flex-center"><div class="spinner"></div></div>';

        try {
            const data = await API.getExam(examId);
            const exam = data.exam;
            const questions = data.questions || [];

            document.getElementById('examDetailTitle').textContent = exam.title;
            document.getElementById('examDetailSubject').textContent = exam.subject;

            if (!questions.length) {
                container.innerHTML = '<div class="empty-state"><p>Belum ada soal. Tambahkan soal di bawah.</p></div>';
            } else {
                container.innerHTML = questions.map(q => `
                    <div class="question-item">
                        <div class="question-num">Soal ${q.question_number} · ${q.max_point} poin</div>
                        <div class="question-text">${q.question_text}</div>
                        ${q.key_text ? `<div class="key-preview">Kunci Jawaban: ${q.key_text}</div>` : ''}
                    </div>
                `).join('');
            }
        } catch (e) {
            container.innerHTML = `<div class="alert alert-error">${e.message}</div>`;
        }
    }

    // ============================================================
    // CREATE EXAM
    // ============================================================
    async function handleCreateExam(e) {
        e.preventDefault();
        const title = document.getElementById('newExamTitle').value.trim();
        const subject = document.getElementById('newExamSubject').value.trim();
        const desc = document.getElementById('newExamDesc').value.trim();
        if (!title) return;

        try {
            const res = await API.createExam({ title, subject, description: desc });
            showAlert('createExamAlert', 'success', `Paket ujian "${title}" berhasil dibuat!`);
            e.target.reset();
            currentExamId = res.id;
            loadDashboard();
        } catch (err) {
            showAlert('createExamAlert', 'error', err.message);
        }
    }

    // ============================================================
    // ADD QUESTION
    // ============================================================
    async function handleAddQuestion(e) {
        e.preventDefault();
        if (!currentExamId) return showAlert('addQAlert', 'error', 'Pilih paket ujian dulu');

        const qText = document.getElementById('questionText').value.trim();
        const maxPt = parseFloat(document.getElementById('questionMaxPoint').value) || 10;
        const keyText = document.getElementById('keyText').value.trim();

        if (!qText || !keyText) return showAlert('addQAlert', 'error', 'Isi soal dan kunci jawaban');

        try {
            await API.addQuestion(currentExamId, { question_text: qText, max_point: maxPt, key_text: keyText });
            showAlert('addQAlert', 'success', 'Soal berhasil ditambahkan!');
            e.target.reset();
            loadExamDetail(currentExamId);
            updateStats();
        } catch (err) {
            showAlert('addQAlert', 'error', err.message);
        }
    }

    // ============================================================
    // ANSWERS VIEW — Per Student, All Questions
    // ============================================================
    async function loadAnswersView() {
        const examSel = document.getElementById('answerExamSelect');
        if (!examSel) return;

        try {
            const data = await API.listExams();
            exams = data.exams || [];
            examSel.innerHTML = '<option value="">-- Pilih paket --</option>' +
                exams.map(e => `<option value="${e.id}" ${e.id === currentExamId ? 'selected' : ''}>${e.title} — ${e.subject}</option>`).join('');

            if (currentExamId) {
                handleAnswerExamChange();
            }
        } catch { }
    }

    async function handleAnswerExamChange() {
        const examId = parseInt(document.getElementById('answerExamSelect').value);
        const container = document.getElementById('answerFieldsContainer');
        const fields = document.getElementById('answerFields');
        const submitBtn = document.getElementById('submitAnswerBtn');
        const title = document.getElementById('answerFieldsTitle');

        if (!examId || !container || !fields) {
            if (container) container.classList.add('hidden');
            if (submitBtn) submitBtn.disabled = true;
            currentQuestions = [];
            return;
        }

        currentExamId = examId;

        try {
            const data = await API.getExam(examId);
            currentQuestions = data.questions || [];

            if (!currentQuestions.length) {
                container.classList.add('hidden');
                showAlert('answerAlert', 'info', 'Paket ujian ini belum memiliki soal. Tambahkan soal terlebih dahulu di halaman Paket Soal.');
                return;
            }

            title.textContent = `Jawaban untuk ${currentQuestions.length} soal — ${data.exam.title}`;
            container.classList.remove('hidden');
            submitBtn.disabled = false;

            // Render answer fields for each question
            fields.innerHTML = currentQuestions.map((q, idx) => `
                <div class="answer-field-item">
                    <div class="answer-field-header">
                        <div class="answer-field-number">Soal ${q.question_number}</div>
                        <div class="answer-field-points">${q.max_point} poin</div>
                    </div>
                    <div class="answer-field-question">${escapeHtml(q.question_text)}</div>
                    ${q.key_text ? `<div class="answer-field-key">
                        <div class="answer-field-key-label">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/></svg>
                            Kunci Jawaban:
                        </div>
                        <div class="answer-field-key-text">${escapeHtml(q.key_text)}</div>
                    </div>` : ''}
                    <textarea class="form-textarea answer-textarea" id="answerQ_${q.id}" rows="4"
                        placeholder="Tuliskan jawaban siswa untuk soal ${q.question_number}..." data-qid="${q.id}"></textarea>
                </div>
            `).join('');
        } catch (err) {
            showAlert('answerAlert', 'error', err.message);
        }
    }

    async function handleSubmitAnswer(e) {
        e.preventDefault();

        const name = document.getElementById('studentName').value.trim();
        if (!name) {
            showAlert('answerAlert', 'error', 'Masukkan nama siswa');
            return;
        }

        if (!currentQuestions.length) {
            showAlert('answerAlert', 'error', 'Pilih paket ujian terlebih dahulu');
            return;
        }

        // Collect all answers
        const answers = [];
        let emptyCount = 0;
        for (const q of currentQuestions) {
            const textarea = document.getElementById(`answerQ_${q.id}`);
            const text = textarea ? textarea.value.trim() : '';
            if (!text) emptyCount++;
            answers.push({ question_id: q.id, raw_text: text });
        }

        // Check if all answers are empty
        if (emptyCount === currentQuestions.length) {
            showAlert('answerAlert', 'error', 'Isi minimal satu jawaban sebelum menyimpan.');
            return;
        }

        // Filter out empty answers
        const validAnswers = answers.filter(a => a.raw_text);

        const btn = document.getElementById('submitAnswerBtn');
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner"></span> Menyimpan...';

        try {
            const res = await API.submitBulk({
                student_name: name,
                answers: validAnswers,
            });

            showAlert('answerAlert', 'success',
                `🎉 ${res.count} jawaban dari ${name} berhasil disimpan!`);

            // Clear form
            document.getElementById('studentName').value = '';
            currentQuestions.forEach(q => {
                const ta = document.getElementById(`answerQ_${q.id}`);
                if (ta) ta.value = '';
            });

            // Update stats
            updateStats();
        } catch (err) {
            showAlert('answerAlert', 'error', err.message);
        }

        btn.disabled = false;
        btn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 2L11 13"/><path d="M22 2l-7 20-4-9-9-4 20-7z"/></svg> Simpan Semua Jawaban`;
    }

    // ============================================================
    // RESULTS VIEW
    // ============================================================
    async function loadResultsView() {
        const examSel = document.getElementById('evalExamSelect');
        if (!examSel) return;

        try {
            const data = await API.listExams();
            exams = data.exams || [];
            examSel.innerHTML = '<option value="">-- Pilih paket --</option>' +
                exams.map(e => `<option value="${e.id}" ${e.id === currentExamId ? 'selected' : ''}>${e.title}</option>`).join('');
            handleEvalExamChange();
        } catch { }
    }

    function handleEvalExamChange() {
        const examId = parseInt(document.getElementById('evalExamSelect').value);
        const btn = document.getElementById('evaluateBtn');
        if (examId) {
            currentExamId = examId;
            btn.disabled = false;
            loadResults(examId);
        } else {
            btn.disabled = true;
        }
    }

    async function handleEvaluate() {
        if (!currentExamId) return;
        const btn = document.getElementById('evaluateBtn');
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner"></span> Memproses...';

        try {
            const res = await API.evaluate(currentExamId);
            showAlert('resultAlert', 'success', `Evaluasi selesai! ${res.evaluated} jawaban diproses.`);
            loadResults(currentExamId);
        } catch (err) {
            showAlert('resultAlert', 'error', err.message);
        }

        btn.disabled = false;
        btn.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg> Proses Evaluasi`;
    }

    async function loadResults(examId) {
        const container = document.getElementById('resultsContent');
        if (!container) return;
        container.innerHTML = '<div class="flex-center" style="padding:2rem"><div class="spinner"></div></div>';

        try {
            const [resultsData, rankingsData, examData] = await Promise.all([
                API.getResults(examId),
                API.getRankings(examId),
                API.getExam(examId),
            ]);

            const results = resultsData.results || [];
            const rankings = rankingsData.rankings || [];
            const questions = examData.questions || [];

            if (!results.length) {
                container.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">
                            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M18 20V10"/><path d="M12 20V4"/><path d="M6 20v-6"/></svg>
                        </div>
                        <p>Belum ada hasil evaluasi. Jalankan evaluasi terlebih dahulu.</p>
                    </div>`;
                return;
            }

            let html = '';

            // --- Rankings ---
            html += '<div class="card mb-2">';
            html += '<div class="card-header">Peringkat Siswa</div>';
            rankings.forEach((r, i) => {
                const cls = i < 3 ? `rank-${i + 1}` : 'rank-default';
                const scoreColor = getScoreColor(r.percentage);
                html += `
                <div class="ranking-item ${cls}">
                    <div class="rank-badge">${r.rank}</div>
                    <div class="rank-info">
                        <div class="rank-name">${r.student_name}</div>
                        <div class="rank-detail">${r.questions_answered} soal dijawab</div>
                    </div>
                    <div class="rank-score">
                        <div class="rank-score-value" style="color:${scoreColor}">${r.percentage.toFixed(0)}%</div>
                        <div class="rank-score-total">${r.total_score.toFixed(1)} / ${r.max_possible.toFixed(0)}</div>
                    </div>
                </div>`;
            });
            html += '</div>';

            // --- Charts ---
            html += `<div class="grid-2 mb-2">
                <div class="card">
                    <div class="card-header">Grafik Peringkat</div>
                    <div style="height:${Math.max(200, rankings.length * 35)}px">
                        <canvas id="chartRanking"></canvas>
                    </div>
                </div>
                <div class="card">
                    <div class="card-header">Distribusi Nilai</div>
                    <div style="height:250px">
                        <canvas id="chartDistribution"></canvas>
                    </div>
                </div>
            </div>`;

            // --- Results Table ---
            html += '<div class="card">';
            html += '<div class="card-header">Detail Nilai</div>';
            html += '<table class="data-table"><thead><tr>';
            html += '<th>Siswa</th><th>Soal</th><th>Nilai</th><th>Grade</th><th>Catatan</th>';
            html += '</tr></thead><tbody>';

            results.forEach(r => {
                const pct = (r.final_point / r.max_point * 100);
                const grade = pct >= 85 ? 'A' : pct >= 75 ? 'B' : pct >= 60 ? 'C' : pct >= 40 ? 'D' : 'E';
                const gradeClass = `grade-${grade.toLowerCase()}`;

                const missing = (r.missing_keywords || []);
                let noteHtml = '';
                if (missing.length > 0 && pct < 75) {
                    noteHtml = '<span class="form-hint">Kurang: ' +
                        missing.slice(0, 4).map(k => `<span class="kw-tag kw-miss">${k}</span>`).join('') +
                        '</span>';
                } else if (pct >= 85) {
                    noteHtml = '<span class="form-hint" style="color:var(--success)">Jawaban sangat baik</span>';
                } else {
                    noteHtml = '<span class="form-hint">-</span>';
                }

                html += `<tr>
                    <td style="font-weight:600">${r.student_name}</td>
                    <td>Soal ${r.question_number}</td>
                    <td style="font-weight:700">${r.final_point.toFixed(1)} / ${r.max_point}</td>
                    <td><span class="score-badge ${gradeClass}">${grade}</span></td>
                    <td>${noteHtml}</td>
                </tr>`;
            });

            html += '</tbody></table></div>';

            container.innerHTML = html;

            // Render charts
            setTimeout(() => {
                Charts.renderRankingChart('chartRanking', rankings);
                Charts.renderDistributionChart('chartDistribution', results);
            }, 100);

        } catch (e) {
            container.innerHTML = `<div class="alert alert-error">${e.message}</div>`;
        }
    }

    // ============================================================
    // PREVIEW (Cek Cepat) — With Linear Algebra Process Display
    // ============================================================
    function togglePreview() {
        const section = document.getElementById('previewSection');
        const chevron = document.getElementById('previewChevron');
        section.classList.toggle('hidden');
        chevron.classList.toggle('open');
    }

    async function handlePreview() {
        const keyText = document.getElementById('previewKey').value.trim();
        const ansText = document.getElementById('previewAnswer').value.trim();
        const maxPt = parseFloat(document.getElementById('previewMaxPoint').value) || 10;
        const resultDiv = document.getElementById('previewResult');
        if (!keyText || !ansText) {
            showAlert('resultAlert', 'error', 'Isi kunci jawaban dan jawaban siswa terlebih dahulu.');
            return;
        }

        const btn = document.getElementById('previewBtn');
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner"></span> Mengecek...';

        try {
            const res = await API.preview({ key_text: keyText, answer_text: ansText, max_point: maxPt });

            const percentage = typeof res.percentage === 'number' ? res.percentage : 0;
            const grade = res.grade || 'E';
            const finalPoint = typeof res.final_point === 'number' ? res.final_point : 0;
            const maxPoint = typeof res.max_point === 'number' ? res.max_point : maxPt;
            const color = getScoreColor(percentage);

            const matched = (Array.isArray(res.matched) ? res.matched : []).slice(0, 8).map(k =>
                `<span class="kw-tag kw-match">${escapeHtml(String(k))}</span>`).join('');
            const missing = (Array.isArray(res.missing) ? res.missing : []).slice(0, 8).map(k =>
                `<span class="kw-tag kw-miss">${escapeHtml(String(k))}</span>`).join('');

            let processHtml = '';
            if (res.process) {
                processHtml = renderProcessSteps(res.process);
            }

            resultDiv.innerHTML = `
                <div class="preview-result-card">
                    <div class="preview-score-row">
                        <div class="preview-score-big" style="color:${color}">${percentage.toFixed(0)}%</div>
                        <div>
                            <div><span class="score-badge grade-${grade.toLowerCase()}" style="font-size:1rem">${grade}</span></div>
                            <div class="preview-score-detail mt-1">Nilai: ${finalPoint.toFixed(1)} / ${maxPoint}</div>
                        </div>
                    </div>
                    <div class="progress-bar mb-1">
                        <div class="progress-fill ${percentage >= 75 ? 'high' : percentage >= 60 ? 'mid' : percentage >= 40 ? 'low' : 'very-low'}" style="width:${percentage}%"></div>
                    </div>
                    ${matched ? '<div class="mb-1"><span class="form-hint">Kata kunci cocok:</span> ' + matched + '</div>' : ''}
                    ${missing ? '<div class="mb-1"><span class="form-hint">Kata kunci kurang:</span> ' + missing + '</div>' : ''}
                </div>
                ${processHtml}`;
            resultDiv.classList.remove('hidden');
        } catch (e) {
            resultDiv.innerHTML = `<div class="alert alert-error">${escapeHtml(e.message)}</div>`;
            resultDiv.classList.remove('hidden');
        }

        btn.disabled = false;
        btn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg> Cek Nilai`;
    }

    // ============================================================
    // RENDER LINEAR ALGEBRA PROCESS STEPS
    // ============================================================
    function renderProcessSteps(process) {
        if (!process) return '';

        let html = '<div class="process-container">';
        html += '<div class="process-title">📐 Proses Aljabar Linier (Bukti Analisis)</div>';

        // Step 1: Preprocessing
        const s1 = process.step1_preprocessing;
        html += `<div class="process-step">
            <div class="process-step-header">
                <span class="process-step-num">1</span>
                <span class="process-step-title">Preprocessing Teks</span>
            </div>
            <div class="process-step-body">
                <div class="process-row">
                    <div class="process-label">Kunci Jawaban (asli):</div>
                    <div class="process-value process-text-original">${escapeHtml(s1.key_original)}</div>
                </div>
                <div class="process-row">
                    <div class="process-label">→ Token (setelah stemming + sinonim):</div>
                    <div class="process-value"><code>[${s1.key_tokens.map(t => `"${t}"`).join(', ')}]</code></div>
                </div>
                <div class="process-row mt-1">
                    <div class="process-label">Jawaban Siswa (asli):</div>
                    <div class="process-value process-text-original">${escapeHtml(s1.answer_original)}</div>
                </div>
                <div class="process-row">
                    <div class="process-label">→ Token (setelah stemming + sinonim):</div>
                    <div class="process-value"><code>[${s1.answer_tokens.map(t => `"${t}"`).join(', ')}]</code></div>
                </div>
            </div>
        </div>`;

        // Step 2: Vocabulary
        const vocab = process.step2_vocabulary;
        html += `<div class="process-step">
            <div class="process-step-header">
                <span class="process-step-num">2</span>
                <span class="process-step-title">Vocabulary (${vocab.length} term)</span>
            </div>
            <div class="process-step-body">
                <div class="process-vocab">${vocab.map(v => `<span class="process-vocab-item">${v}</span>`).join('')}</div>
            </div>
        </div>`;

        // Step 3: TF-IDF Table
        const table = process.step3_tfidf_table;
        html += `<div class="process-step">
            <div class="process-step-header">
                <span class="process-step-num">3</span>
                <span class="process-step-title">Matriks TF-IDF</span>
            </div>
            <div class="process-step-body">
                <div class="process-table-wrap">
                    <table class="process-table">
                        <thead>
                            <tr>
                                <th>Term</th>
                                <th colspan="3" class="process-th-group process-th-key">Kunci Jawaban</th>
                                <th colspan="3" class="process-th-group process-th-ans">Jawaban Siswa</th>
                                <th>A×B</th>
                            </tr>
                            <tr class="process-sub-header">
                                <th></th>
                                <th>TF</th><th>IDF</th><th>TF-IDF*</th>
                                <th>TF</th><th>IDF</th><th>TF-IDF*</th>
                                <th></th>
                            </tr>
                        </thead>
                        <tbody>
                            ${table.map(row => `<tr class="${row.product > 0 ? 'process-row-active' : ''}">
                                <td class="process-term">${row.term}</td>
                                <td>${row.key_tf.toFixed(3)}</td>
                                <td>${row.key_idf.toFixed(3)}</td>
                                <td class="process-val-key">${row.key_tfidf_norm.toFixed(4)}</td>
                                <td>${row.ans_tf.toFixed(3)}</td>
                                <td>${row.ans_idf.toFixed(3)}</td>
                                <td class="process-val-ans">${row.ans_tfidf_norm.toFixed(4)}</td>
                                <td class="process-val-product">${row.product.toFixed(4)}</td>
                            </tr>`).join('')}
                        </tbody>
                    </table>
                </div>
                <div class="process-note">* TF-IDF setelah normalisasi L2</div>
            </div>
        </div>`;

        // Step 4: Hybrid Scoring Calculation
        const s5 = process.step5_hybrid_scoring;
        const s6 = process.step6_scoring;
        
        if (s5.is_hybrid) {
            html += `<div class="process-step">
                <div class="process-step-header">
                    <span class="process-step-num">4</span>
                    <span class="process-step-title">Perhitungan Hybrid Scoring (SBERT + Keyword)</span>
                </div>
                <div class="process-step-body">
                    <div class="process-formula-block">
                        <div class="process-formula-title">Rumus Hybrid:</div>
                        <div class="process-formula">Nilai = (W1 × SBERT) + (W2 × Keyword)</div>
                    </div>
                    <div class="process-calc-grid">
                        <div class="process-calc-item">
                            <div class="process-calc-label">Skor SBERT (Semantik)</div>
                            <div class="process-calc-value" style="color:var(--primary)">${s5.semantic_score.toFixed(4)}</div>
                            <div style="font-size:0.75rem; color:var(--text-light); margin-top:0.25rem;">Bobot: ${s5.weight_sbert * 100}%</div>
                        </div>
                        <div class="process-calc-item">
                            <div class="process-calc-label">Skor Kata Kunci</div>
                            <div class="process-calc-value" style="color:var(--primary)">${s5.keyword_score.toFixed(4)}</div>
                            <div style="font-size:0.75rem; color:var(--text-light); margin-top:0.25rem;">Bobot: ${s5.weight_keyword * 100}%</div>
                        </div>
                        <div class="process-calc-item" style="grid-column: span 2;">
                            <div class="process-calc-label">Nilai Dasar Gabungan</div>
                            <div class="process-calc-value">${s5.cosine_score.toFixed(6)}</div>
                        </div>
                    </div>
                    <div class="process-formula-block process-result-formula">
                        <div class="process-formula">${escapeHtml(s5.formula)}</div>
                    </div>
                </div>
            </div>`;
        } else {
            html += `<div class="process-step">
                <div class="process-step-header">
                    <span class="process-step-num">4</span>
                    <span class="process-step-title">Perhitungan Cosine Similarity (Lexical Fallback)</span>
                </div>
                <div class="process-step-body">
                    <div class="alert alert-info" style="margin-bottom: 1rem;">
                        <strong>Info:</strong> Model SBERT tidak aktif. Sistem menggunakan fallback TF-IDF Lexical Matching.
                    </div>
                    <div class="process-calc-grid">
                        <div class="process-calc-item">
                            <div class="process-calc-label">Skor Cosine (Lexical)</div>
                            <div class="process-calc-value">${s5.lexical_score_fallback.toFixed(6)}</div>
                        </div>
                    </div>
                    <div class="process-formula-block process-result-formula">
                        <div class="process-formula">${escapeHtml(s5.formula)}</div>
                    </div>
                </div>
            </div>`;
        }

        // Step 4.5: Directional Semantic Analysis (Contradiction/Inversion)
        const s5b = process.step5b_semantic_analysis;
        if (s5b) {
            const isContra = s5b.verdict === 'CONTRADICTION';
            const isEntail = s5b.verdict === 'ENTAILMENT';
            const isNeutral = s5b.verdict === 'NEUTRAL';

            let stepNumStyle, alertType, titleIcon, titleText;

            if (isContra) {
                stepNumStyle = 'background:var(--danger)';
                alertType = 'error';
                titleIcon = '⚠️';
                titleText = 'Kontradiksi Makna / Inversi Terdeteksi';
            } else if (isEntail) {
                stepNumStyle = 'background:var(--success)';
                alertType = 'success';
                titleIcon = '✅';
                titleText = 'Parafrase Valid Terdeteksi';
            } else {
                stepNumStyle = 'background:var(--primary)';
                alertType = 'info';
                titleIcon = '🔍';
                titleText = 'Tidak Ditemukan Kontradiksi';
            }

            html += `<div class="process-step">
                <div class="process-step-header">
                    <span class="process-step-num" style="${stepNumStyle}">!</span>
                    <span class="process-step-title">Analisis Arah Proses & Kontradiksi</span>
                </div>
                <div class="process-step-body">
                    <div class="alert alert-${alertType}" style="margin-bottom: 1rem; align-items: flex-start; flex-direction: column; gap: 0.25rem;">
                        <strong style="font-size: 1.05rem; display: flex; align-items: center; gap: 0.5rem; width: 100%;">
                            ${titleIcon} ${titleText}
                        </strong>
                        <div style="font-size: 0.95rem; font-weight: 500; opacity: 0.9; margin-top: 0.25rem; width: 100%; text-align: left;">${escapeHtml(s5b.formula)}</div>
                    </div>
                    ${isNeutral ? `
                    <div class="process-calc-grid">
                        <div class="process-calc-item" style="grid-column: span 2; border-left: 4px solid var(--primary);">
                            <div class="process-calc-label">Hasil Analisis 7 Lapisan Deteksi</div>
                            <div class="process-calc-value" style="font-size:0.9rem; font-weight:normal; margin-top:0.5rem; line-height:1.6">
                                Sistem telah memeriksa 7 lapisan deteksi kontradiksi:<br>
                                ✓ Lapisan 1 — Inversi Peran (Subject-Object Swap)<br>
                                ✓ Lapisan 2 — Negasi (Multi-word & Implisit)<br>
                                ✓ Lapisan 3 — Pembalikan Arah (Direction Reversal)<br>
                                ✓ Lapisan 4 — Substitusi Antonim<br>
                                ✓ Lapisan 5 — Inversi Kausal / Temporal<br>
                                ✓ Lapisan 6 — Kontradiksi Kuantifier / Modal<br>
                                ✓ Lapisan 7 — SBERT Deep Semantic<br>
                                <br>
                                <strong>Tidak ditemukan kontradiksi semantik.</strong> Skor tidak diubah.
                            </div>
                        </div>
                    </div>
                    ` : ''}
                    ${!isNeutral && s5b.details && s5b.details.length > 0 ? `
                    <div class="process-calc-grid">
                        ${s5b.details.map(d => `
                            <div class="process-calc-item" style="grid-column: span 2; border-left: 4px solid ${isContra ? 'var(--danger)' : 'var(--success)'};">
                                <div class="process-calc-label">${escapeHtml(d.type)}</div>
                                <div class="process-calc-value" style="font-size:0.9rem; font-weight:normal; margin-top:0.5rem; line-height:1.4">${escapeHtml(d.description)}</div>
                            </div>
                        `).join('')}
                    </div>
                    ` : ''}
                </div>
            </div>`;
        }

        // Step 5: Final Scoring
        html += `<div class="process-step process-step-final">
            <div class="process-step-header">
                <span class="process-step-num">5</span>
                <span class="process-step-title">Konversi ke Nilai Akhir</span>
            </div>
            <div class="process-step-body">
                <div class="process-formula-block">
                    <div class="process-formula-title">Kurva Nilai Akhir:</div>
                    <div class="process-formula">Nilai = (Nilai Dasar)^1.0 × Poin Maks</div>
                </div>
                <div class="process-formula-block process-result-formula">
                    <div class="process-formula">${escapeHtml(s6.formula)}</div>
                </div>
                <div class="process-final-score">
                    <span class="process-final-label">Nilai Akhir:</span>
                    <span class="process-final-value">${s6.final_point} / ${s6.max_point}</span>
                    <span class="process-final-pct">(${s6.percentage}%)</span>
                </div>
            </div>
        </div>`;

        html += '</div>';
        return html;
    }

    // ============================================================
    // UTILITIES
    // ============================================================
    function updateDatetime() {
        const el = document.getElementById('datetimeDisplay');
        if (el) {
            const now = new Date();
            const date = now.toLocaleDateString('id-ID', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
            const time = now.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' });
            el.innerHTML = `${date}<br>${time} WIB`;
        }
    }

    async function checkEngine() {
        const el = document.getElementById('engineStatus');
        try {
            const res = await API.engineStatus();
            if (el) {
                el.innerHTML = `<span class="status-indicator online"></span><span>Engine Aktif</span>`;
            }
        } catch {
            if (el) {
                el.innerHTML = `<span class="status-indicator offline"></span><span>Offline</span>`;
            }
        }
    }

    function getScoreColor(pct) {
        if (pct >= 85) return '#10b981';
        if (pct >= 75) return '#4f46e5';
        if (pct >= 60) return '#06b6d4';
        if (pct >= 40) return '#f59e0b';
        return '#ef4444';
    }

    function showAlert(containerId, type, msg) {
        const el = document.getElementById(containerId);
        if (!el) return;
        el.innerHTML = `<div class="alert alert-${type === 'error' ? 'error' : type === 'success' ? 'success' : 'info'}">${msg}</div>`;
        el.classList.remove('hidden');
        setTimeout(() => el.classList.add('hidden'), 8000);
    }

    function escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    // Public API
    return { init, navigate, openExam };
})();

// Boot
document.addEventListener('DOMContentLoaded', App.init);
