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

function parseDuration(durationStr) {
  const regex = /(\d+)(ms|s|m|h|d|w|y)/g;
  const unitToMs = {
    ms: .001,
    s: 1,
    m: 60,
    h: 60 * 60,
    d: 24 * 60 * 60,
    w: 7 * 24 * 60 * 60,
    y: 365 * 24 * 60 * 60,
  };

  let totalMs = null;
  let match;
  let matchedLength = 0;

  while ((match = regex.exec(durationStr)) !== null) {
    const value = parseInt(match[1], 10);
    const unit = match[2];

    totalMs += value * unitToMs[unit];
    matchedLength += match[0].length;
  }

  if (totalMs !== null) return totalMs;

  return durationStr
}

function ChartPropertiesModal() {
    return {
      show: false,
      form: {
        start: '',
        stop: '',
        step: '5s',
        refresh: '1',
      },

      open() {
        this.show = true;
      },

      close() {
        this.show = false;
      },

      get queryParams() {
        return new URLSearchParams(
            Object.entries({step: this.step,
                            start: this.form.start,
                            end: this.form.end}).filter((
            [k, v]) => v)).toString();
      },

      get step() {
        return this.form.step ? parseDuration(this.form.step): '';
      },

      get refresh() {
        return this.form.refresh ? parseDuration(this.form.refresh + 's'): '';
      },

    };
}

function DevicesTab() {
  return {
    ...BaseTab(),
    ...Selectable('devices'),
    name: "devices",
    modal: DeviceModal(),
    chartPropertiesModal: ChartPropertiesModal(),
    chart: null,
    refreshIntervalId: null,
    metrics: [],
    selectedMetric: 'temperature',

    init() {
      this.watchSelection();
      this.createChart();
    },

    async createChart() {
      const canvas = document.getElementById('deviceMetricChart');
      const ctx = canvas?.getContext('2d');
      if (!ctx) return;

      const datasets = [ this.createDataset() ]; // todo add datasets dynamically

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

            left: { // General purpose scale to be used and updated by dataset selection
              type: 'linear',
              position: 'left',
              title: { display: false, text: '' },
              beginAtZero: true,
            },

            right: { // General purpose scale to be used and updated by dataset selection
              type: 'linear',
              position: 'right',
              title: { display: false, text: '' },
              beginAtZero: true,
            },

          },
          plugins: { legend: { display: false } },
        }
      });

      Alpine.effect(() => { this.selected; this.fetchMetricSummary(); });
      Alpine.effect(() => { this.selected && this.selectedMetric; this.updateChart(); });
      Alpine.effect(() => {
        const interval = (this.chartPropertiesModal.refresh || 5) * 1000;
        if (this.refreshIntervalId !== null) {
          clearInterval(this.refreshIntervalId);
          this.refreshintervalid = null;
        }
        if (interval > 0) {
          this.refreshIntervalId = setInterval(() => {
            this.updateChart(true);
          }, interval);
        }
      });
    },

    async fetchMetricSummary() {
      if (this.selected) {
        const summary = await Alpine.store('network').apiRequest(
          `/device/${this.selected.id}/metrics`, 'GET');
        this.metrics = summary.metrics;
      }
    },

    createDataset() {
      return {
        data: [],
        tooltip: null,

        yAxisID: 'left',
        label: '',
        borderColor: '#f97316',
        backgroundColor: 'rgba(249, 115, 22, 0.15)',
        borderWidth: 2,
        fill: false,
        tension: 0.0,
        pointBackgroundColor: '#ea580c',
        pointRadius: 1,
        pointHoverRadius: 4,
      };
    },

    async updateChart(skipAnimation=false) {
      const chart = Alpine.raw(this.chart);

      const dataset = chart.data.datasets[0]; // todo handle multiple metrics
      const scale = chart.options.scales.left;

      function DataSet(axis) { //todo merge with CreateDataset/GET /device/.../metrics
        return {
          scale: {
            scale: null, // todo set to options.scales.[left|right]
            title: '<metric title>', // -> scale.title.text
            beginAtZero: true,       // -> scale.beginAtZero
          },
          dataset_properties: {

          },
        };
      };

      // done  1) put everything in here that needs to change
      // todo  2) figure out how to get it from server (units, type, etc)
      // todo  3) factor it out into Series that reacts to update correct item in chart.data.datasets
      // set up the axis
      scale.title.display = true;
      dataset.yAxisID = 'left',
      scale.title.text = `units for ${this.selectedMetric}`;
      scale.beginAtZero = true;

      // set up the dataset
      dataset.tooltip = { callbacks: {label: context => `${context.parsed.y.toFixed(1)} (°C)`}},
      dataset.label = `units for ${this.selectedMetric}`;
      dataset.data = await this.queryMetrics();
      dataset.spanGaps = this.chartPropertiesModal.step * 1000,
      chart.update(skipAnimation ? 'none' : null);
    },

    async queryMetrics() {
      if (this.selected) {
        const result = await Alpine.store('network').apiRequest(
          `/device/${this.selected.id}/metrics/${this.selectedMetric}?${this.chartParams}`, 'GET');
        return result.values.map(([time, value]) => ({ x: new Date(time * 1000), y: value }));
      }
      return [];
    },

    get chartParams() {
      return this.chartPropertiesModal.queryParams;
    },

  };
}

Alpine.store('tabs')['devices'] = DevicesTab();