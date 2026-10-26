/**
 * Sara AI - Global JavaScript Utilities
 * Handles settings modal, toast notifications, and server status checks.
 */

window.SaraApp = {
  /**
   * Display a floating toast notification.
   * @param {string} message 
   * @param {'info'|'success'|'error'} type 
   */
  showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    let icon = 'ℹ️';
    if (type === 'success') icon = '✅';
    if (type === 'error') icon = '⚠️';

    toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(100%)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  },

  /**
   * Fetch provider status from the backend.
   */
  async fetchStatus() {
    try {
      const resp = await fetch('/api/status');
      if (resp.ok) {
        return await resp.json();
      }
    } catch (e) {
      console.error('Failed to load status:', e);
    }
    return null;
  },

  /**
   * Initialize settings modal listeners.
   */
  initSettingsModal() {
    const modal = document.getElementById('settings-modal');
    if (!modal) return;

    const openBtns = [
      document.getElementById('open-settings-btn'),
      document.getElementById('open-settings-topbar-btn'),
      document.getElementById('open-settings-voice-btn')
    ];
    const closeBtn = document.getElementById('close-settings-btn');
    const saveBtn = document.getElementById('save-settings-btn');

    const openModal = async () => {
      modal.classList.remove('hidden');
      const data = await this.fetchStatus();
      if (data && data.ai_status) {
        const activeLabel = document.getElementById('settings-active-provider');
        if (activeLabel) {
          activeLabel.textContent = `${data.ai_status.active_provider} (Mode: ${data.ai_status.mode})`;
        }

        const listContainer = document.getElementById('settings-provider-list');
        if (listContainer) {
          listContainer.innerHTML = '';
          const providers = data.ai_status.providers || {};
          for (const key of Object.keys(providers)) {
            const p = providers[key];
            const row = document.createElement('div');
            row.className = 'provider-row';
            const badge = p.configured ? '✅ Configured' : '❌ Not Configured';
            row.innerHTML = `
              <div>
                <strong>${p.name}</strong>
                <div class="text-muted" style="font-size: 0.78rem;">Model: ${p.model || 'N/A'}</div>
              </div>
              <span class="status-badge" style="font-size: 0.75rem;">${badge}</span>
            `;
            listContainer.appendChild(row);
          }
        }
      }
    };

    const closeModal = () => modal.classList.add('hidden');

    openBtns.forEach(btn => {
      if (btn) btn.addEventListener('click', openModal);
    });

    if (closeBtn) closeBtn.addEventListener('click', closeModal);
    if (saveBtn) saveBtn.addEventListener('click', closeModal);

    modal.addEventListener('click', (e) => {
      if (e.target === modal) closeModal();
    });
  }
};

document.addEventListener('DOMContentLoaded', () => {
  window.SaraApp.initSettingsModal();
});
