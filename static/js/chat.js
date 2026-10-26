/**
 * Sara AI - Mode A: Chat Assistant Interface
 * Handles chat messaging, conversational context, markdown parsing, code copying,
 * suggested prompts, mic shortcut dictation, and conversation history.
 */

class SaraChat {
  constructor() {
    this.currentConversationId = null;
    this.isGenerating = false;
    this.lastUserMessage = '';
    this.attachedFile = null;

    this.initElements();
    this.initEventListeners();
    this.initSpeechShortcut();
    this.loadInitialConversation();
  }

  initElements() {
    this.chatFeed = document.getElementById('chat-feed');
    this.messagesContainer = document.getElementById('messages-container');
    this.welcomeCard = document.getElementById('welcome-card');
    this.typingIndicator = document.getElementById('typing-indicator');
    this.activeChatTitle = document.getElementById('active-chat-title');
    this.conversationList = document.getElementById('conversation-list');
    this.textarea = document.getElementById('chat-textarea');
    this.sendBtn = document.getElementById('send-msg-btn');
    this.clearInputBtn = document.getElementById('clear-input-btn');
    this.micQuickBtn = document.getElementById('mic-quick-btn');
    this.attachFileBtn = document.getElementById('attach-file-btn');
    this.fileUploadInput = document.getElementById('file-upload-input');
    this.attachmentPreviewBar = document.getElementById('attachment-preview-bar');
    this.previewFileName = document.getElementById('preview-file-name');
    this.previewFileSize = document.getElementById('preview-file-size');
    this.removeAttachmentBtn = document.getElementById('remove-attachment-btn');
    this.newChatBtn = document.getElementById('new-chat-btn');
    this.clearChatBtn = document.getElementById('clear-chat-btn');
    this.toggleSidebarBtn = document.getElementById('toggle-sidebar-btn');
    this.closeSidebarBtn = document.getElementById('close-sidebar-btn');
    this.chatSidebar = document.getElementById('chat-sidebar');
  }

  initEventListeners() {
    // Auto-expanding textarea
    this.textarea.addEventListener('input', () => {
      this.textarea.style.height = 'auto';
      this.textarea.style.height = Math.min(this.textarea.scrollHeight, 180) + 'px';
    });

    // Enter to submit (Shift+Enter for newline)
    this.textarea.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this.handleSend();
      }
    });

    // Send button click
    this.sendBtn.addEventListener('click', () => this.handleSend());

    // Clear input button
    this.clearInputBtn.addEventListener('click', () => {
      this.textarea.value = '';
      this.textarea.style.height = 'auto';
      this.textarea.focus();
    });

    // New Chat button
    this.newChatBtn.addEventListener('click', () => this.startNewChat());

    // Clear Chat button
    this.clearChatBtn.addEventListener('click', () => this.clearCurrentChat());

    // Suggested prompt buttons
    document.querySelectorAll('.prompt-pill').forEach(btn => {
      btn.addEventListener('click', () => {
        if (btn.id === 'prompt-help-files') {
          const fileModal = document.getElementById('file-tools-modal');
          if (fileModal) fileModal.classList.remove('hidden');
        } else {
          const prompt = btn.getAttribute('data-prompt');
          if (prompt) {
            this.textarea.value = prompt;
            this.textarea.style.height = 'auto';
            this.textarea.style.height = Math.min(this.textarea.scrollHeight, 180) + 'px';
            this.handleSend();
          }
        }
      });
    });

    // Attachment handling
    this.attachFileBtn.addEventListener('click', () => this.fileUploadInput.click());
    this.fileUploadInput.addEventListener('change', () => this.handleFileSelected());
    this.removeAttachmentBtn.addEventListener('click', () => this.removeAttachment());

    // Sidebar conversation item clicks & delete delegation
    this.conversationList.addEventListener('click', (e) => {
      const deleteBtn = e.target.closest('.conv-delete-btn');
      if (deleteBtn) {
        e.stopPropagation();
        const convId = deleteBtn.getAttribute('data-id');
        this.deleteConversation(convId);
        return;
      }

      const item = e.target.closest('.conv-item');
      if (item) {
        const convId = item.getAttribute('data-id');
        if (convId && convId !== this.currentConversationId) {
          this.loadConversation(convId);
        }
      }
    });

    // Sidebar toggle for mobile/responsive
    if (this.toggleSidebarBtn) {
      this.toggleSidebarBtn.addEventListener('click', () => {
        this.chatSidebar.classList.toggle('open');
      });
    }
    if (this.closeSidebarBtn) {
      this.closeSidebarBtn.addEventListener('click', () => {
        this.chatSidebar.classList.remove('open');
      });
    }
  }

  initSpeechShortcut() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.lang = 'en-US';

      recognition.onstart = () => {
        this.micQuickBtn.style.color = '#ef4444';
        window.SaraApp.showToast('Listening... Speak into microphone', 'info');
      };

      recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        this.textarea.value = (this.textarea.value ? this.textarea.value + ' ' : '') + transcript;
        this.textarea.style.height = 'auto';
        this.textarea.style.height = Math.min(this.textarea.scrollHeight, 180) + 'px';
      };

      recognition.onerror = (event) => {
        this.micQuickBtn.style.color = '';
        window.SaraApp.showToast(`Speech recognition notice: ${event.error}`, 'error');
      };

      recognition.onend = () => {
        this.micQuickBtn.style.color = '';
      };

      this.micQuickBtn.addEventListener('click', () => {
        try {
          recognition.start();
        } catch (e) {
          recognition.stop();
        }
      });
    } else {
      this.micQuickBtn.addEventListener('click', () => {
        window.location.href = '/voice';
      });
    }
  }

  handleFileSelected() {
    if (this.fileUploadInput.files.length === 0) return;
    const file = this.fileUploadInput.files[0];
    this.attachedFile = file;
    this.previewFileName.textContent = file.name;
    this.previewFileSize.textContent = window.SaraFiles.formatBytes(file.size);
    this.attachmentPreviewBar.classList.remove('hidden');
  }

  removeAttachment() {
    this.attachedFile = null;
    this.fileUploadInput.value = '';
    this.attachmentPreviewBar.classList.add('hidden');
  }

  async loadInitialConversation() {
    const firstItem = this.conversationList.querySelector('.conv-item');
    if (firstItem) {
      const id = firstItem.getAttribute('data-id');
      await this.loadConversation(id);
    } else {
      await this.startNewChat(false);
    }
  }

  async startNewChat(focus = true) {
    try {
      const resp = await fetch('/api/history', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: 'New Conversation' })
      });
      const data = await resp.json();
      if (data.success) {
        this.currentConversationId = data.id;
        this.activeChatTitle.textContent = 'New Conversation';
        this.messagesContainer.innerHTML = '';
        this.welcomeCard.classList.remove('hidden');

        // Add to sidebar
        this.addConversationToSidebar(data.id, 'New Conversation', true);
        if (focus) this.textarea.focus();
      }
    } catch (e) {
      console.error('Error starting new chat:', e);
    }
  }

  async loadConversation(conversationId) {
    try {
      const resp = await fetch(`/api/history/${conversationId}`);
      if (!resp.ok) return;

      const data = await resp.json();
      if (!data.success || !data.conversation) return;

      this.currentConversationId = conversationId;
      this.activeChatTitle.textContent = data.conversation.title || 'Conversation';

      // Update active highlight in sidebar
      this.conversationList.querySelectorAll('.conv-item').forEach(item => {
        item.classList.toggle('active', item.getAttribute('data-id') === conversationId);
      });

      // Clear & render messages
      this.messagesContainer.innerHTML = '';
      const messages = data.conversation.messages || [];

      if (messages.length === 0) {
        this.welcomeCard.classList.remove('hidden');
      } else {
        this.welcomeCard.classList.add('hidden');
        messages.forEach(msg => {
          this.appendMessage(msg.role, msg.content, msg.metadata);
        });
        this.scrollToBottom();
      }
    } catch (e) {
      console.error('Error loading conversation:', e);
    }
  }

  async deleteConversation(conversationId) {
    if (!confirm('Are you sure you want to delete this conversation?')) return;

    try {
      const resp = await fetch(`/api/history/${conversationId}`, { method: 'DELETE' });
      if (resp.ok) {
        const item = this.conversationList.querySelector(`.conv-item[data-id="${conversationId}"]`);
        if (item) item.remove();

        if (this.currentConversationId === conversationId) {
          const next = this.conversationList.querySelector('.conv-item');
          if (next) {
            this.loadConversation(next.getAttribute('data-id'));
          } else {
            this.startNewChat();
          }
        }
        window.SaraApp.showToast('Conversation deleted.', 'info');
      }
    } catch (e) {
      console.error('Failed to delete conversation:', e);
    }
  }

  async clearCurrentChat() {
    if (!this.currentConversationId) return;
    this.messagesContainer.innerHTML = '';
    this.welcomeCard.classList.remove('hidden');
    window.SaraApp.showToast('Chat view cleared.', 'info');
  }

  addConversationToSidebar(id, title, setActive = false) {
    const emptyNotice = document.getElementById('empty-history-notice');
    if (emptyNotice) emptyNotice.remove();

    if (setActive) {
      this.conversationList.querySelectorAll('.conv-item').forEach(el => el.classList.remove('active'));
    }

    const item = document.createElement('div');
    item.className = `conv-item ${setActive ? 'active' : ''}`;
    item.setAttribute('data-id', id);
    item.innerHTML = `
      <span class="conv-icon">💬</span>
      <span class="conv-title" title="${title}">${title}</span>
      <button class="conv-delete-btn" title="Delete conversation" data-id="${id}">&times;</button>
    `;
    this.conversationList.prepend(item);
  }

  updateSidebarTitle(id, title) {
    const item = this.conversationList.querySelector(`.conv-item[data-id="${id}"] .conv-title`);
    if (item) {
      item.textContent = title;
      item.title = title;
    }
  }

  async handleSend() {
    const message = this.textarea.value.trim();
    if (!message && !this.attachedFile) return;
    if (this.isGenerating) return;

    this.welcomeCard.classList.add('hidden');

    // Handle attached file if user uploaded one
    if (this.attachedFile) {
      const file = this.attachedFile;
      this.removeAttachment();
      await this.processAttachedFile(file, message);
      return;
    }

    this.lastUserMessage = message;
    this.appendMessage('user', message);
    this.textarea.value = '';
    this.textarea.style.height = 'auto';
    this.scrollToBottom();

    // Show typing indicator
    this.setGenerating(true);

    try {
      const resp = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: message,
          conversation_id: this.currentConversationId
        })
      });

      const data = await resp.json();
      this.setGenerating(false);

      if (data.success) {
        if (!this.currentConversationId) {
          this.currentConversationId = data.conversation_id;
        }

        // If command triggered action
        if (data.action === 'navigate' && data.url) {
          window.location.href = data.url;
          return;
        }
        if (data.action === 'clear_conversation') {
          this.clearCurrentChat();
          return;
        }
        if (data.action === 'open_pdf_modal' || data.action === 'open_image_modal') {
          const modal = document.getElementById('file-tools-modal');
          if (modal) modal.classList.remove('hidden');
        }

        this.appendMessage('assistant', data.response, {
          provider: data.provider,
          model: data.model
        });

        // Update active title if this was first message
        if (this.activeChatTitle.textContent === 'New Conversation') {
          const newTitle = message.substring(0, 26) + (message.length > 26 ? '...' : '');
          this.activeChatTitle.textContent = newTitle;
          this.updateSidebarTitle(this.currentConversationId, newTitle);
        }
      } else {
        this.appendMessage('assistant', `⚠️ ${data.error || 'Sara AI encountered an issue processing your request.'}`);
      }
    } catch (err) {
      this.setGenerating(false);
      this.appendMessage('assistant', '⚠️ Network error: Could not reach Sara AI server. Please check your connection.');
    }

    this.scrollToBottom();
  }

  async processAttachedFile(file, userPrompt) {
    const isPdf = file.name.toLowerCase().endsWith('.pdf');
    const isImage = file.name.match(/\.(png|jpe?g|webp|bmp|gif)$/i);

    this.appendMessage('user', userPrompt || `Uploaded file: **${file.name}**`);
    this.setGenerating(true);

    try {
      let result;
      if (isPdf) {
        result = await window.SaraFiles.compressPdf(file);
      } else if (isImage) {
        result = await window.SaraFiles.enhanceImage(file);
      } else {
        // Normal upload
        const form = new FormData();
        form.append('file', file);
        const upResp = await fetch('/upload', { method: 'POST', body: form });
        result = await upResp.json();
      }

      this.setGenerating(false);

      if (result.success && (result.operation || result.download_url)) {
        const card = window.SaraFiles.createResultCard(result);
        const row = document.createElement('div');
        row.className = 'message-row assistant';
        row.innerHTML = `<div class="message-avatar">✨</div><div class="message-content-wrapper"></div>`;
        row.querySelector('.message-content-wrapper').appendChild(card);
        this.messagesContainer.appendChild(row);
      } else {
        this.appendMessage('assistant', `⚠️ File operation failed: ${result.error || 'Unknown error'}`);
      }
    } catch (e) {
      this.setGenerating(false);
      this.appendMessage('assistant', '⚠️ An error occurred while uploading or processing your file.');
    }
    this.scrollToBottom();
  }

  setGenerating(isGenerating) {
    this.isGenerating = isGenerating;
    if (isGenerating) {
      this.typingIndicator.classList.remove('hidden');
      this.sendBtn.disabled = true;
    } else {
      this.typingIndicator.classList.add('hidden');
      this.sendBtn.disabled = false;
    }
  }

  appendMessage(role, content, metadata = null) {
    const row = document.createElement('div');
    row.className = `message-row ${role}`;

    const avatar = role === 'user' ? '👤' : '✨';
    const parsedHtml = this.parseMarkdown(content);

    let actionsHtml = '';
    if (role === 'assistant') {
      actionsHtml = `
        <div class="message-actions">
          <button class="msg-action-btn copy-msg-btn" title="Copy response">
            📋 Copy
          </button>
          <button class="msg-action-btn regen-msg-btn" title="Regenerate response">
            🔄 Regenerate
          </button>
          ${metadata && metadata.provider ? `<span style="margin-left: auto;">${metadata.provider}</span>` : ''}
        </div>
      `;
    }

    row.innerHTML = `
      <div class="message-avatar">${avatar}</div>
      <div class="message-content-wrapper">
        <div class="message-bubble">${parsedHtml}</div>
        ${actionsHtml}
      </div>
    `;

    // Attach copy button logic
    const copyBtn = row.querySelector('.copy-msg-btn');
    if (copyBtn) {
      copyBtn.addEventListener('click', () => {
        navigator.clipboard.writeText(content).then(() => {
          window.SaraApp.showToast('Copied to clipboard!', 'success');
        });
      });
    }

    // Attach regenerate button logic
    const regenBtn = row.querySelector('.regen-msg-btn');
    if (regenBtn) {
      regenBtn.addEventListener('click', () => {
        if (this.lastUserMessage) {
          this.textarea.value = this.lastUserMessage;
          this.handleSend();
        }
      });
    }

    // Attach copy buttons inside code blocks
    row.querySelectorAll('.copy-code-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const codeText = btn.getAttribute('data-code') || '';
        navigator.clipboard.writeText(decodeURIComponent(codeText)).then(() => {
          btn.textContent = 'Copied!';
          setTimeout(() => btn.textContent = 'Copy', 2000);
        });
      });
    });

    this.messagesContainer.appendChild(row);
  }

  parseMarkdown(text) {
    if (!text) return '';

    // Escape raw HTML entities
    let escaped = text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

    // Fenced Code blocks ```lang\ncode```
    escaped = escaped.replace(/```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g, (match, lang, code) => {
      const language = lang || 'code';
      const encodedCode = encodeURIComponent(code);
      return `
        <pre><div class="code-header"><span>${language}</span><button class="copy-code-btn" data-code="${encodedCode}">Copy</button></div><code>${code.trim()}</code></pre>
      `;
    });

    // Inline code `code`
    escaped = escaped.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Headers
    escaped = escaped.replace(/^### (.*$)/gim, '<h4 style="margin: 10px 0 6px 0; font-size: 1rem; color: #f8fafc;">$1</h4>');
    escaped = escaped.replace(/^## (.*$)/gim, '<h3 style="margin: 12px 0 8px 0; font-size: 1.15rem; color: #f8fafc;">$1</h3>');
    escaped = escaped.replace(/^# (.*$)/gim, '<h2 style="margin: 14px 0 10px 0; font-size: 1.3rem; color: #f8fafc;">$1</h2>');

    // Bold **text**
    escaped = escaped.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

    // Italic *text*
    escaped = escaped.replace(/\*([^*]+)\*/g, '<em>$1</em>');

    // Blockquotes
    escaped = escaped.replace(/^> (.*$)/gim, '<blockquote style="border-left: 3px solid var(--accent-purple); padding-left: 10px; margin: 8px 0; color: #94a3b8;">$1</blockquote>');

    // Line breaks outside code blocks
    const paragraphs = escaped.split('\n\n').map(p => {
      if (p.startsWith('<pre') || p.startsWith('<h') || p.startsWith('<blockquote') || p.startsWith('<table')) {
        return p;
      }
      return `<p>${p.replace(/\n/g, '<br>')}</p>`;
    });

    return paragraphs.join('');
  }

  scrollToBottom() {
    this.chatFeed.scrollTop = this.chatFeed.scrollHeight;
  }
}

document.addEventListener('DOMContentLoaded', () => {
  window.saraChat = new SaraChat();
});
