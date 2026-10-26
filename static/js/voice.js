/**
 * Sara AI - Mode B: Voice Assistant Interface
 * Implements 5 distinct voice states, circular canvas audio visualizer,
 * MediaRecorder audio capture, SpeechRecognition backend pipeline,
 * pyttsx3 audio playback, and Web Speech API synthesis fallback.
 */

class SaraVoice {
  constructor() {
    this.state = 'idle'; // 'idle', 'listening', 'processing', 'speaking', 'error'
    this.mediaRecorder = null;
    this.audioChunks = [];
    this.audioContext = null;
    this.analyser = null;
    this.micStream = null;
    this.isMuted = false;
    this.animationFrameId = null;

    this.initElements();
    this.initCanvas();
    this.initEventListeners();
    this.setState('idle');
  }

  initElements() {
    this.micToggleBtn = document.getElementById('mic-toggle-btn');
    this.micIcon = document.getElementById('mic-icon');
    this.statePill = document.getElementById('voice-state-pill');
    this.stateText = document.getElementById('voice-state-text');
    this.canvas = document.getElementById('voice-canvas');
    this.userSpeechCard = document.getElementById('user-speech-card');
    this.userSpeechText = document.getElementById('user-speech-text');
    this.assistantSpeechCard = document.getElementById('assistant-speech-card');
    this.assistantSpeechText = document.getElementById('assistant-speech-text');
    this.errorCard = document.getElementById('voice-error-card');
    this.errorMessage = document.getElementById('voice-error-message');
    this.retryBtn = document.getElementById('voice-retry-btn');
    this.stopSpeakingBtn = document.getElementById('stop-speaking-btn');
    this.muteToggleBtn = document.getElementById('mute-toggle-btn');
    this.muteIcon = document.getElementById('mute-icon');
    this.muteLabel = document.getElementById('mute-label');
    this.audioPlayerBar = document.getElementById('audio-player-bar');
    this.audioElement = document.getElementById('sara-audio-element');

    this.pulseRing1 = document.getElementById('pulse-ring-1');
    this.pulseRing2 = document.getElementById('pulse-ring-2');
    this.pulseRing3 = document.getElementById('pulse-ring-3');
  }

  initEventListeners() {
    this.micToggleBtn.addEventListener('click', () => this.handleMicToggle());
    this.stopSpeakingBtn.addEventListener('click', () => this.stopSpeaking());
    this.retryBtn.addEventListener('click', () => this.startListening());

    this.muteToggleBtn.addEventListener('click', () => {
      this.isMuted = !this.isMuted;
      this.muteIcon.textContent = this.isMuted ? '🔇' : '🔊';
      this.muteLabel.textContent = this.isMuted ? 'Muted' : 'Audio On';
      if (this.audioElement) this.audioElement.muted = this.isMuted;
      if (this.isMuted && window.speechSynthesis) {
        window.speechSynthesis.cancel();
      }
    });

    if (this.audioElement) {
      this.audioElement.addEventListener('ended', () => {
        this.setState('idle');
      });
      this.audioElement.addEventListener('error', () => {
        this.setState('idle');
      });
    }
  }

  initCanvas() {
    this.ctx = this.canvas.getContext('2d');
    this.startCanvasAnimation();
  }

  setState(newState, errorMsg = '') {
    this.state = newState;

    // Reset classes
    this.micToggleBtn.className = `mic-orb-btn state-${newState}`;
    this.statePill.className = `state-pill state-${newState}`;
    
    // Rings
    [this.pulseRing1, this.pulseRing2, this.pulseRing3].forEach(ring => {
      if (ring) {
        ring.className = `pulse-ring ${ring.id.replace('pulse-', '')} state-${newState}`;
      }
    });

    // Handle states
    switch (newState) {
      case 'idle':
        this.stateText.textContent = 'Tap the microphone to talk to Sara.';
        this.micIcon.textContent = '🎙️';
        this.stopSpeakingBtn.disabled = true;
        this.errorCard.classList.add('hidden');
        break;

      case 'listening':
        this.stateText.textContent = 'Listening...';
        this.micIcon.textContent = '🔴';
        this.stopSpeakingBtn.disabled = false;
        this.errorCard.classList.add('hidden');
        break;

      case 'processing':
        this.stateText.textContent = 'Sara is thinking...';
        this.micIcon.textContent = '⏳';
        this.stopSpeakingBtn.disabled = false;
        break;

      case 'speaking':
        this.stateText.textContent = 'Sara is speaking...';
        this.micIcon.textContent = '🔊';
        this.stopSpeakingBtn.disabled = false;
        break;

      case 'error':
        this.stateText.textContent = 'Voice interaction error';
        this.micIcon.textContent = '⚠️';
        this.errorMessage.textContent = errorMsg || 'Could not process audio. Please try again.';
        this.errorCard.classList.remove('hidden');
        this.stopSpeakingBtn.disabled = true;
        break;
    }
  }

  async handleMicToggle() {
    if (this.state === 'listening') {
      this.stopListening();
    } else if (this.state === 'speaking') {
      this.stopSpeaking();
    } else {
      await this.startListening();
    }
  }

  async startListening() {
    // If speaking, stop playback first
    this.stopSpeaking();

    // Check for getUserMedia support
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      this.fallbackWebSpeech();
      return;
    }

    try {
      this.audioChunks = [];
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      this.micStream = stream;

      // Setup audio analyzer for visualizer
      try {
        const AudioContext = window.AudioContext || window.webkitAudioContext;
        this.audioContext = new AudioContext();
        const source = this.audioContext.createMediaStreamSource(stream);
        this.analyser = this.audioContext.createAnalyser();
        this.analyser.fftSize = 64;
        source.connect(this.analyser);
      } catch (e) {
        console.warn('AudioContext visualization setup warning:', e);
      }

      // Setup MediaRecorder
      const options = { mimeType: 'audio/webm' };
      if (!MediaRecorder.isTypeSupported('audio/webm')) {
        delete options.mimeType;
      }

      this.mediaRecorder = new MediaRecorder(stream, options);

      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          this.audioChunks.push(event.data);
        }
      };

      this.mediaRecorder.onstop = () => {
        this.cleanupMicStream();
        if (this.audioChunks.length > 0) {
          const mime = this.mediaRecorder.mimeType || 'audio/webm';
          const audioBlob = new Blob(this.audioChunks, { type: mime });
          this.sendAudioForProcessing(audioBlob);
        }
      };

      this.mediaRecorder.start();
      this.setState('listening');

      // Auto-stop after 10 seconds of listening max
      this.listeningTimeout = setTimeout(() => {
        if (this.state === 'listening') {
          this.stopListening();
        }
      }, 10000);

    } catch (err) {
      console.error('Microphone access denied or failed:', err);
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        this.setState('error', 'Microphone permission denied. Please allow microphone access in your browser settings.');
      } else {
        // Try Web Speech API fallback
        this.fallbackWebSpeech();
      }
    }
  }

  stopListening() {
    if (this.listeningTimeout) clearTimeout(this.listeningTimeout);

    if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
      this.mediaRecorder.stop();
      this.setState('processing');
    } else {
      this.setState('idle');
    }
  }

  cleanupMicStream() {
    if (this.micStream) {
      this.micStream.getTracks().forEach(track => track.stop());
      this.micStream = null;
    }
    if (this.audioContext && this.audioContext.state !== 'closed') {
      this.audioContext.close().catch(() => {});
      this.audioContext = null;
      this.analyser = null;
    }
  }

  fallbackWebSpeech() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      this.setState('error', 'Audio recording is not supported in this browser. Please use Google Chrome, Edge, or Firefox.');
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = 'en-US';
    recognition.interimResults = false;

    recognition.onstart = () => {
      this.setState('listening');
    };

    recognition.onresult = (event) => {
      const text = event.results[0][0].transcript;
      this.setState('processing');
      this.sendTextForProcessing(text);
    };

    recognition.onerror = (event) => {
      this.setState('error', `Speech recognition error: ${event.error}`);
    };

    recognition.onend = () => {
      if (this.state === 'listening') {
        this.setState('idle');
      }
    };

    try {
      recognition.start();
    } catch (e) {
      this.setState('error', 'Could not initialize speech recognition.');
    }
  }

  async sendAudioForProcessing(audioBlob) {
    this.setState('processing');

    const formData = new FormData();
    formData.append('audio', audioBlob, 'voice_input.webm');

    try {
      const resp = await fetch('/api/voice/interact', {
        method: 'POST',
        body: formData
      });

      const data = await resp.json();
      if (data.success) {
        this.displayInteraction(data.recognized_text, data.response_text, data.audio_url, data.use_browser_tts);
      } else {
        this.setState('error', data.error || 'Sara could not recognize speech. Please try again.');
      }
    } catch (err) {
      this.setState('error', 'Network error connecting to Sara AI voice service.');
    }
  }

  async sendTextForProcessing(text) {
    this.setState('processing');

    const formData = new FormData();
    formData.append('text', text);

    try {
      const resp = await fetch('/api/voice/interact', {
        method: 'POST',
        body: formData
      });

      const data = await resp.json();
      if (data.success) {
        this.displayInteraction(data.recognized_text, data.response_text, data.audio_url, data.use_browser_tts);
      } else {
        this.setState('error', data.error || 'Error processing response.');
      }
    } catch (err) {
      this.setState('error', 'Network error generating voice reply.');
    }
  }

  displayInteraction(recognizedText, responseText, audioUrl, useBrowserTTS) {
    // Show recognized user query
    this.userSpeechText.textContent = recognizedText;
    this.userSpeechCard.classList.remove('hidden');

    // Show assistant response
    this.assistantSpeechText.textContent = responseText;
    this.assistantSpeechCard.classList.remove('hidden');

    // Speak response
    if (this.isMuted) {
      this.setState('idle');
      return;
    }

    if (audioUrl) {
      // Play pyttsx3 WAV file
      this.setState('speaking');
      this.audioPlayerBar.classList.remove('hidden');
      this.audioElement.src = audioUrl;
      this.audioElement.play().catch(e => {
        console.warn('Autoplay prevented, falling back to browser TTS:', e);
        this.speakWithBrowser(responseText);
      });
    } else if (useBrowserTTS || window.speechSynthesis) {
      this.speakWithBrowser(responseText);
    } else {
      this.setState('idle');
    }
  }

  speakWithBrowser(text) {
    if (!window.speechSynthesis) {
      this.setState('idle');
      return;
    }

    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'en-US';
    utterance.rate = 1.0;

    // Pick a natural voice if available
    const voices = window.speechSynthesis.getVoices();
    const naturalVoice = voices.find(v => v.lang.startsWith('en') && (v.name.includes('Natural') || v.name.includes('Female') || v.name.includes('Samantha') || v.name.includes('Zira')));
    if (naturalVoice) utterance.voice = naturalVoice;

    utterance.onstart = () => {
      this.setState('speaking');
    };

    utterance.onend = () => {
      this.setState('idle');
    };

    utterance.onerror = () => {
      this.setState('idle');
    };

    window.speechSynthesis.speak(utterance);
  }

  stopSpeaking() {
    if (this.audioElement) {
      this.audioElement.pause();
      this.audioElement.currentTime = 0;
    }
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    if (this.state === 'speaking' || this.state === 'processing') {
      this.setState('idle');
    }
  }

  startCanvasAnimation() {
    let phase = 0;

    const render = () => {
      this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

      const cx = this.canvas.width / 2;
      const cy = this.canvas.height / 2;
      phase += 0.04;

      if (this.state === 'listening' && this.analyser) {
        // Draw real frequency audio bars/waves
        const dataArray = new Uint8Array(this.analyser.frequencyBinCount);
        this.analyser.getByteFrequencyData(dataArray);

        const count = 32;
        const radius = 80;
        this.ctx.save();
        this.ctx.translate(cx, cy);

        for (let i = 0; i < count; i++) {
          const angle = (i / count) * Math.PI * 2;
          const val = dataArray[i % dataArray.length] / 255;
          const barHeight = 8 + val * 45;

          const x1 = Math.cos(angle) * radius;
          const y1 = Math.sin(angle) * radius;
          const x2 = Math.cos(angle) * (radius + barHeight);
          const y2 = Math.sin(angle) * (radius + barHeight);

          this.ctx.beginPath();
          this.ctx.moveTo(x1, y1);
          this.ctx.lineTo(x2, y2);
          this.ctx.strokeStyle = `rgba(239, 68, 68, ${0.4 + val * 0.6})`;
          this.ctx.lineWidth = 3;
          this.ctx.lineCap = 'round';
          this.ctx.stroke();
        }
        this.ctx.restore();

      } else if (this.state === 'speaking') {
        // Draw rhythmic sound waves
        const radius = 85 + Math.sin(phase * 2) * 8;
        this.ctx.beginPath();
        this.ctx.arc(cx, cy, radius, 0, Math.PI * 2);
        this.ctx.strokeStyle = 'rgba(16, 185, 129, 0.4)';
        this.ctx.lineWidth = 3;
        this.ctx.stroke();

        this.ctx.beginPath();
        this.ctx.arc(cx, cy, radius + 15, 0, Math.PI * 2);
        this.ctx.strokeStyle = 'rgba(6, 182, 212, 0.25)';
        this.ctx.lineWidth = 2;
        this.ctx.stroke();

      } else if (this.state === 'processing') {
        // Rotating spinner glow
        this.ctx.save();
        this.ctx.translate(cx, cy);
        this.ctx.rotate(phase);
        this.ctx.beginPath();
        this.ctx.arc(0, 0, 85, 0, Math.PI * 1.4);
        this.ctx.strokeStyle = 'rgba(245, 158, 11, 0.7)';
        this.ctx.lineWidth = 4;
        this.ctx.lineCap = 'round';
        this.ctx.stroke();
        this.ctx.restore();
      }

      this.animationFrameId = requestAnimationFrame(render);
    };

    render();
  }
}

document.addEventListener('DOMContentLoaded', () => {
  window.saraVoice = new SaraVoice();
});
