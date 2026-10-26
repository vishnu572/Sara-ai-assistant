/**
 * Sara AI - File Processing & Result Interface
 * Section 9 Requirement: Reusable Result Component with Preview & Download.
 */

window.SaraFiles = {
  formatBytes(bytes, decimals = 2) {
    if (!bytes || bytes === 0) return '0 Bytes';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
  },

  /**
   * Render Section 9 compliant result component.
   * @param {Object} data 
   * @returns {HTMLElement}
   */
  createResultCard(data) {
    const card = document.createElement('div');
    card.className = 'result-card';

    const operation = data.operation || 'File Processing';
    const origName = data.original_name || 'file';
    const resultName = data.result_name || origName;
    const status = data.status || (data.success ? 'Completed' : 'Failed');
    const origSize = this.formatBytes(data.original_size);
    const resultSize = data.result_size ? this.formatBytes(data.result_size) : origSize;
    const savings = data.savings_percent ? ` (${data.savings_percent}% reduction)` : '';

    let previewHtml = '';
    if (data.preview_url) {
      if (data.file_type === 'Image' || resultName.match(/\.(png|jpe?g|webp|bmp|gif)$/i)) {
        previewHtml = `
          <div class="result-preview-box">
            <img src="${data.preview_url}" alt="Enhanced Preview" loading="lazy">
          </div>
        `;
      } else if (resultName.endsWith('.pdf')) {
        previewHtml = `
          <div class="result-preview-box" style="background: #1e293b; color: #94a3b8; padding: 20px; text-align: center;">
            <span>📄 PDF Document Ready for Download (${resultSize})</span>
          </div>
        `;
      }
    }

    card.innerHTML = `
      <div class="result-header">
        <h4><span class="icon">✨</span> Sara AI — Processing Complete</h4>
        <span class="status-badge" style="color: var(--success); border-color: rgba(16, 185, 129, 0.4);">
          ${status}
        </span>
      </div>
      <div class="result-body">
        <div class="result-meta-grid">
          <div class="meta-field">
            <label>Operation</label>
            <span>${operation}</span>
          </div>
          <div class="meta-field">
            <label>Original File</label>
            <span>${origName} (${origSize})</span>
          </div>
          <div class="meta-field">
            <label>Result File</label>
            <span>${resultName} (${resultSize}${savings})</span>
          </div>
          <div class="meta-field">
            <label>Status</label>
            <span>${status}</span>
          </div>
        </div>
        ${previewHtml}
      </div>
      <div class="result-footer">
        ${data.preview_url ? `<a href="${data.preview_url}" target="_blank" class="btn btn-secondary btn-sm">Preview</a>` : ''}
        ${data.download_url ? `<a href="${data.download_url}" download="${resultName}" class="btn btn-primary btn-sm">Download Result</a>` : ''}
      </div>
    `;

    return card;
  },

  /**
   * Upload and compress PDF file.
   */
  async compressPdf(file) {
    const formData = new FormData();
    formData.append('file', file);

    const resp = await fetch('/api/pdf/compress', {
      method: 'POST',
      body: formData
    });
    return await resp.json();
  },

  /**
   * Upload and enhance image file.
   */
  async enhanceImage(file) {
    const formData = new FormData();
    formData.append('file', file);

    const resp = await fetch('/api/image/enhance', {
      method: 'POST',
      body: formData
    });
    return await resp.json();
  },

  /**
   * Initialize file tools modal tabs & dropzones.
   */
  initFileTools() {
    const modal = document.getElementById('file-tools-modal');
    if (!modal) return;

    const openBtn = document.getElementById('open-file-tools-btn');
    const closeBtn = document.getElementById('close-file-tools-btn');
    const closeFooterBtn = document.getElementById('close-file-tools-footer-btn');

    const openModal = () => modal.classList.remove('hidden');
    const closeModal = () => modal.classList.add('hidden');

    if (openBtn) openBtn.addEventListener('click', openModal);
    if (closeBtn) closeBtn.addEventListener('click', closeModal);
    if (closeFooterBtn) closeFooterBtn.addEventListener('click', closeModal);

    // Tab switcher
    const tabBtns = modal.querySelectorAll('.tab-btn');
    tabBtns.forEach(btn => {
      btn.addEventListener('click', () => {
        tabBtns.forEach(b => b.classList.remove('active'));
        modal.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
        btn.classList.add('active');
        const targetId = btn.getAttribute('data-tab');
        const pane = document.getElementById(targetId);
        if (pane) pane.classList.add('active');
      });
    });

    // PDF Dropzone
    const pdfDropZone = document.getElementById('pdf-drop-zone');
    const pdfInput = document.getElementById('pdf-file-input');
    const pdfStatus = document.getElementById('pdf-process-status');
    const pdfResultArea = document.getElementById('pdf-result-card-area');

    if (pdfDropZone && pdfInput) {
      pdfDropZone.addEventListener('click', () => pdfInput.click());
      pdfDropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        pdfDropZone.classList.add('dragover');
      });
      pdfDropZone.addEventListener('dragleave', () => pdfDropZone.classList.remove('dragover'));
      pdfDropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        pdfDropZone.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
          handlePdfUpload(e.dataTransfer.files[0]);
        }
      });
      pdfInput.addEventListener('change', () => {
        if (pdfInput.files.length > 0) {
          handlePdfUpload(pdfInput.files[0]);
        }
      });
    }

    const handlePdfUpload = async (file) => {
      if (!file.name.toLowerCase().endsWith('.pdf')) {
        window.SaraApp.showToast('Please select a valid PDF file.', 'error');
        return;
      }
      pdfStatus.classList.remove('hidden');
      pdfResultArea.innerHTML = '';

      try {
        const res = await this.compressPdf(file);
        pdfStatus.classList.add('hidden');
        if (res.success) {
          const card = this.createResultCard(res);
          pdfResultArea.appendChild(card);
          window.SaraApp.showToast('PDF compressed successfully!', 'success');
        } else {
          pdfResultArea.innerHTML = `
            <div class="alert alert-error" style="color: #fca5a5; background: rgba(239,68,68,0.1); border: 1px solid #ef4444; border-radius: 8px; padding: 12px; margin-top: 14px;">
              ⚠️ ${res.error || 'Compression failed.'}
            </div>
          `;
          window.SaraApp.showToast(res.error || 'Compression failed', 'error');
        }
      } catch (err) {
        pdfStatus.classList.add('hidden');
        pdfResultArea.innerHTML = `<div class="alert alert-error">Network error processing PDF.</div>`;
      }
    };

    // Image Dropzone
    const imgDropZone = document.getElementById('image-drop-zone');
    const imgInput = document.getElementById('image-file-input');
    const imgStatus = document.getElementById('image-process-status');
    const imgResultArea = document.getElementById('image-result-card-area');

    if (imgDropZone && imgInput) {
      imgDropZone.addEventListener('click', () => imgInput.click());
      imgDropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        imgDropZone.classList.add('dragover');
      });
      imgDropZone.addEventListener('dragleave', () => imgDropZone.classList.remove('dragover'));
      imgDropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        imgDropZone.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
          handleImageUpload(e.dataTransfer.files[0]);
        }
      });
      imgInput.addEventListener('change', () => {
        if (imgInput.files.length > 0) {
          handleImageUpload(imgInput.files[0]);
        }
      });
    }

    const handleImageUpload = async (file) => {
      imgStatus.classList.remove('hidden');
      imgResultArea.innerHTML = '';

      try {
        const res = await this.enhanceImage(file);
        imgStatus.classList.add('hidden');
        if (res.success) {
          const card = this.createResultCard(res);
          imgResultArea.appendChild(card);
          window.SaraApp.showToast('Image enhanced successfully!', 'success');
        } else {
          imgResultArea.innerHTML = `
            <div class="alert alert-error" style="color: #fca5a5; background: rgba(239,68,68,0.1); border: 1px solid #ef4444; border-radius: 8px; padding: 12px; margin-top: 14px;">
              ⚠️ ${res.error || 'Enhancement failed.'}
            </div>
          `;
          window.SaraApp.showToast(res.error || 'Enhancement failed', 'error');
        }
      } catch (err) {
        imgStatus.classList.add('hidden');
        imgResultArea.innerHTML = `<div class="alert alert-error">Network error enhancing image.</div>`;
      }
    };
  }
};

document.addEventListener('DOMContentLoaded', () => {
  window.SaraFiles.initFileTools();
});
