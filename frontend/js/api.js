/**
 * EssayGrader — API Client Module v2.0
 * Handles all communication with the FastAPI backend.
 */
const API = (() => {
    const BASE = 'http://localhost:8000';

    async function request(method, path, body = null) {
        const opts = {
            method,
            headers: { 'Content-Type': 'application/json' },
        };
        if (body) opts.body = JSON.stringify(body);
        const res = await fetch(`${BASE}${path}`, opts);
        if (!res.ok) {
            const err = await res.json().catch(() => ({ detail: res.statusText }));
            // FastAPI validation errors return detail as an array of objects
            let message = 'Request failed';
            if (typeof err.detail === 'string') {
                message = err.detail;
            } else if (Array.isArray(err.detail)) {
                message = err.detail.map(e => e.msg || JSON.stringify(e)).join('; ');
            } else if (err.detail) {
                message = JSON.stringify(err.detail);
            }
            throw new Error(message);
        }
        return res.json();
    }

    return {
        // Health
        health: () => request('GET', '/'),
        engineStatus: () => request('GET', '/api/engine/status'),

        // Stats (dashboard)
        getStats: () => request('GET', '/api/stats'),

        // Exams
        listExams: () => request('GET', '/api/exams'),
        getExam: (id) => request('GET', `/api/exams/${id}`),
        createExam: (data) => request('POST', '/api/exams', data),
        deleteExam: (id) => request('DELETE', `/api/exams/${id}`),

        // Questions
        addQuestion: (examId, data) => request('POST', `/api/exams/${examId}/questions`, data),

        // Answers
        submitAnswer: (data) => request('POST', '/api/answers/text', data),
        submitBulk: (data) => request('POST', '/api/answers/bulk', data),
        submitBatch: (data) => request('POST', '/api/answers/batch', data),
        getAnswers: (qId) => request('GET', `/api/answers/${qId}`),

        // Evaluation
        evaluate: (examId) => request('POST', `/api/evaluate/${examId}`),
        preview: (data) => request('POST', '/api/evaluate/preview', data),

        // Results
        getResults: (examId) => request('GET', `/api/results/${examId}`),
        getRankings: (examId) => request('GET', `/api/results/${examId}/rankings`),

        // Image upload (multipart)
        uploadImage: async (questionId, studentName, file) => {
            const form = new FormData();
            form.append('question_id', questionId);
            form.append('student_name', studentName);
            form.append('file', file);
            const res = await fetch(`${BASE}/api/answers/image`, { method: 'POST', body: form });
            if (!res.ok) {
                const err = await res.json().catch(() => ({ detail: 'Upload gambar gagal' }));
                throw new Error(err.detail || 'Upload gambar gagal');
            }
            return res.json();
        },

        // PDF upload (multipart)
        uploadPDF: async (questionId, studentName, file) => {
            const form = new FormData();
            form.append('question_id', questionId);
            form.append('student_name', studentName);
            form.append('file', file);
            const res = await fetch(`${BASE}/api/answers/pdf`, { method: 'POST', body: form });
            if (!res.ok) {
                const err = await res.json().catch(() => ({ detail: 'Upload PDF gagal' }));
                throw new Error(err.detail || 'Upload PDF gagal');
            }
            return res.json();
        },
    };
})();
