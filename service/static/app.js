const DEFAULT_ROOM_TEMP = 20;

// --- Helper Functions ---
async function initTab(element, tabName) {
    const response = await fetch(`/static/tabs/${tabName}.html`);

    if (!response.ok) {
        throw new Error(`Failed to load tab ${tabName}: ${response.status}`);
    }

    element.innerHTML = await response.text();
    Alpine.initTree(element);
}

function assert (condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

async function refreshChart(canvas, schedulePhases) {
  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  const dataPoints = computeTemperatureProfilePoints(schedulePhases);

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

function createEntityStore(endpoint) {
  return {
    items: null,
    loading: false,

    init() {
      Alpine.effect(() => {
        if (Alpine.store('auth').user) {
          this.reload();
        } else {
            this.items  = null;
        }
      });
    },

    async reload() {
      this.items = await Alpine.store('network').apiRequest(endpoint);
      return this.items;
    },

    async create(payload) {
      try {
        return await Alpine.store('network').apiRequest(endpoint, 'POST', payload);
      } finally {
        await this.reload();
      }
    },

    async save(payload) {
      try {
        return await Alpine.store('network').apiRequest(`${endpoint}/${payload.id}`, 'PUT', payload);
      } finally {
        await this.reload();
      }
    },

    async delete(id) {
      try {
        await Alpine.store('network').apiRequest(`${endpoint}/${id}`, 'DELETE');
      } finally {
        await this.reload();
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
        window.dispatchEvent(new CustomEvent('show-login'));
      }
    },

    async logout() {
      try {
        await Alpine.store('auth').logout();
        Alpine.store('toast').showToast("Logout success.", "success");
      } finally {
        window.dispatchEvent(new CustomEvent('show-login'));
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

    async confirmed() {
      if (!this.action || await this.action()) this.dismiss();
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
        try {
          await config.entityStore.delete(entity.id);
          Alpine.store('toast').showToast(`${config.entityType} deleted`, "warning");
          return true;
        } catch (error) {
          Alpine.store('toast').showToast(`${config.entityType} deleted failed: ${error.message}`, "error");
        }
        return false;
      });
    },

  };
}

function UserModal() {
  const model = () => ({
    id: '',
    version: null,
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
              `/schedule/${this.selectedSchedule.id}/phase/${phaseToUpdate.id}`,
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
        schedule_id: parseInt(this.selectedSchedule.id),
        temperature: p.temperature !== "" ? parseInt(p.temperature) : null,
        rate: (p.phase_type === 'constant') ? null : ((this.activeRampMode=='rate' && p.rate !== "") ? parseInt(p.rate) : null),
        duration: (this.activeRampMode === 'duration') ? (p.duration || null) : null,
      };

      try {
        if (p.id) {
          await Alpine.store('network').apiRequest(`/schedule/${this.selectedSchedule.id}/phase/${p.id}`, 'PUT', payload);
          Alpine.store('toast').showToast("Phase updated!", "success");
        } else {
          await Alpine.store('network').apiRequest(`/schedule/${this.selectedSchedule.id}/phase`, 'POST', payload);
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
    schedulePhases: [],

    async init() {
      Alpine.effect(() => this.selectSchedule());
    },

    async selectSchedule(schedule = null) {
      const schedules = Alpine.store('schedules').items;

      selectedSchedule = schedule ?? this.selectedSchedule;

      if (selectedSchedule && (!schedules || !schedules.some(s => s.id === selectedSchedule.id))) {
        selectedSchedule = null;
      }

      if (!selectedSchedule && schedules?.length > 0) {
        selectedSchedule = schedules[0];
      }

      if (selectedSchedule != this.selectedSchedule) {
        this.selectedSchedule = selectedSchedule;
        this.reloadSelectedSchedulePhases();
      }
    },

    async reloadSelectedSchedulePhases() {
      if (this.selectedSchedule) {
        this.schedulePhases = await Alpine.store('network').apiRequest(`/schedule/${this.selectedSchedule.id}/phase`);
      } else {
        this.schedulePhases = [];
      }
    },

    get selectedScheduleOwnerName() {
      if (!this.selectedSchedule) return '--';
      const u = Alpine.store('users').items?.find(x => x.id === this.selectedSchedule.user_id);
      return u ? u.name : `User #${this.selectedSchedule.user_id}`;
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
      return { previous: null, next: null};
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

    get admin() { return this.user?.username === 'admin'; },

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
      window.dispatchEvent(new CustomEvent('show-login'));
    }

  }),

  // todo? - move the entity stores onto kilnApp
  Alpine.store('users', createEntityStore('/user')),
  Alpine.store('devices', createEntityStore('/device')),
  Alpine.store('schedules', createEntityStore('/schedule')),

  Alpine.data('kilnApp', () => ({

    loginModal: LoginModal(),
    confirmModal: ConfirmModal(),

    activeTab: null,
    tabs: {
        dashboard: DashboardTab(),
        users: UsersTab(),
        devices: DevicesTab(),
        schedules: SchedulesTab(),
    },

    async maybeShowLogin() {
      try {
        if (!await Alpine.store('auth').getUser()) this.loginModal.open();
      } catch (err) {
        Alpine.store('toast').showToast(err, "error");
      }
    },

    init() {
      this.activeTab = this.tabs[window.location.hash.replace("#", "")] || this.tabs.dashboard;
      this.activeTab.open();
      this.maybeShowLogin();

      window.addEventListener('hashchange', () => {
        const tabname = window.location.hash.replace("#", "") || "dashboard";
        if (tabname != this.activeTab?.name) {
          if (this.activeTab) this.activeTab.close();
          this.activeTab = this.tabs[tabname];
          if (this.activeTab) {
            this.activeTab.open();
            this.maybeShowLogin();
          }
        }
      });
    },

    switchTab(tab) {
      window.location.hash = `#${tab}`
    },

  }))

});
