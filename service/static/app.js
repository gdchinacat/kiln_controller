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

// --- Alpine.js App ---
document.addEventListener('alpine:init', () => {
  Alpine.data('kilnApp', () => ({
    // App State & Data Collections
    activeTab: 'dashboard',
    selectedScheduleId: null,
    users: [],
    devices: [],
    schedules: [],
    schedulePhases: [],
    serverOrigin: '',

    // Console & Toasts State
    consoleDrawerOpen: false,
    hasUnreadLogs: false,
    consoleLogs: [],
    toasts: [],
    requestCounter: 0,

    // Modal Visibility & Form Data
    modals: {
      user: false,
      device: false,
      schedule: false,
      phase: false,
      confirm: false
    },

    forms: {
      user: { id: '', name: '', username: '', email: '', phone_number: '' },
      device: { id: '', name: '', host: '', port: 5000, user_id: '', url: '', description: '' },
      schedule: { id: '', name: '', user_id: '' },
      phase: { id: '', name: '', ordinal: 10, phase_type: 'ramp', temperature: '', rate: '', duration: '' }
    },

    // Ramp/Phase logic states
    activeRampMode: 'rate',
    confirmDialog: { message: '', action: null },
    dashboardChartInstance: null,
    detailChartInstance: null,

    init() {
      this.serverOrigin = `Connected: ${window.location.origin}`;
      this.refreshCurrentView();
      this.$nextTick(() => lucide.createIcons());
    },

    // --- Navigation ---
    switchTab(tab) {
      this.activeTab = tab;
      this.refreshCurrentView();
    },

    async refreshCurrentView() {
      try {
        if (this.activeTab === 'dashboard') await this.renderDashboard();
        else if (this.activeTab === 'users') await this.renderUsers();
        else if (this.activeTab === 'devices') await this.renderDevices();
        else if (this.activeTab === 'schedules') await this.renderSchedules();
      } catch (e) {
        console.error("View refresh error:", e);
      }
    },

    // --- API Helper ---
    async apiRequest(endpoint, method = 'GET', body = null) {
      const reqId = ++this.requestCounter;
      this.logConsoleRequest(reqId, method, endpoint, body);
      try {
        const options = { method, headers: { 'Content-Type': 'application/json' } };
        if (body) options.body = JSON.stringify(body);

        const res = await fetch(endpoint, options);
        const status = res.status;
        let data = null;

        if (status !== 204) {
          const text = await res.text();
          data = text ? JSON.parse(text) : null;
        }

        this.logConsoleResponse(reqId, status, data);

        if (!res.ok) {
          let errorMsg = `Server error (${status})`;
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
      } catch (err) {
        if (!err.message.includes('Server error')) {
          this.showToast(`Server Connection Error: ${err.message}`, 'error');
        } else {
          this.showToast(err.message, 'error');
        }
        throw err;
      }
    },

    // --- Views Rendering ---
    async renderDashboard() {
      const [users, devices, schedules] = await Promise.all([
        this.apiRequest('/user/').catch(() => []),
        this.apiRequest('/device/').catch(() => []),
        this.apiRequest('/schedule/').catch(() => [])
      ]);

      this.users = users;
      this.devices = devices;
      this.schedules = schedules;

      if (schedules.length > 0 && !this.selectedScheduleId) {
        this.selectedScheduleId = schedules[0].id;
      }

      if (this.selectedScheduleId) {
        await this.loadDashboardScheduleChart(this.selectedScheduleId);
      }
      this.$nextTick(() => lucide.createIcons());
    },

    async renderUsers() {
      this.users = await this.apiRequest('/user/').catch(() => []);
      this.$nextTick(() => lucide.createIcons());
    },

    async renderDevices() {
      const [devices, users] = await Promise.all([
        this.apiRequest('/device/').catch(() => []),
        this.apiRequest('/user/').catch(() => [])
      ]);
      this.devices = devices;
      this.users = users;
      this.$nextTick(() => lucide.createIcons());
    },

    async renderSchedules() {
      const [schedules, users] = await Promise.all([
        this.apiRequest('/schedule/').catch(() => []),
        this.apiRequest('/user/').catch(() => [])
      ]);
      this.schedules = schedules;
      this.users = users;

      if (schedules.length > 0) {
        if (!this.selectedScheduleId || !schedules.some(s => s.id === this.selectedScheduleId)) {
          this.selectedScheduleId = schedules[0].id;
        }
        await this.loadScheduleDetail(this.selectedScheduleId);
      } else {
        this.selectedScheduleId = null;
        this.schedulePhases = [];
      }
      this.$nextTick(() => lucide.createIcons());
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
        const [schedules, users, phases] = await Promise.all([
          this.apiRequest('/schedule/'),
          this.apiRequest('/user/').catch(() => []),
          this.apiRequest(`/schedule/${scheduleId}/phase/`).catch(() => [])
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
      const [schedules, users, phases] = await Promise.all([
        this.apiRequest('/schedule/'),
        this.apiRequest('/user/').catch(() => []),
        this.apiRequest(`/schedule/${scheduleId}/phase/`).catch(() => [])
      ]);

      this.schedules = schedules;
      this.users = users;
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
      this.$nextTick(() => lucide.createIcons());
    },

    // --- Computed Properties for Detail View ---
    get currentSchedule() {
      return this.schedules.find(s => s.id === this.selectedScheduleId) || null;
    },

    get currentScheduleOwnerName() {
      if (!this.currentSchedule) return '--';
      const u = this.users.find(x => x.id === this.currentSchedule.user_id);
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

    // --- User Actions ---
    openUserModal(user = null) {
      this.forms.user = user ? { ...user } : { id: '', name: '', username: '', password: '', email: '', phone_number: '' };
      this.modals.user = true;
      this.$nextTick(() => lucide.createIcons());
    },

    async handleUserSubmit() {
      const { id, ...payload } = this.forms.user;
      payload.email = payload.email || null;
      payload.phone_number = payload.phone_number || null;

      if (id) {
        await this.apiRequest(`/user/${id}`, 'PUT', payload);
        this.showToast("User updated successfully!", "success");
      } else {
        await this.apiRequest('/user/', 'POST', payload);
        this.showToast("User created successfully!", "success");
      }
      this.modals.user = false;
      this.refreshCurrentView();
    },

    deleteUser(user) {
      const nameStr = user.name ? `${user.name} (@${user.username})` : `User #${user.id}`;
      this.showConfirmDialog(`Are you sure you want to delete user "${nameStr}"?`, async () => {
        await this.apiRequest(`/user/${user.id}`, 'DELETE');
        this.showToast("User deleted", "warning");
        this.refreshCurrentView();
      });
    },

    // --- Device Actions ---
    openDeviceModal(device = null) {
      if (this.users.length === 0) {
        this.showToast("Cannot add or edit kiln until users are loaded", "warning");
        return;
      }
      this.forms.device = device
        ? { ...device, description: device.description || '', url: device.url || '' }
        : { id: '', name: '', host: '', port: 5000, user_id: this.users[0]?.id || '', url: '', description: '' };
      this.modals.device = true;
      this.$nextTick(() => lucide.createIcons());
    },

    async handleDeviceSubmit() {
      if (!this.forms.device.user_id) {
        this.showToast("Please select a valid user for this device", "error");
        return;
      }
      const { id, ...payload } = this.forms.device;
      payload.port = parseInt(payload.port);
      payload.user_id = parseInt(payload.user_id);
      payload.url = payload.url || null;
      payload.description = payload.description || null;

      if (id) {
        await this.apiRequest(`/device/${id}`, 'PUT', payload);
        this.showToast("Kiln updated successfully!", "success");
      } else {
        await this.apiRequest('/device/', 'POST', payload);
        this.showToast("Kiln added successfully!", "success");
      }
      this.modals.device = false;
      this.refreshCurrentView();
    },

    deleteDevice(device) {
      const deviceStr = device.name ? `"${device.name}" (${device.host}:${device.port})` : `Device #${device.id}`;
      this.showConfirmDialog(`Are you sure you want to delete kiln ${deviceStr}?`, async () => {
        await this.apiRequest(`/device/${device.id}`, 'DELETE');
        this.showToast("Kiln removed", "warning");
        this.refreshCurrentView();
      });
    },

    // --- Schedule Actions ---
    openScheduleModal(schedule = null) {
      if (this.users.length === 0) {
        this.showToast("Cannot add or edit schedule until users are loaded", "warning");
        return;
      }
      this.forms.schedule = schedule
        ? { ...schedule }
        : { id: '', name: '', user_id: this.users[0]?.id || '' };
      this.modals.schedule = true;
      this.$nextTick(() => lucide.createIcons());
    },

    async handleScheduleSubmit() {
      if (!this.forms.schedule.user_id) {
        this.showToast("Please select a user for this schedule", "error");
        return;
      }
      const { id, ...payload } = this.forms.schedule;
      payload.user_id = parseInt(payload.user_id);

      if (id) {
        await this.apiRequest(`/schedule/${id}`, 'PUT', payload);
        this.showToast("Schedule updated!", "success");
      } else {
        const created = await this.apiRequest('/schedule/', 'POST', payload);
        if (created && created.id) this.selectedScheduleId = created.id;
        this.showToast("Schedule created!", "success");
      }
      this.modals.schedule = false;
      this.refreshCurrentView();
    },

    deleteSchedule(schedule) {
      const sch = typeof schedule === 'object' ? schedule : this.schedules.find(s => s.id === schedule);
      const schStr = sch ? `"${sch.name}"` : `Schedule #${schedule}`;
      this.showConfirmDialog(`Are you sure you want to delete firing schedule ${schStr} and all its phases?`, async () => {
        const id = sch ? sch.id : schedule;
        await this.apiRequest(`/schedule/${id}`, 'DELETE');
        this.selectedScheduleId = null;
        this.showToast("Schedule deleted", "warning");
        this.refreshCurrentView();
      });
    },

    // --- Phase Actions & Calculations ---
    openPhaseModal(phaseToEdit = null, insertBeforePhase = null) {
      if (!this.selectedScheduleId) {
        this.showToast("Select a schedule first", "warning");
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
      this.$nextTick(() => lucide.createIcons());
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
          this.showToast("Constant phases must immediately follow a Ramp phase.", "error");
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
        this.showToast("Please enter either a Rate or Duration for Ramp phases.", "error");
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
            await this.apiRequest(
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
        await this.apiRequest(`/schedule/${this.selectedScheduleId}/phase/${p.id}`, 'PUT', payload);
        this.showToast("Phase updated!", "success");
      } else {
        await this.apiRequest(`/schedule/${this.selectedScheduleId}/phase/`, 'POST', payload);
        this.showToast("Phase added!", "success");
      }
      this.modals.phase = false;
      this.refreshCurrentView();
    },

    deletePhase(scheduleId, phase) {
      const phStr = phase.name ? `"${phase.name}"` : `Phase #${phase.id}`;
      this.showConfirmDialog(`Delete phase ${phStr} from the schedule?`, async () => {
        await this.apiRequest(`/schedule/${scheduleId}/phase/${phase.id}`, 'DELETE');
        this.showToast("Phase removed", "warning");
        this.refreshCurrentView();
      });
    },

    // --- Dialogs, Drawer & Toasts ---
    showConfirmDialog(message, action) {
      this.confirmDialog.message = message;
      this.confirmDialog.action = action;
      this.modals.confirm = true;
      this.$nextTick(() => lucide.createIcons());
    },

    confirmAction() {
      if (this.confirmDialog.action) this.confirmDialog.action();
      this.modals.confirm = false;
    },

    toggleConsoleDrawer() {
      this.consoleDrawerOpen = !this.consoleDrawerOpen;
      if (this.consoleDrawerOpen) this.hasUnreadLogs = false;
    },

    logConsoleRequest(reqId, method, endpoint, body) {
      const time = new Date().toLocaleTimeString();
      this.consoleLogs.push({ reqId, time, method, endpoint, body, type: 'req' });
      if (!this.consoleDrawerOpen) this.hasUnreadLogs = true;
    },

    logConsoleResponse(reqId, status, data) {
      this.consoleLogs.push({ reqId, status, data, type: 'res' });
    },

    clearConsoleLogs() {
      this.consoleLogs = [];
    },

    showToast(message, type = 'info') {
      const toast = { id: Date.now(), message, type };
      this.toasts.push(toast);
      this.$nextTick(() => lucide.createIcons());
      setTimeout(() => {
        this.toasts = this.toasts.filter(t => t.id !== toast.id);
      }, 4000);
    }
  }));
});
