/**
 * EssayGrader — Boot Terminal Animation
 */
const Terminal = (() => {
    const lines = [
        '[BOOT] EssayGrader Engine v1.0.0',
        '[BOOT] Initializing TF-IDF vectorizer...',
        '[BOOT] Loading Indonesian stemmer (Confix-Stripping)...',
        '[BOOT] Compiling C math engine (essay_engine.dll)...',
        '[MATH] cos(θ) = (A·B) / (||A|| × ||B||)',
        '[MATH] TF-IDF weighting: w(t,d) = tf(t,d) × log(N/df(t))',
        '[CORE] Cosine similarity batch processor: READY',
        '[CORE] Score normalization: percentage^0.7 mapping',
        '[DB  ] SQLite database: CONNECTED',
        '[DB  ] Tables: exam_packages, questions, master_keys, student_answers, evaluations',
        '[OCR ] Tesseract OCR service: STANDBY',
        '[SYS ] All systems operational.',
        '[SYS ] Ready for essay evaluation.',
    ];

    function run(containerId, callback) {
        const container = document.getElementById(containerId);
        if (!container) return;
        let i = 0;
        const interval = setInterval(() => {
            if (i >= lines.length) {
                clearInterval(interval);
                if (callback) setTimeout(callback, 600);
                return;
            }
            const div = document.createElement('div');
            div.className = 'line';
            div.textContent = lines[i];
            div.style.animationDelay = '0s';
            container.appendChild(div);
            container.scrollTop = container.scrollHeight;
            i++;
        }, 180);
    }

    return { run };
})();
