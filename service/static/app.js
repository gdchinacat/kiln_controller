'use strict';
const DEFAULT_ROOM_TEMP = 20;

// --- Helper Functions ---
const tabLoaders = [];
function loadTab(element, tabName) {
  tabLoaders.push((async () => {
    const module = await import(`/static/tabs/${tabName}/${tabName}.js`);
    Object.assign(window, module.exports || {});
    const response = await fetch(`/static/tabs/${tabName}/${tabName}.html`);

    if (!response.ok) {
        throw new Error(`Failed to load tab ${tabName}: ${response.status}`);
    }

    element.innerHTML = await response.text();
    Alpine.initTree(element);
  })());
}

function assert (condition, message) {
  if (!condition) {
    throw new Error(message);
  }
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

    async created(entity) {},

    async submit() {
      if (this.form.id != '') {
        await config.entityStore.save(this.form);
        Alpine.store('toast').showToast(`${config.entityType} updated successfully!`, "success");
      } else {
        let created = await config.entityStore.create(this.form);
        this.created(created);
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

function BaseTab() {
    return {
        show: false,
        open() {
          this.show = true; 
          if (window.location.hash !== `#${this.name}`) {
            history.replaceState(null, '', `#${this.name}`);
          }
        },
        close() { this.show = false; },
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
  Alpine.store('tabs', {}),

  Alpine.data('kilnApp', () => ({

    activeTab: null,

    loginModal: LoginModal(),
    confirmModal: ConfirmModal(),

    async maybeShowLogin() {
      try {
        if (!await Alpine.store('auth').getUser()) this.loginModal.open();
      } catch (err) {
        Alpine.store('toast').showToast(err, "error");
      }
    },

    init() {
      window.addEventListener('alpine:initialized', async () => {
        await Promise.allSettled(tabLoaders);
        let tabs = Alpine.store('tabs');
        this.activeTab = tabs[window.location.hash.replace("#", "")] || tabs.dashboard;
        this.activeTab.open();
        this.maybeShowLogin();

        window.addEventListener('hashchange', () => {
          const tabname = window.location.hash.replace("#", "") || "dashboard";
          if (tabname != this.activeTab?.name) {
            if (this.activeTab) this.activeTab.close();
            this.activeTab = tabs[tabname] || tabs.dashboard;
            if (this.activeTab) {
              this.activeTab.open();
              this.maybeShowLogin();
            }
          }
        });
      });
    },

    switchTab(tab) {
      window.location.hash = `#${tab}`
    },

  }))

});
