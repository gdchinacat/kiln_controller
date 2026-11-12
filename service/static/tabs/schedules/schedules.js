'use strict';

function durationToHours(durationStr) {
  if (!durationStr) return 0;
  const parts = durationStr.split(':').map(Number);
  if (parts.some(isNaN)) return 0;
  if (parts.length === 3) return parts[0] + parts[1] / 60 + parts[2] / 3600;
  if (parts.length === 2) return parts[0] + parts[1] / 60;
  return 0;
}

function hoursToDuration(hours) {
  if (!hours || isNaN(hours) || hours <= 0) return '';
  const totalMinutes = Math.round(hours * 60);
  const h = Math.floor(totalMinutes / 60);
  const m = totalMinutes % 60;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
}

function computeTemperatureProfilePoints(phases) {
  if (!phases || phases.length === 0) {
    return [{ x: 0, temp: 20 }, { x: 1, temp: 20 }];
  }
  let points = [{ x: 0, temp: 20 }];
  let currentTemp = 20;
  let totalHours = 0;

  phases.forEach((p) => {
    const targetTemp = p.temperature !== null && p.temperature !== undefined ? p.temperature : currentTemp;
    let durationHours = 0;
    if (p.duration) {
      durationHours = durationToHours(p.duration);
    } else if (p.phase_type === 'ramp' && p.rate && p.rate > 0) {
      const tempDiff = Math.abs(targetTemp - currentTemp);
      durationHours = tempDiff / p.rate;
    }
    totalHours += durationHours;
    points.push({ x: totalHours, temp: targetTemp });
    currentTemp = targetTemp;
  });
  return points;
}

async function refreshChart(canvas, schedulePhases) {
  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  const dataPoints = computeTemperatureProfilePoints(schedulePhases);

  const datasets = [{
    label: 'Temperature (°C)',
    data: dataPoints.map(p => ({ x: p.x, y: p.temp })),
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
    data: { datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          type: 'linear',
          title: { display: true, text: 'Time (Hours)', color: '#94a3b8' },
          grid: { color: '#1e293b' },
          ticks: { color: '#64748b', callback: (val) => hoursToDuration(val) }
        },
        y: {
          title: { display: true, text: 'Temperature (°C)', color: '#94a3b8' },
          grid: { color: '#1e293b' },
          ticks: { color: '#64748b' },
          beginAtZero: true
        }
      },
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: (ctx) => ` Temp: ${ctx.parsed.y}°C (${hoursToDuration(ctx.parsed.x)})` } }
      }
    }
  });
}

function ScheduleModal() {
  const model = () => ({
    id: '',
    version: null,
    name: '',
    user_id: Alpine.store('auth').user?.id || ''});  // default to current user

  return {
    ...createEntityModal({
      entityType: 'Schedule',
      endpoint: '/schedule',
      entityStore: Alpine.store('schedules')}),
    async created(schedule) { this.$data.select(schedule)},
    model: model,
    form: model()
  };
}

function PhaseModal() {
  return {
    show: false,
    name: '',
    activeRampMode: 'rate',
    form: {
      id: '',
      version: null,
      name: '',
      ordinal: 10,
      phase_type: 'ramp',
      temperature: '',
      rate: '',
      duration: ''
    },

    open(phase = null, insertBefore = null) {
      this.phase = phase;
      this.insertBefore = insertBefore;
      this.form = phase? {
        id: phase.id,
        version: phase.version,
        name: phase.name,
        ordinal: phase.ordinal,
        phase_type: phase.phase_type,
        temperature: phase.temperature ?? '',
        rate: phase.rate ?? '',
        duration: phase.duration || ''
      } : {
        id: '',
        version: null,
        name: '',
        ordinal: null,
        phase_type: 'ramp',
        temperature: '',
        rate: '',
        duration: ''
      };

      this.setActiveRampMode((phase && !phase.rate && phase.duration) ? 'duration' : 'rate');
      this.onPhaseTypeChange();
      this.show = true;
    },

    close() {
      this.show = false;
      this.phase = null;
      this.insertBefore = null;
    },

    async assignOrdinal() {
      let ordinal;
      const phases = this.$data.schedulePhases;

      if (this.insertBefore) {
        const targetIdx = phases.findIndex(p => p.id === this.insertBefore.id);
        const prevPhase = targetIdx > 0 ? phases[targetIdx - 1] : null;

        if (prevPhase) {
          ordinal = Math.floor((prevPhase.ordinal + this.insertBefore.ordinal) / 2);
        } else {
          ordinal = Math.floor(this.insertBefore.ordinal / 2);
        }
        if (ordinal <= 0 || this.$data.schedulePhases.some(p => p.ordinal === ordinal)) {
          const subsequentPhases = [...this.$data.schedulePhases]
            .filter(p => p.ordinal > ordinal)
            .toReversed();

          let nextMinGapOrdinal = ordinal + ((subsequentPhases.length + 1) * 10);
          for (const phaseToUpdate of subsequentPhases) {
            await Alpine.store('network').apiRequest(
              `/schedule/${this.selected.id}/phase/${phaseToUpdate.id}`,
              'PUT',
              { ...phaseToUpdate, ordinal: nextMinGapOrdinal }
            );
            nextMinGapOrdinal -= 10;
          }
          ordinal = nextMinGapOrdinal;
        }
      } else {
        ordinal = (phases[phases.length - 1]?.ordinal || 0) + 10;
      }

      this.form.ordinal = ordinal;
    },

    async submit() {
      if (this.form.phase_type === 'ramp' && !this.form.rate && !this.form.duration) {
        Alpine.store('toast').showToast("Please enter either a Rate or Duration for Ramp phases.", "error");
        return;
      }

      if (!this.form.id) {
        await this.assignOrdinal();
      }

      const p = this.form;
      const payload = {
        name: p.name,
        version: p.version,
        ordinal: parseInt(this.form.ordinal),
        phase_type: p.phase_type,
        schedule_id: parseInt(this.selected.id),
        temperature: p.temperature !== "" ? parseInt(p.temperature) : null,
        rate: (p.phase_type === 'constant') ? null : ((this.activeRampMode=='rate' && p.rate !== "") ? parseInt(p.rate) : null),
        duration: (this.activeRampMode === 'duration') ? (p.duration || null) : null,
      };

      try {
        if (p.id) {
          await Alpine.store('network').apiRequest(`/schedule/${this.selected.id}/phase/${p.id}`, 'PUT', payload);
          Alpine.store('toast').showToast("Phase updated!", "success");
        } else {
          await Alpine.store('network').apiRequest(`/schedule/${this.selected.id}/phase`, 'POST', payload);
          Alpine.store('toast').showToast("Phase added!", "success");
        }
        this.close();
      } catch (error) {
          Alpine.store('toast').showToast(`Phase ${p.id ? 'edit' : 'create'} failed: ${error.message}`, "error");
      } finally {
        this.$data.reloadSelectedSchedulePhases();
      }
    },

    delete(scheduleId, phase) {
      const phStr = phase.name ? `"${phase.name}"` : `Phase #${phase.id}`;
      this.$data.confirmModal.confirm(`Delete phase ${phStr} from the schedule?`, async () => {
        try {
          await Alpine.store('network').apiRequest(`/schedule/${scheduleId}/phase/${phase.id}`, 'DELETE');
          Alpine.store('toast').showToast("Phase deleted", "warning");
          return true;
        } catch (error) {
          Alpine.store('toast').showToast(`Phase delete failed: ${error.message}`, "error");
          return false;
        } finally {
          this.$data.reloadSelectedSchedulePhases();
        }
      });
    },

    setActiveRampMode(mode) {
      if (this.form.phase_type !== 'ramp') return;
      this.activeRampMode = mode;
    },

    onPhaseTypeChange() {
      if (this.form.phase_type === 'constant') {
        let { previous, next } = this.$data.surroundingPhases(this.phase || this.insertBefore);
        if (this.insertBefore) {
            next = this.insertBefore;
        }

        if (   (!previous || previous.phase_type !== 'ramp')
            || (next && next.phase_type === 'constant')) {
          Alpine.store('toast').showToast("Constant phases must immediately follow a Ramp phase.", "error");
          this.form.phase_type = 'ramp';
          return;
        }

        this.form.temperature = previous.temperature;
        this.form.rate = '';
        this.activeRampMode = 'duration';
      } else {
        this.recalculateRampValues();
      }
    },

    recalculateRampValues() {
      if (this.form.phase_type !== 'ramp') return;
      const targetTemp = parseFloat(this.form.temperature);
      const currentOrdinal = parseInt(this.form.ordinal);
      const startTemp = this.$data.getPrecedingTemperature(currentOrdinal);

      if (isNaN(targetTemp)) return;
      const tempDiff = Math.abs(targetTemp - startTemp);

      if (this.activeRampMode === 'rate') {
        const rate = parseFloat(this.form.rate);
        if (!isNaN(rate) && rate > 0) {
          const hours = tempDiff / rate;
          this.form.duration = hoursToDuration(hours);
        }
      } else if (this.activeRampMode === 'duration') {
        const hours = durationToHours(this.form.duration);
        if (hours > 0) {
          this.form.rate = Math.round(tempDiff / hours);
        }
      }
    },
  }
}

function SchedulesTab() {
  return {
    ...BaseTab(),
    ...Selectable('schedules'),
    name: "schedules",
    modal: ScheduleModal(),
    phaseModal: PhaseModal(),
    schedulePhases: [],

    init() {
      this.watchSelection();
      Alpine.effect(() => this.reloadSelectedSchedulePhases());
    },

    async reloadSelectedSchedulePhases() {
      if (this.selected) {
        this.schedulePhases = await Alpine.store('network').apiRequest(`/schedule/${this.selected.id}/phase`);
      } else {
        this.schedulePhases = [];
      }
    },

    get selectedOwnerName() {
      if (!this.selected) return '--';
      const u = Alpine.store('users').items?.find(x => x.id === this.selected.user_id);
      return u ? u.name : `User #${this.selected.user_id}`;
    },

    getDisplayRateForDurationPhase(p) {
      if (p.phase_type === 'constant') return '';
      if (p.rate !== null && p.rate !== undefined && p.rate > 0) return `${p.rate}°/h`;

      if (p.duration) {
        const startTemp = this.getPrecedingTemperature(p.ordinal);
        const targetTemp = p.temperature !== null && p.temperature !== undefined ? p.temperature : startTemp;
        const tempDiff = Math.abs(targetTemp - startTemp);
        const hours = durationToHours(p.duration);
        if (hours != 0) {
          return `~${Math.round(tempDiff / hours)}°/h`;
        } else {
          return "ASAP";
        }
      }
      return '--';
    },

    getDisplayDurationForRatePhase(p) {
      if (p.duration) return p.duration;
      if (p.phase_type === 'ramp' && p.rate && p.rate > 0) {
        const startTemp = this.getPrecedingTemperature(p.ordinal);
        const targetTemp = p.temperature !== null && p.temperature !== undefined ? p.temperature : startTemp;
        const tempDiff = Math.abs(targetTemp - startTemp);
        const hours = tempDiff / p.rate;
        return hoursToDuration(hours);
      }
      return '--';
    },

    surroundingPhases(phase) {
      const phases = this.schedulePhases;
      if (phase && phases) {
        let phaseIdx = phases.findIndex(p => p.id === phase.id);
        if (phaseIdx === -1) {
          throw new Error('phase is not in schedulePhases');
        }
        return {
          previous: phaseIdx >= 1 ? phases[phaseIdx - 1] : null,
          next: phaseIdx < phases.length - 1 ? phases[phaseIdx + 1] : null,
        };
      }
      return { previous: phase === null && phases ? phases[phases.length - 1] : null, next: null};
    },

    getPrecedingTemperature(editingOrdinal = null) {
      // todo use surroundingPhases
      let targetList = [...this.$data.schedulePhases];
      if (editingOrdinal !== null) {
        targetList = targetList.filter(p => p.ordinal < editingOrdinal);
      }
      if (targetList.length === 0) return DEFAULT_ROOM_TEMP;
      const lastPhase = targetList[targetList.length - 1];
      return (lastPhase.temperature !== null && lastPhase.temperature !== undefined) ? lastPhase.temperature : DEFAULT_ROOM_TEMP;
    },

    isPhaseDeletable(phase) {
      let { previous, next } = this.surroundingPhases(phase);

      if (phase.phase_type === 'ramp' && next?.phase_type === 'constant') {
        // constant phases must be preceeded by ramp
        return false;
      }
      return true;
    },

  }
}

Alpine.store('tabs')['schedules'] = SchedulesTab();
export const exports = { refreshChart: refreshChart }