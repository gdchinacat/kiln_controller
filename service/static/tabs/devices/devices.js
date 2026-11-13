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

function zip(...arrays) {
  const minLength = Math.min(...arrays.map(arr => arr.length));
  return Array.from({ length: minLength }, (_, i) => 
    arrays.map(arr => arr[i])
  );
}

function DevicesTab() {
  return {
    ...BaseTab(),
    ...Selectable('devices'),
    name: "devices",
    modal: DeviceModal(),
    selectedMetric: 'temperature',

    async queryMetrics() {
      if (this.selected) {
        const url = `/device/${this.selected.id}/metrics`;
        const result = await Alpine.store('network').apiRequest(
            url, 'POST', {metrics: [this.selectedMetric]});
        const times = result.times;
        const values = result.series[0].values;
        const dataPoints = zip(times, values);
        return dataPoints.map(([time, value]) => ({ x: new Date(time), y: value }));
      }
      return [];
    },

    async chartMetric(canvas) {
      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      const dataPoints = await this.queryMetrics();

      const datasets = [{
        label: 'Temperature (°C)',
        yAxisID: this.selectedMetric, // todo? map names?
        data: dataPoints,
        tooltip: { callbacks: {label: context => `${context.parsed.y.toFixed(1)} (°C)`}},

        // todo factor this display stuff out
        borderColor: '#f97316',
        backgroundColor: 'rgba(249, 115, 22, 0.15)',
        borderWidth: 2,
        fill: true,
        tension: 0.0,
        pointBackgroundColor: '#ea580c',
        pointRadius: 1,
        pointHoverRadius: 4
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
          animation: false,
          maintainAspectRatio: false,
          scales: {
            x: {
              type: 'time',
              title: { display: true, text: 'time', color: '#94a3b8' },
              grid: { color: '#1e293b' },
              ticks: {
                color: '#64748b',
                autoSkip: true,
                maxTicksLimit: 8,
              },
            },

            // todo - add/remove on demand
            uptime: {
              type: 'linear',
              position: 'right',
              title: { display: true, text: 'Uptime (s)' },
              beginAtZero: false,
            },
            temperature: {
              type: 'linear',
              position: 'left',
              title: { display: true, text: 'Temperature (°C)' },
              beginAtZero: false,
            },
          },
          plugins: { legend: { display: false } },
        }
      });
    },

  };
}

Alpine.store('tabs')['devices'] = DevicesTab();