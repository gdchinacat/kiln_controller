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
    items: [],
    loading: false,

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

function BaseTab() {
    return {
        show: false,
        open() { this.show = true; this.render(); },
        close() { this.show = false; },
        async render() { },
    }
}

function DashboardTab() {
  return {
    ...BaseTab(),
    name: "dashboard",

    async render() {
      const [users, devices, schedules] = await Promise.all([
        Alpine.store('users').refresh(),
        Alpine.store('devices').refresh(),
        Alpine.store('schedules').refresh(),
      ]);

      if (schedules.length > 0 && !this.$data.selectedScheduleId) {
        this.$data.selectedScheduleId = schedules[0].id;
      }

      if (this.$data.selectedScheduleId) {
        await this.$data.loadDashboardScheduleChart(this.$data.selectedScheduleId);
      }
    },
  }
}

function UserTab() {
  return {
    ...BaseTab(),
    name: "users",
    modal: UserModal(),
    async render() {
      await Alpine.store('users').refresh();
    },
  }
}

function DeviceTab() {
  return {
    ...BaseTab(),
    name: "devices",
    modal: DeviceModal(),
    async render() {
      const [users, devices] = await Promise.all([
        Alpine.store('users').refresh(),
        Alpine.store('devices').refresh(),
      ]);
    },
  }
}

function ScheduleTab() {
  return {
    ...BaseTab(),
    name: "schedules",
    modal: ScheduleModal(),
    async render() {
      const [users, schedules] = await Promise.all([
        Alpine.store('users').refresh(),
        Alpine.store('schedules').refresh(),
      ]);

      if (schedules.length > 0) {
        if (!this.selectedScheduleId || !schedules.some(s => s.id === this.selectedScheduleId)) {
          this.selectedScheduleId = schedules[0].id;
        }
        await this.$data.loadScheduleDetail(this.selectedScheduleId);
      } else {
        this.selectedScheduleId = null;
        this.schedulePhases = [];
      }
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
        if (res.status == 401) {
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
  //Alpine.store('schedulePhases', createEntityStore('/schedule/${schedule_id}/phase')),

  Alpine.data('kilnApp', () => ({

    // App State & Data Collections
    selectedScheduleId: null,
    schedulePhases: [], // todo move into tab

    loginModal: LoginModal(),
    confirmModal: ConfirmModal(),

    activeTab: null,
    tabs: {
        dashboard: DashboardTab(),
        users: UserTab(),
        devices: DeviceTab(),
        schedules: ScheduleTab(),
    },

    // Modal Visibility & Form Data
    modals: {
      phase: false,
    },
    forms: {
      phase: { id: '', name: '', ordinal: 10, phase_type: 'ramp', temperature: '', rate: '', duration: '' }
    },

    // Ramp/Phase logic states
    activeRampMode: 'rate',
    dashboardChartInstance: null,
    detailChartInstance: null,

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

    // --- Navigation ---
    switchTab(tab) {
      window.location.hash = `#${tab}`
    },

    async selectSchedule(id) {
      this.selectedScheduleId = id;
      await this.loadScheduleDetail(id);
    },

    async loadDashboardScheduleChart(scheduleId) {
      const ctx = document.getElementById('dashboardChart')?.getContext('2d');
      if (!ctx) return;

      this.selectedScheduleId = parseInt(scheduleId);

      let datasets = null;
      if (scheduleId) {
        const [users, schedules, phases] = await Promise.all([
          Alpine.store('users').refresh(),
          Alpine.store('schedules').refresh(),
          Alpine.store('network').apiRequest(`/schedule/${scheduleId}/phase`).catch(() => [])
        ]);

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
      }

      if (this.dashboardChartInstance) this.dashboardChartInstance.destroy();

      this.dashboardChartInstance = new Chart(ctx, {
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

    async loadScheduleDetail(scheduleId) {
      if (!scheduleId) return;
      const [users, schedules, phases] = await Promise.all([
        Alpine.store('users').refresh(),
        Alpine.store('schedules').refresh(),
        Alpine.store('network').apiRequest(`/schedule/${scheduleId}/phase`).catch(() => [])
      ]);

      this.schedulePhases = (phases || []).sort((a, b) => a.ordinal - b.ordinal);

      const dataPoints = computeTemperatureProfilePoints(this.schedulePhases);
      const ctx = document.getElementById('scheduleDetailChart')?.getContext('2d');
      if (!ctx) return;

      if (this.detailChartInstance) this.detailChartInstance.destroy();

      this.detailChartInstance = new Chart(ctx, {
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

    // --- Computed Properties for Detail View ---
    get currentSchedule() {
      return Alpine.store('schedules').items.find(s => s.id === this.selectedScheduleId) || null;
    },

    get currentScheduleOwnerName() {
      if (!this.currentSchedule) return '--';
      const u = Alpine.store('users').items.find(x => x.id === this.currentSchedule.user_id);
      return u ? u.name : `User #${this.currentSchedule.user_id}`;
    },

    // Helper calculations for Phase Table
    getPrecedingTemperature(editingOrdinal = null) {
      let targetList = [...this.schedulePhases];
      if (editingOrdinal !== null) {
        targetList = targetList.filter(p => p.ordinal < editingOrdinal);
      }
      if (targetList.length === 0) return DEFAULT_ROOM_TEMP;
      const lastPhase = targetList[targetList.length - 1];
      return (lastPhase.temperature !== null && lastPhase.temperature !== undefined) ? lastPhase.temperature : DEFAULT_ROOM_TEMP;
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

    // --- Phase Actions & Calculations ---
    openPhaseModal(phaseToEdit = null, insertBeforePhase = null) {
      if (!this.selectedScheduleId) {
        Alpine.store('toast').showToast("Select a schedule first", "warning");
        return;
      }

      let calculatedOrdinal;

      if (phaseToEdit) {
        calculatedOrdinal = phaseToEdit.ordinal;
      } else if (insertBeforePhase) {
        const sorted = [...this.schedulePhases].sort((a, b) => a.ordinal - b.ordinal);
        const targetIdx = sorted.findIndex(p => p.id === insertBeforePhase.id);
        const prevPhase = targetIdx > 0 ? sorted[targetIdx - 1] : null;

        if (prevPhase) {
          calculatedOrdinal = Math.floor((prevPhase.ordinal + insertBeforePhase.ordinal) / 2);
        } else {
          calculatedOrdinal = Math.floor(insertBeforePhase.ordinal / 2);
        }
      } else {
        if (this.schedulePhases.length === 0) {
          calculatedOrdinal = 10;
        } else {
          const maxOrdinal = Math.max(...this.schedulePhases.map(p => p.ordinal));
          calculatedOrdinal = maxOrdinal + 10;
        }
      }

      this.forms.phase = phaseToEdit ? {
        id: phaseToEdit.id,
        name: phaseToEdit.name,
        ordinal: phaseToEdit.ordinal,
        phase_type: phaseToEdit.phase_type,
        temperature: phaseToEdit.temperature ?? '',
        rate: phaseToEdit.rate ?? '',
        duration: phaseToEdit.duration || ''
      } : {
        id: '',
        name: '',
        ordinal: calculatedOrdinal,
        phase_type: 'ramp',
        temperature: '',
        rate: '',
        duration: ''
      };

      this.activeRampMode = (phaseToEdit && !phaseToEdit.rate && phaseToEdit.duration) ? 'duration' : 'rate';
      this.onPhaseTypeChange();
      this.modals.phase = true;
    },

    setActiveRampMode(mode) {
      if (this.forms.phase.phase_type !== 'ramp') return;
      this.activeRampMode = mode;
    },

    recalculateRampValues() {
      if (this.forms.phase.phase_type !== 'ramp') return;
      const targetTemp = parseFloat(this.forms.phase.temperature);
      const currentOrdinal = parseInt(this.forms.phase.ordinal);
      const startTemp = this.getPrecedingTemperature(currentOrdinal);

      if (isNaN(targetTemp)) return;
      const tempDiff = Math.abs(targetTemp - startTemp);

      if (this.activeRampMode === 'rate') {
        const rate = parseFloat(this.forms.phase.rate);
        if (!isNaN(rate) && rate > 0) {
          const hours = tempDiff / rate;
          this.forms.phase.duration = hoursToDuration(hours);
        }
      } else if (this.activeRampMode === 'duration') {
        const hours = durationToHours(this.forms.phase.duration);
        if (hours > 0) {
          this.forms.phase.rate = Math.round(tempDiff / hours);
        }
      }
    },

    onPhaseTypeChange() {
      const currentOrdinal = parseInt(this.forms.phase.ordinal);
      if (this.forms.phase.phase_type === 'constant') {
        const sorted = [...this.schedulePhases].sort((a, b) => a.ordinal - b.ordinal);
        const precedingPhases = sorted.filter(p => p.ordinal < currentOrdinal);
        const relativePrev = precedingPhases.length > 0 ? precedingPhases[precedingPhases.length - 1] : null;

        if (!relativePrev || relativePrev.phase_type !== 'ramp') {
          Alpine.store('toast').showToast("Constant phases must immediately follow a Ramp phase.", "error");
          this.forms.phase.phase_type = 'ramp';
          return;
        }

        this.forms.phase.temperature = this.getPrecedingTemperature(currentOrdinal);
        this.forms.phase.rate = '';
      } else {
        this.recalculateRampValues();
      }
    },

    async handlePhaseSubmit() {
      const p = this.forms.phase;
      if (p.phase_type === 'ramp' && !p.rate && !p.duration) {
        Alpine.store('toast').showToast("Please enter either a Rate or Duration for Ramp phases.", "error");
        return;
      }

      let targetOrdinal = parseInt(p.ordinal);

      if (!p.id) {
        const existingOrdinals = new Set(this.schedulePhases.map(phase => phase.ordinal));
        if (targetOrdinal <= 0 || existingOrdinals.has(targetOrdinal)) {
          const sortedSubsequent = [...this.schedulePhases]
            .filter(phase => phase.ordinal >= targetOrdinal)
            .sort((a, b) => b.ordinal - a.ordinal);

          let nextMinGapOrdinal = targetOrdinal + (sortedSubsequent.length * 10);
          for (const phaseToUpdate of sortedSubsequent) {
            await Alpine.store('network').apiRequest(
              `/schedule/${this.selectedScheduleId}/phase/${phaseToUpdate.id}`,
              'PUT',
              { ...phaseToUpdate, ordinal: nextMinGapOrdinal }
            );
            nextMinGapOrdinal -= 10;
          }
        }
      }

      const payload = {
        name: p.name,
        ordinal: targetOrdinal,
        phase_type: p.phase_type,
        schedule_id: parseInt(this.selectedScheduleId),
        temperature: p.temperature !== "" ? parseInt(p.temperature) : null,
        rate: p.phase_type === 'constant' ? null : (p.rate !== "" ? parseInt(p.rate) : null),
        duration: p.duration || null
      };

      if (p.id) {
        await Alpine.store('network').apiRequest(`/schedule/${this.selectedScheduleId}/phase/${p.id}`, 'PUT', payload);
        Alpine.store('toast').showToast("Phase updated!", "success");
      } else {
        await Alpine.store('network').apiRequest(`/schedule/${this.selectedScheduleId}/phase`, 'POST', payload);
        Alpine.store('toast').showToast("Phase added!", "success");
      }
      this.modals.phase = false;
      this.refreshCurrentView();
    },

    deletePhase(scheduleId, phase) {
      const phStr = phase.name ? `"${phase.name}"` : `Phase #${phase.id}`;
      this.showConfirmDialog(`Delete phase ${phStr} from the schedule?`, async () => {
        await Alpine.store('network').apiRequest(`/schedule/${scheduleId}/phase/${phase.id}`, 'DELETE');
        Alpine.store('toast').showToast("Phase removed", "warning");
        this.refreshCurrentView();
      });
    },

  }))

});
