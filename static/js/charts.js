/* ════════════════════════════════════════════
   SocialGuard — Chart Initializer
   Uses Chart.js 4.x
════════════════════════════════════════════ */

const COLORS = {
  accent:  '#6366f1',
  success: '#10b981',
  danger:  '#ef4444',
  warning: '#f59e0b',
  muted:   '#55556a',
  grid:    'rgba(255,255,255,0.05)',
  text:    '#9898b0',
};

Chart.defaults.color = COLORS.text;
Chart.defaults.borderColor = COLORS.grid;
Chart.defaults.font.family = "'DM Sans', sans-serif";

function initCharts(trendData, breakdown) {
  initTrendChart(trendData);
  initDonutChart(breakdown);
}

/* ── Engagement Trend Line Chart ── */
function initTrendChart(trendData) {
  const ctx = document.getElementById('trendChart');
  if (!ctx) return;

  const labels = trendData.length > 0
    ? trendData.map(d => {
        const date = new Date(d.date);
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      })
    : ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

  const values = trendData.length > 0
    ? trendData.map(d => parseFloat(d.avg).toFixed(2))
    : [4.2, 6.8, 5.1, 9.3, 7.4, 11.2, 8.6];  // demo data

  new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: 'Avg Engagement (%)',
        data: values,
        borderColor: COLORS.accent,
        backgroundColor: (ctx) => {
          const gradient = ctx.chart.ctx.createLinearGradient(0, 0, 0, 200);
          gradient.addColorStop(0, 'rgba(99,102,241,0.25)');
          gradient.addColorStop(1, 'rgba(99,102,241,0)');
          return gradient;
        },
        fill: true,
        tension: 0.4,
        pointBackgroundColor: COLORS.accent,
        pointBorderColor: '#14141c',
        pointBorderWidth: 2,
        pointRadius: 4,
        pointHoverRadius: 6,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#1a1a26',
          borderColor: 'rgba(99,102,241,0.3)',
          borderWidth: 1,
          titleColor: '#e8e6f0',
          bodyColor: '#9898b0',
          callbacks: {
            label: ctx => ` ${ctx.raw}% engagement`
          }
        }
      },
      scales: {
        x: {
          grid: { color: COLORS.grid },
          ticks: { font: { size: 11 } }
        },
        y: {
          grid: { color: COLORS.grid },
          ticks: {
            font: { size: 11 },
            callback: val => val + '%'
          }
        }
      }
    }
  });
}

/* ── Content Authenticity Donut Chart ── */
function initDonutChart(breakdown) {
  const ctx = document.getElementById('donutChart');
  if (!ctx) return;

  const imageOnly   = parseInt(breakdown?.image_only   || 0);
  const textOnly    = parseInt(breakdown?.text_only    || 0);
  const bothFlagged = parseInt(breakdown?.both_flagged || 0);
  const clean       = parseInt(breakdown?.clean        || 0);

  const total = imageOnly + textOnly + bothFlagged + clean;

  // Demo data if no posts
  const data = total > 0
    ? [clean, imageOnly, textOnly, bothFlagged]
    : [65, 15, 12, 8];

  new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Authentic', 'Image Tampered', 'Text Flagged', 'Both Flagged'],
      datasets: [{
        data,
        backgroundColor: [
          COLORS.success,
          COLORS.danger,
          COLORS.warning,
          '#8b5cf6',
        ],
        borderColor: '#14141c',
        borderWidth: 3,
        hoverOffset: 6,
      }]
    },
    options: {
      responsive: true,
      cutout: '68%',
      plugins: {
        legend: {
          position: 'bottom',
          labels: {
            padding: 12,
            font: { size: 11 },
            usePointStyle: true,
            pointStyleWidth: 8,
          }
        },
        tooltip: {
          backgroundColor: '#1a1a26',
          borderColor: 'rgba(255,255,255,0.08)',
          borderWidth: 1,
          titleColor: '#e8e6f0',
          bodyColor: '#9898b0',
          callbacks: {
            label: ctx => {
              const sum = ctx.dataset.data.reduce((a, b) => a + b, 0);
              const pct = sum > 0 ? ((ctx.raw / sum) * 100).toFixed(1) : 0;
              return ` ${ctx.label}: ${ctx.raw} (${pct}%)`;
            }
          }
        }
      }
    }
  });
}
