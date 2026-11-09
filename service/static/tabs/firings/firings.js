'use strict';

function FiringsTab() {
  return {
    ...BaseTab(),
    name: "firings",
  }
}

Alpine.store('tabs')['firings'] = FiringsTab();