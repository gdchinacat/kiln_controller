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

const formatDuration = (totalSeconds) => {
  const days = Math.floor(totalSeconds / 86400);
  const hours = Math.floor((totalSeconds % 86400) / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h ${minutes}m`;
  if (minutes > 0) return `${minutes}m ${seconds}s`;
  return `${seconds}s`;
};

function formatBytes(bytes, decimals = 2) {
  if (!+bytes || bytes === 0) return '0 B';

  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB'];

  const i = Math.floor(Math.log(Math.abs(bytes)) / Math.log(k));

  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
}


function ChartPropertiesModal() {
    return {
      show: false,
      form: {
        start: '',
        end: '',
        step: '5s',
        refresh: '0',
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

function Series(chart, device, metric, info, chartProperties) {
  const name = info.name ?? metric;
  const scale = chart.scales[info.units];
  const series = {
    device,
    metric,
    info,
    async queryMetrics() {
      const result = await Alpine.store('network').apiRequest(
        `/device/${device.id}/metrics/${metric}?${chartProperties.queryParams}`, 'GET');
      this.dataset.data = result.values.map(([time, value]) => ({ x: new Date(time * 1000), y: value }));
    },

    name,

    dataset: {
        data: null,
        label: name,
        scale,
        yAxisID: info.units,
        borderColor: info.color,
        backgroundColor: 'rgba(249, 115, 22, 0.15)',
        borderWidth: 2,
        fill: false,
        tension: 0.0,
        pointBackgroundColor: info.color,
        pointRadius: 1,
        pointHitRadius: 10,
        pointHoverRadius: 5,
    },
  };
  return series;
}

function DevicesTab() {
  return {
    ...BaseTab(),
    ...Selectable('devices'),
    name: "devices",
    modal: DeviceModal(),
    chartPropertiesModal: ChartPropertiesModal(),

    // todo factor out chart
    chart: null,
    refreshIntervalId: null,
    metrics: null,  // the available metrics for the selected device
    selectedMetrics: [],
    series: [ ],  // the series for the selected metrics

    init() {
      this.watchSelection();
      this.createChart();
    },

    async createChart() {
      const canvas = document.getElementById('deviceMetricChart');
      const ctx = canvas?.getContext('2d');
      if (!ctx) return;

      this.chart = new Chart(ctx, {
        type: 'line',

        data: {
            datasets: [],
        },

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

            temperature: {
              type: 'linear',
              position: 'left',
              title: { display: true, text: 'temperature (°C)'},
              beginAtZero: true,
              display: false,
              ticks: { callback: (value) => `${value}°C ` },
            },

            seconds: {
              type: 'linear',
              position: 'left',
              title: { display: true, text: 'time (s)' },
              beginAtZero: true,
              display: false,
              ticks: { callback: (value) => formatDuration(value) }
            },

            milliseconds: {
              type: 'linear',
              position: 'left',
              title: { display: true, text: 'time (s)' },
              beginAtZero: true,
              display: false,
              ticks: { callback: (value) => formatDuration(value/1000) }
            },

            count: {
              type: 'linear',
              position: 'left',
              title: { display: true, text: 'count' },
              beginAtZero: true,
              display: false,
              ticks: { callback: (value) => value },
            },

            percent: {
              type: 'linear',
              position: 'left',
              title: { display: true, text: 'percent' },
              beginAtZero: true,
              display: false,
              ticks: { callback: (value) => `${value}%` },
            },

            bytes: {
              type: 'linear',
              position: 'right',
              title: { display: true, text: 'bytes' },
              beginAtZero: true,
              display: false,
              ticks: { callback: (value) => formatBytes(value) },
            },

          },
          plugins: { legend: { display: true,
                               position: "bottom", },
                     tooltip: {
                        callbacks: {
                            label: (context) => context.dataset.scale.options.ticks.callback(context.parsed.y)
                        }
                    },
                },
        },
      });

      Alpine.effect(() => { this.fetchMetricSummary(); });
      Alpine.effect(() => { this.createSeries(); }); // todo - this creates series when chartProperties change, probably don't want that (use this.$watch('selected', () => this.createSeries()))

      Alpine.effect(() => {
        const interval = this.chartPropertiesModal.refresh * 1000;
        if (this.refreshIntervalId !== null) {
          clearInterval(this.refreshIntervalId);
          this.refreshIntervalId = null;
        }
        if (interval > 0) {
          this.refreshIntervalId = setInterval(() => {
            this.updateChart(true);
          }, interval);
        }
      });
    },

    seriesColor(metric, info) { return info.color; },
    metricLabel(metric, info) { return info.name ?? metric; },

    async fetchMetricSummary() {
      // get the list of supported metrics for the selected device
      this.metrics = null; // prevent double queryMetrics() on selection change
      if (this.selected) {
        const palette = [
          '#f97316', // orange
          '#38bdf8', // sky blue
          '#4ade80', // green
          '#a78bfa', // violet
          '#f43f5e', // rose
          '#facc15', // yellow
          '#2dd4bf', // teal
          '#e879f9', // fuchsia
          '#60a5fa', // blue
          '#a3e635', // lime
          '#fb7185', // pink
          '#34d399', // emerald
          '#fbbf24', // amber
          '#818cf8', // indigo
          '#22d3ee', // cyan
          '#f87171', // red
        ];

        const summary = await Alpine.store('network').apiRequest(
          `/device/${this.selected.id}/metrics`, 'GET');
        Object.values(summary.metrics).forEach((info, i) => {
            info.color = palette[i % palette.length];
          });
        this.metrics = summary.metrics;
      }
    },

    async updateChart(skipAnimation=false) {
      const chart = Alpine.raw(this.chart);
      await Promise.allSettled(this.series.map(s => s.queryMetrics()));

      //todo - I believe a race condition exists here where an update can start
      //       for device 1 but before it completes another device is selected,
      //       quries, updates chart, then the original one completes and
      //       clobbers the chart with stale data (resulting in showing the
      //       user metrics for device 1 when they think they are looking at
      //       device 2 because that is what is selected). Not a priority to
      //       fix at this point, but wanted it tracked so it doesn't lead to
      //       difficult to troubleshoot bugs. No multi-tenant issues because
      //       users can only see devices they have access to. Still likely to
      //       waste troubleshooting time through confusion.

      // set axis visibility
      Object.values(chart.options.scales).forEach(s => s.display = false);
      chart.options.scales.x.display = true;
      this.series.map((series) => {
        const info = this.metrics[series.metric];
        chart.options.scales[info.units].display = true;
        series.dataset.spanGaps = this.chartPropertiesModal.step * 1000;
        //series.dataset.tooltip = { callbacks: {label: context => `${context.parsed.y.toFixed(1)}`}};
      });

      chart.update(skipAnimation ? 'none' : null);
    },

    createSeries() {
      if (this.selected && this.metrics) {
        this.series = this.selectedMetrics.map(
            m => Series(this.chart, this.selected, m, this.metrics[m], this.chartPropertiesModal)
        );
        this.chart.data.datasets = this.series.map(s => s.dataset);
      } else {
        this.series = [];
      }
      this.updateChart();
    },

    chartableMetrics() {
        return Object.entries(this.metrics ?? {}).filter(([_, info]) => info.units);
    },

  };
}

Alpine.store('tabs')['devices'] = DevicesTab();