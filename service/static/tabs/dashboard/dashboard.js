
function DashboardTab() {
  return {
    ...BaseTab(),
    name: "dashboard",
  }
}

Alpine.store('tabs')['dashboard'] = DashboardTab();