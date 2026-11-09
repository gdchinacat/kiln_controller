'use strict';

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

function UsersTab() {
  return {
    ...BaseTab(),
    name: "users",
    modal: UserModal(),
  }
}

Alpine.store('tabs')['users'] = UsersTab();