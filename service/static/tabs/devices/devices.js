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

    chartMetric(element, metric) {
        alert(metric);
    },

  };
}

Alpine.store('tabs')['devices'] = DevicesTab();