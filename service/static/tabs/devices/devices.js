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

function DevicesTab() {
  return {
    ...BaseTab(),
    ...Selectable('devices'),
    name: "devices",
    modal: DeviceModal(),
    selectedMetric: 'temperature',
    chart: null,

    init() {
      this.watchSelection();
      this.createChart();
    },

    async createChart() {
      const canvas = document.getElementById('deviceMetricChart');
      const ctx = canvas?.getContext('2d');
      if (!ctx) return;

      const datasets = [{
        label: 'Temperature (°C)',
        yAxisID: this.selectedMetric, // todo? map names?
        data: [],
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

      this.chart = new Chart(ctx, {
        type: 'line',
        data: { datasets },
        options: {
          responsive: true,
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

      Alpine.effect(() => {this.selected && this.selectedMetric; this.updateChart();});
      setInterval(() => {
        this.updateChart(true);
      }, 5000);
    },

    async updateChart(skipAnimation=false) {
      const chart = Alpine.raw(this.chart);
      // todo replace the axis, not just the data
      chart.data.datasets[0].data = await this.queryMetrics();
      chart.update(skipAnimation ? 'none' : null);
    },

    async queryMetrics() {
      if (this.selected) {
        const result = await Alpine.store('network').apiRequest(
          `/device/${this.selected.id}/metrics/${this.selectedMetric}`, 'GET');
        return result.values.map(([time, value]) => ({ x: new Date(time * 1000), y: value }));
      }
      return [];
    },


  };
}

Alpine.store('tabs')['devices'] = DevicesTab();