'use strict';

function DeviceModal() {
  const model = () => ({
    id: '',
    version: null,
    name: '',
    user_id: Alpine.store('auth').user?.id || ''});  // default to current user

  return {
    ...createEntityModal({
      entityType: 'Kiln',
      endpoint: '/device',
      entityStore: Alpine.store('devices')}),
    model: model,
    form: model()
  };
}

function epochToDate(epoch) { return epoch; }

function DevicesTab() {
  return {
    ...BaseTab(),
    ...Selectable('devices'),
    name: "devices",
    modal: DeviceModal(),
    selectedMetric: 'temperature',

    async chartMetric(canvas) {
      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      const dataPoints = [{x: 0, y: 1}, {x: 1, y: 1}];

      const datasets = [{
        label: 'Temperature (°C)',
        yAxisID: 'temperature',  // todo - select correct and make sure it exists
        data: dataPoints,
        tooltip: { callbacks: {label: context => `${context.parsed.y.toFixed(1)} (°C)`}},

        // todo factor this display stuff out
        borderColor: '#f97316',
        backgroundColor: 'rgba(249, 115, 22, 0.15)',
        borderWidth: 2,
        fill: true,
        tension: 0.0,
        pointBackgroundColor: '#ea580c',
        pointRadius: 4,
        pointHoverRadius: 7
      }];

      if (canvas.chart) {
        const chart = Alpine.raw(canvas.chart);
        chart.data = { datasets };
        chart.update();
        return;
      }

      canvas.chart = new Chart(ctx, {
        type: 'line',
        data: { },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            x: {
              type: 'linear',
              title: { display: true, text: 'Time', color: '#94a3b8' },
              grid: { color: '#1e293b' },
              ticks: { color: '#64748b', callback: epochToDate },
            },

            // todo - add/remove on demand
            temperature: {
              type: 'linear',
              position: 'left',
              title: { display: true, text: 'Temperature (°C)' },
              beginAtZero: true,
            },
          },
          plugins: { legend: { display: false } },
        }
      });
    },

  };
}

Alpine.store('tabs')['devices'] = DevicesTab();