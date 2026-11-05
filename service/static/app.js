const DEFAULT_ROOM_TEMP = 20;

// --- Helper Functions ---
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
  const sorted = [...phases].sort((a, b) => a.ordinal - b.ordinal);
  let points = [{ x: 0, temp: 20 }];
  let currentTemp = 20;
  let totalHours = 0;

  sorted.forEach((p) => {
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

function createEntityStore(endpoint) {
  return {
    items: null,
    loading: false,

    init() {
      Alpine.effect(() => {
        if (Alpine.store('auth').user) {
          this.refresh();
        } else {
            this.items  = null;
        }
      });
    },

    async refresh() {
      this.items = await Alpine.store('network').apiRequest(endpoint);
      return this.items;
    },

    async create(payload) {
      try {
        return await Alpine.store('network').apiRequest(endpoint, 'POST', payload);
      } finally {
        await this.refresh();
      }
    },

    async save(payload) {
      try {
        return await Alpine.store('network').apiRequest(`${endpoint}/${payload.id}`, 'PUT', payload);
      } finally {
        await this.refresh();
      }
    },

    async delete(id) {
      try {
        await Alpine.store('network').apiRequest(`${endpoint}/${id}`, 'DELETE');
      } finally {
        await this.refresh();
      }
    }
  };
}

function LoginModal() {
  return {
    show: false,
    form: { username: '', password:'' },
    open() { this.show = true; },
    close() {
        this.show = false;
        this.form.password = '';
    },

    async login() {
      try {
        await Alpine.store('auth').login(this.form);
        Alpine.store('toast').showToast('Login success.', 'success');
        this.close();
      } catch (err) {
        Alpine.store('toast').showToast(`Login failed: ${err.message}`, "error");
      } finally {
        window.dispatchEvent(new CustomEvent('refresh-view'));
      }
    },

    async logout() {
      try {
        await Alpine.store('auth').logout();
        Alpine.store('toast').showToast("Logout success.", "success");
      } finally {
        window.dispatchEvent(new CustomEvent('refresh-view'));
      }
    },

  };
}

function ConfirmModal() {
  return {
    show: false,
    message: '',
    action: null,

    confirm(message, action) {
      this.message = message;
      this.action = action;
      this.show = true;
    },

    dismiss() {
      this.show = false;
    },

    confirmed() {
      if (this.action) this.action();
      this.dismiss();
    }
  }
}

function createEntityModal(config) {
  return {
    show: false,

    open(entity = null) {
      this.form = entity ? { ...this.model(), ...entity } : this.model();
      this.show = true;
    },

    close() {
      this.show = false;
      this.form = this.model();
    },

    async submit() {
      if (this.form.id != '') {
        await config.entityStore.save(this.form);
        Alpine.store('toast').showToast(`${config.entityType} updated successfully!`, "success");
      } else {
        await config.entityStore.create(this.form);
        Alpine.store('toast').showToast(`${config.entityType} created successfully!`, "success");
      }
      this.close();
    },

    async delete(entity) {
      const nameStr = entity.name ? `${entity.name}` : `#${entity.id}`;
      this.$data.confirmModal.confirm(`Are you sure you want to delete ${config.entityType.toLowerCase()} "${nameStr}"?`, async () => {
        await config.entityStore.delete(entity.id);
        Alpine.store('toast').showToast(`${config.entityType} deleted`, "warning");
      });

    }
  };
}

function UserModal() {
  const model = () => ({
    id: '',
    name: '',
    id: '',
    name: '',
    username: '',
    password: '',
    email: '',
    phone_number: '',
  });

  return {
    ...createEntityModal({
      entityType: 'User',
      endpoint: '/user',
      entityStore: Alpine.store('users')}),
    model: model,
    form: model()
  };
}

function DeviceModal() {
  const model = () => ({
    id: '',
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

function ScheduleModal() {
  const model = () => ({
    id: '',
    name: '',
    user_id: Alpine.store('auth').user?.id || ''});  // default to current user

  return {
    ...createEntityModal({
      entityType: 'Schedule',
      endpoint: '/schedule',
      entityStore: Alpine.store('schedules')}),
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
      name: '',
      ordinal: 10,
      phase_type: 'ramp',
      temperature: '',
      rate: '',
      duration: ''
    },

    open(phase = null, insertBefore = null) {
      if (!this.$data.selectedSchedule) {
        Alpine.store('toast').showToast("Select a schedule first", "warning");
        return;
      }

      let calculatedOrdinal;

      // todo - extract this ordinal calculation
      // todo - handle cases where the gap is full and ordinals need to be shifted.
      if (phase) {
        calculatedOrdinal = phase.ordinal;
      } else if (insertBefore) {
        // todo - phases should already be sorted, don't think this is necessary
        //const sorted = [...this.$data.schedulePhases].sort((a, b) => a.ordinal - b.ordinal);
        const targetIdx = this.$data.schedulePhases.findIndex(p => p.id === insertBefore.id);
        const prevPhase = targetIdx > 0 ? this.$data.schedulePhases[targetIdx - 1] : null;

        if (prevPhase) {
          calculatedOrdinal = Math.floor((prevPhase.ordinal + insertBefore.ordinal) / 2);
        } else {
          calculatedOrdinal = Math.floor(insertBefore.ordinal / 2);
        }
      } else {
        if (this.$data.schedulePhases.length === 0) {
          calculatedOrdinal = 10;
        } else {
          const maxOrdinal = Math.max(...this.$data.schedulePhases.map(p => p.ordinal));
          calculatedOrdinal = maxOrdinal + 10;
        }
      }

      this.form = phase? {
        id: phase.id,
        name: phase.name,
        ordinal: phase.ordinal,
        phase_type: phase.phase_type,
        temperature: phase.temperature ?? '',
        rate: phase.rate ?? '',
        duration: phase.duration || ''
      } : {
        id: '',
        name: '',
        ordinal: calculatedOrdinal,
        phase_type: 'ramp',
        temperature: '',
        rate: '',
        duration: ''
      };

      this.setActiveRampMode((phase && !phase.rate && phase.duration) ? 'duration' : 'rate');
      this.onPhaseTypeChange();
      this.show = true;
    },

    close() { this.show = false; },

    async submit() {
      if (this.form.phase_type === 'ramp' && !this.form.rate && !this.form.duration) {
        Alpine.store('toast').showToast("Please enter either a Rate or Duration for Ramp phases.", "error");
        return;
      }

      const ordinal = parseInt(this.form.ordinal);
      const p = this.form;

      if (!this.form.id) {
        // todo - only reassign ordinals if there is a need.
        const existingOrdinals = new Set(this.$data.schedulePhases.map(p => p.ordinal));
        if (ordinal <= 0 || existingOrdinals.has(ordinal)) {
          const sortedSubsequent = [...this.$data.schedulePhases]
            .filter(phase => phase.ordinal >= ordinal)
            .sort((a, b) => b.ordinal - a.ordinal);

          let nextMinGapOrdinal = ordinal + (sortedSubsequent.length * 10);
          for (const phaseToUpdate of sortedSubsequent) {
            await Alpine.store('network').apiRequest(
              `/schedule/${this.selectedSchedule.id}/phase/${phaseToUpdate.id}`,
              'PUT',
              { ...phaseToUpdate, ordinal: nextMinGapOrdinal }
            );
            nextMinGapOrdinal -= 10;
          }
        }
      }

      const payload = {
        name: p.name,
        ordinal: ordinal,
        phase_type: p.phase_type,
        schedule_id: parseInt(this.selectedSchedule.id),
        temperature: p.temperature !== "" ? parseInt(p.temperature) : null,
        rate: p.phase_type === 'constant' ? null : (p.rate !== "" ? parseInt(p.rate) : null),
        duration: p.duration || null
      };

      try {
        if (p.id) {
          await Alpine.store('network').apiRequest(`/schedule/${this.selectedSchedule.id}/phase/${p.id}`, 'PUT', payload);
          Alpine.store('toast').showToast("Phase updated!", "success");
        } else {
          await Alpine.store('network').apiRequest(`/schedule/${this.selectedSchedule.id}/phase`, 'POST', payload);
          Alpine.store('toast').showToast("Phase added!", "success");
        }
        this.show = false;
      } finally {
        this.$data.loadScheduleDetail();
      }
    },

    delete(scheduleId, phase) {
      const phStr = phase.name ? `"${phase.name}"` : `Phase #${phase.id}`;
      this.$data.confirmModal.confirm(`Delete phase ${phStr} from the schedule?`, async () => {
        try {
          await Alpine.store('network').apiRequest(`/schedule/${scheduleId}/phase/${phase.id}`, 'DELETE');
          Alpine.store('toast').showToast("Phase removed", "warning");
        } catch (error) {
          Alpine.store('toast').showToast(`Phase delete failed: ${error.message}`, "error");
        } finally {
          this.$data.loadScheduleDetail();
        }
      });
    },

    setActiveRampMode(mode) {
      if (this.form.phase_type !== 'ramp') return;
      this.activeRamMode = mode;
    },

    onPhaseTypeChange() {
      const currentOrdinal = parseInt(this.form.ordinal);
      if (this.form.phase_type === 'constant') {
        //todo - phases should already be sorted, don't think this is necessary
        //const sorted = [...this.schedulePhases].sort((a, b) => a.ordinal - b.ordinal);
        const precedingPhases = this.$data.schedulePhases.filter(p => p.ordinal < currentOrdinal);
        const relativePrev = precedingPhases.length > 0 ? precedingPhases[precedingPhases.length - 1] : null;

        if (!relativePrev || relativePrev.phase_type !== 'ramp') {
          Alpine.store('toast').showToast("Constant phases must immediately follow a Ramp phase.", "error");
          this.form.phase_type = 'ramp';
          return;
        }

        this.form.temperature = this.$data.getPrecedingTemperature(currentOrdinal);
        this.form.rate = '';
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

function BaseTab() {
    return {
        show: false,
        open() { this.show = true; },
        close() { this.show = false; },
    }
}

function DashboardTab() {
  return {
    ...BaseTab(),
    name: "dashboard",
    chart: null,

    get selectedSchedule() {
        return this.$data.tabs.schedules.selectedSchedule;
    },

    async loadDashboardScheduleChart() {
      const ctx = document.getElementById('dashboardChart')?.getContext('2d');
      if (!ctx) return;

      if (!this.selectedSchedule) return;

      let datasets = null;
      phases = await Alpine.store('network').apiRequest(`/schedule/${this.selectedSchedule.id}/phase`);

      const dataPoints = computeTemperatureProfilePoints(phases);

      datasets = [{
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

      if (this.chart) {
        const chart = Alpine.raw(this.chart);
        chart.data = { datasets };
        chart.update();
        return;
      }

      this.chart = new Chart(ctx, {
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
              title: { display: true, text: 'Target Temp (°C)', color: '#94a3b8' },
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
    },

  }
}

function UsersTab() {
  return {
    ...BaseTab(),
    name: "users",
    modal: UserModal(),
  }
}

function DevicesTab() {
  return {
    ...BaseTab(),
    name: "devices",
    modal: DeviceModal(),
  }
}

function SchedulesTab() {
  return {
    ...BaseTab(),
    name: "schedules",
    modal: ScheduleModal(),
    phaseModal: PhaseModal(),
    selectedSchedule: null,
    chart: null,

    async init() {
      Alpine.effect(() => {
        if (Alpine.store('schedules').items?.length) {
            this.selectSchedule();
        } else {
            this.selectedSchedule = null;
        }
      });
    },

    async selectSchedule(schedule = null) {
      const schedules = Alpine.store('schedules').items;
      if (!schedules) return;

      selectedSchedule = schedule ?? this.selectedSchedule;

      if (selectedSchedule && !schedules.some(s => s.id === selectedSchedule.id)) {
        selectedSchedule = null;
      }

      if (!selectedSchedule && schedules.length > 0) {
        selectedSchedule = schedules[0];
      }

      if (selectedSchedule != this.selectedSchedule) {
        this.selectedSchedule = selectedSchedule;
      }
    },

    get selectedScheduleOwnerName() {
      if (!this.selectedSchedule) return '--';
      const u = Alpine.store('users').items?.find(x => x.id === this.selectedSchedule.user_id);
      return u ? u.name : `User #${this.selectedSchedule.user_id}`;
    },

    async loadScheduleDetail() {
      if (!this.selectedSchedule) return;
      const ctx = document.getElementById('scheduleDetailChart')?.getContext('2d');
      if (!ctx) return;

      const phases = await Alpine.store('network').apiRequest(`/schedule/${this.selectedSchedule.id}/phase`);

      this.schedulePhases = (phases || []).sort((a, b) => a.ordinal - b.ordinal);

      const dataPoints = computeTemperatureProfilePoints(this.schedulePhases);

      if (this.chart) {
        const chart = Alpine.raw(this.chart);
        chart.data.datasets[0].data = dataPoints.map(p => ({ x: p.x, y: p.temp })),
        chart.update();
        return;
      }

      this.chart = new Chart(ctx, {
        type: 'line',
        data: {
          datasets: [{
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
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            x: {
              type: 'linear',
              title: { display: true, text: 'Time (Hours)', color: '#94a3b8' },
              grid: { color: '#1e293b' },
              ticks: { color: '#64748b', font: { size: 10 }, callback: (val) => hoursToDuration(val) }
            },
            y: {
              title: { display: true, text: 'Temperature (°C)', color: '#94a3b8' },
              grid: { color: '#1e293b' },
              ticks: { color: '#64748b', font: { size: 10 } },
              beginAtZero: true
            }
          },
          plugins: {
            legend: { display: false },
            tooltip: { callbacks: { label: (ctx) => ` Temp: ${ctx.parsed.y}°C (${hoursToDuration(ctx.parsed.x)})` } }
          }
        }
      });
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
      alert("shouldn't ever happen");
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

    getPrecedingTemperature(editingOrdinal = null) {
      let targetList = [...this.$data.schedulePhases];
      if (editingOrdinal !== null) {
        targetList = targetList.filter(p => p.ordinal < editingOrdinal);
      }
      if (targetList.length === 0) return DEFAULT_ROOM_TEMP;
      const lastPhase = targetList[targetList.length - 1];
      return (lastPhase.temperature !== null && lastPhase.temperature !== undefined) ? lastPhase.temperature : DEFAULT_ROOM_TEMP;
    },

  }
}

// --- Alpine.js App ---
document.addEventListener('alpine:init', () => {
  Alpine.directive('icon', (el, { expression }) => {
    // x-icon="..." directive to create a data-lucide="..." on the element and
    // call lucide.createIcons() to register it.
    el.setAttribute('data-lucide', expression);
    lucide.createIcons({ scope: el });
  }),

  Alpine.store('network', {

    async apiRequest(endpoint, method = 'GET', body = null) {
      const options = { method, headers: { 'Content-Type': 'application/json' } };
      if (body) options.body = JSON.stringify(body);

      const res = await fetch(endpoint, options);
      const status = res.status;
      let data = null;

      if (status !== 204) {
        const text = await res.text();
        data = text ? JSON.parse(text) : null;
      }

      if (!res.ok) {
        if (res.status === 401) {
          Alpine.store('auth').unauthorized();
        }
        let errorMsg = `Error (${status})`;
        if (data && data.detail) {
          if (Array.isArray(data.detail)) {
            errorMsg = data.detail.map(e => `${e.loc ? e.loc.join('.') + ': ' : ''}${e.msg}: ${e.input}`).join(', ');
          } else if (typeof data.detail === 'string') {
            errorMsg = data.detail;
          }
        }
        throw new Error(errorMsg);
      }
      return data;
    }
  }),

  Alpine.store('toast', {
    toasts: [],

    showToast(message, type = 'info') {
      const toast = { id: Date.now(), message, type };
      this.toasts.push(toast);
      setTimeout(() => {
        this.toasts = this.toasts.filter(t => t.id !== toast.id);
      }, 4000);
    }
  }),

  Alpine.store('auth', {
    user: null,
    initialized: false,
    init() {
        this.initialized = this.initialize();
    },

    async initialize() {
      try {
        const user = await Alpine.store('network').apiRequest('/auth/me');
        this.user = user;
        Alpine.store('toast').showToast(`Logged in as ${user.name} (${user.username}).`)
      } catch (error) {
        this.user = null;
      }
    },

    get isAuthenticated() { return this.user !== null; },

    async getUser() {
      await this.initialized;
      return this.user;
    },

    async login(payload) {
      const response = await Alpine.store('network').apiRequest("/auth/login", 'POST', payload);
      this.user = response;
    },

    async logout() {
      await Alpine.store('network').apiRequest("/auth/logout").catch(() => []);
      this.user = null;
    },

    unauthorized() {
      this.user = null;
      window.dispatchEvent(new CustomEvent('refresh-view'));
    }

  }),

  // todo? - move the entity stores onto kilnApp
  Alpine.store('users', createEntityStore('/user')),
  Alpine.store('devices', createEntityStore('/device')),
  Alpine.store('schedules', createEntityStore('/schedule')),

  Alpine.data('kilnApp', () => ({

    // App State & Data Collections
    schedulePhases: [], // todo move into tab

    loginModal: LoginModal(),
    confirmModal: ConfirmModal(),

    activeTab: null,
    tabs: {
        dashboard: DashboardTab(),
        users: UsersTab(),
        devices: DevicesTab(),
        schedules: SchedulesTab(),
    },

    async refreshCurrentView() {
      try {
        if (!await Alpine.store('auth').getUser()) this.loginModal.open();
      } catch (err) {
        Alpine.store('toast').showToast(err, "error");
      }
    },

    init() {
      this.activeTab = this.tabs[window.location.hash.replace("#", "")] || this.tabs.dashboard;
      this.activeTab.open();
      this.refreshCurrentView();

      window.addEventListener('hashchange', () => {
        const tabname = window.location.hash.replace("#", "") || "dashboard";
        if (tabname != this.activeTab?.name) {
          if (this.activeTab) this.activeTab.close();
          this.activeTab = this.tabs[tabname];
          if (this.activeTab) {
            this.activeTab.open();
            this.refreshCurrentView();
          }
        }
      });
    },

    switchTab(tab) {
      window.location.hash = `#${tab}`
    },

  }))

});
