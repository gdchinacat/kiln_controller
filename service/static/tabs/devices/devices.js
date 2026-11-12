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
    name: "devices",
    modal: DeviceModal(),
    selected: null,

    async init() {
      Alpine.effect(() => this.select());
    },

    async select(entity = null) {
      const entities = Alpine.store(this.name).items;

      let selected = entity ?? this.selected;

      if (selected) {
        selected = entities.find(e => e.id === selected.id);
      }

      if (!selected && entities?.length > 0) {
        selected = entities[0];
      }

      if (selected != this.selected) {
        this.selected = selected;
      }
    },

  };
}

Alpine.store('tabs')['devices'] = DevicesTab();