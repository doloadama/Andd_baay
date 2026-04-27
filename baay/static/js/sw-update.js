/**
 * sw-update.js — Prompt user when a new service-worker version is ready.
 * Shows a non-blocking toast with a "Refresh" button.
 */
(function () {
  'use strict';

  function showUpdateToast(reg) {
    if (document.getElementById('sw-update-toast')) return;

    const toast = document.createElement('div');
    toast.id = 'sw-update-toast';
    toast.style.cssText = `
      position:fixed;bottom:88px;left:16px;right:16px;z-index:1050;
      background:var(--card-bg);color:var(--text-main);
      border:1px solid var(--border-color);border-radius:12px;
      padding:14px 18px;display:flex;align-items:center;gap:12px;
      box-shadow:var(--shadow-lg);backdrop-filter:blur(10px);
      font-size:0.9rem;max-width:420px;margin:0 auto;
    `;
    toast.innerHTML = `
      <span style="font-size:1.1rem">🔄</span>
      <span style="flex:1">Nouvelle version disponible.</span>
      <button id="sw-update-btn" style="
        background:var(--accent);color:#0f172a;border:none;
        border-radius:8px;padding:6px 14px;font-weight:600;
        font-size:0.82rem;cursor:pointer;white-space:nowrap;
      ">Mettre à jour</button>
    `;
    document.body.appendChild(toast);

    document.getElementById('sw-update-btn').addEventListener('click', () => {
      if (reg.waiting) {
        reg.waiting.postMessage({ action: 'skipWaiting' });
      }
      toast.remove();
    });
  }

  function listenForUpdates(reg) {
    reg.addEventListener('updatefound', () => {
      const newWorker = reg.installing;
      if (!newWorker) return;
      newWorker.addEventListener('statechange', () => {
        if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
          showUpdateToast(reg);
        }
      });
    });
  }

  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.ready.then(listenForUpdates);
    // Also listen for controllerchange to reload once new SW activates
    navigator.serviceWorker.addEventListener('controllerchange', () => {
      window.location.reload();
    });
  }
})();
