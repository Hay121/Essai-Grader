/**
 * EssayGrader — Chart Visualizations (Chart.js)
 * Light theme with Plus Jakarta Sans font.
 */
const Charts = (() => {
    const chartInstances = {};
    const FONT_FAMILY = "'Plus Jakarta Sans', sans-serif";

    function getScoreColor(pct) {
        if (pct >= 85) return '#10b981';
        if (pct >= 75) return '#4f46e5';
        if (pct >= 60) return '#06b6d4';
        if (pct >= 40) return '#f59e0b';
        return '#ef4444';
    }

    function getScoreColors(data) {
        return data.map(d => getScoreColor(d));
    }

    function destroyChart(id) {
        if (chartInstances[id]) { chartInstances[id].destroy(); delete chartInstances[id]; }
    }

    function renderRankingChart(canvasId, rankings) {
        destroyChart(canvasId);
        const canvas = document.getElementById(canvasId);
        if (!canvas || !rankings.length) return;

        const labels = rankings.map(r => r.student_name);
        const data = rankings.map(r => r.percentage);
        const colors = getScoreColors(data);

        chartInstances[canvasId] = new Chart(canvas, {
            type: 'bar',
            data: {
                labels,
                datasets: [{
                    label: 'Skor (%)',
                    data,
                    backgroundColor: colors.map(c => c + '30'),
                    borderColor: colors,
                    borderWidth: 1.5,
                    borderRadius: 6,
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true, maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: '#0f172a',
                        titleFont: { family: FONT_FAMILY, size: 12 },
                        bodyFont: { family: FONT_FAMILY, size: 11 },
                        cornerRadius: 8,
                        padding: 10,
                    }
                },
                scales: {
                    x: {
                        max: 100,
                        grid: { color: '#f1f5f9' },
                        ticks: { color: '#94a3b8', font: { family: FONT_FAMILY, size: 11 } }
                    },
                    y: {
                        grid: { display: false },
                        ticks: { color: '#1e293b', font: { family: FONT_FAMILY, size: 12, weight: 500 } }
                    }
                }
            }
        });
    }

    function renderDistributionChart(canvasId, results) {
        destroyChart(canvasId);
        const canvas = document.getElementById(canvasId);
        if (!canvas || !results.length) return;

        const bins = [0, 0, 0, 0, 0]; // E, D, C, B, A
        const binLabels = ['0-39 (E)', '40-59 (D)', '60-74 (C)', '75-84 (B)', '85-100 (A)'];
        const binColors = ['#ef4444', '#f59e0b', '#06b6d4', '#4f46e5', '#10b981'];

        results.forEach(r => {
            const pct = (r.final_point / r.max_point) * 100;
            if (pct >= 85) bins[4]++;
            else if (pct >= 75) bins[3]++;
            else if (pct >= 60) bins[2]++;
            else if (pct >= 40) bins[1]++;
            else bins[0]++;
        });

        chartInstances[canvasId] = new Chart(canvas, {
            type: 'doughnut',
            data: {
                labels: binLabels,
                datasets: [{
                    data: bins,
                    backgroundColor: binColors.map(c => c + '40'),
                    borderColor: binColors,
                    borderWidth: 2,
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                cutout: '55%',
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: '#64748b',
                            font: { family: FONT_FAMILY, size: 11 },
                            padding: 15,
                            usePointStyle: true,
                            pointStyleWidth: 10,
                        }
                    },
                    tooltip: {
                        backgroundColor: '#1e293b',
                        titleFont: { family: FONT_FAMILY },
                        bodyFont: { family: FONT_FAMILY },
                        cornerRadius: 8,
                    }
                }
            }
        });
    }

    return { renderRankingChart, renderDistributionChart, getScoreColor };
})();
