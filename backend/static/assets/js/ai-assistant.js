document.addEventListener('DOMContentLoaded', function() {
  const widget = document.getElementById('ai-assistant-widget');
  if (!widget) return;
  widget.innerHTML = `
    <div id="ai-assistant-bubble" style="position:fixed;bottom:90px;right:24px;z-index:9999;box-shadow:0 2px 8px rgba(0,0,0,0.2);background:#fff;border-radius:50%;padding:8px;cursor:pointer;transition:box-shadow 0.2s;display:flex;align-items:center;justify-content:center;width:56px;height:56px;">
      <img src="/static/assets/image/logo.png" width="32" style="display:block;margin:auto;"/>
    </div>
    <div id="ai-assistant-chatbox" style="position:fixed;bottom:160px;right:24px;width:350px;max-width:95vw;height:480px;max-height:80vh;display:flex;flex-direction:column;background:#181825;border-radius:16px;box-shadow:0 4px 24px rgba(0,0,0,0.25);overflow:hidden;z-index:10000;transform:scale(0);transition:transform 0.2s;">
      <div style="padding:16px; color:#fff; font-weight:bold; background:linear-gradient(90deg,#6c47ff,#ec4899);display:flex;align-items:center;justify-content:space-between;">
        <img src="/static/assets/image/logo.png" width="32" style="display:inline-block;margin-right:-60px;"/>
        <span>INEMI AI Assistant</span> <span id="close-ai-chat" style="cursor:pointer;font-size:22px;">&times;</span>
      </div>
      <div id="ai-chat-messages" style="flex:1;overflow-y:auto;padding:16px;background:#23233a;display:flex;flex-direction:column;gap:10px;"></div>
      <form id="ai-chat-form" class="d-flex align-items-center" style="gap:6px;padding:6px;background:#23233a;flex-wrap:nowrap;">
      <!-- Voice Button -->
      <button id="ai-voice-btn" type="button" style="flex:0 0 auto;width:42px;height:42px;border:none;border-radius:50%;background:linear-gradient(135deg,#6c47ff 0%,#ec4899 100%);color:#fff;display:flex;align-items:center;justify-content:center;font-size:20px;box-shadow:0 2px 8px #6c47ff33;transition:box-shadow 0.2s,background 0.2s;outline:none;cursor:pointer;">
        <svg id="ai-voice-icon" xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="none" viewBox="0 0 24 24"><path fill="currentColor" d="M12 16a4 4 0 0 0 4-4V7a4 4 0 1 0-8 0v5a4 4 0 0 0 4 4Zm6-4a1 1 0 1 1 2 0c0 4.08-3.06 7.44-7 7.93V22a1 1 0 1 1-2 0v-2.07c-3.94-.49-7-3.85-7-7.93a1 1 0 1 1 2 0c0 3.31 2.69 6 6 6s6-2.69 6-6Z"/></svg>
      </button>

      <!-- Input Field -->
      <input id="ai-chat-input" type="text" placeholder="Tulis pertanyaan..." style="flex:1;padding:10px 12px;border-radius:10px;border:none;background:#181825;color:#fff;font-size:15px;outline:none;min-width:0;"/>

      <!-- Send Button -->
      <button id="ai-send-btn" type="submit" style="flex:0 0 auto;padding:8px 14px;border:none;border-radius:10px;background:linear-gradient(90deg,#6c47ff,#ec4899);color:#fff;font-weight:600;display:flex;align-items:center;justify-content:center;font-size:18px;">
        <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" fill="none" viewBox="0 0 24 24"><path fill="currentColor" d="M2 21l21-9-21-9v7l15 2-15 2v7z"/></svg>
      </button>
    </form>

    </div>
  `;
  const bubble = document.getElementById('ai-assistant-bubble');
  const chatbox = document.getElementById('ai-assistant-chatbox');
  const closeBtn = document.getElementById('close-ai-chat');
  bubble.onclick = () => chatbox.style.transform = 'scale(1)';
  closeBtn.onclick = () => chatbox.style.transform = 'scale(0)';

  // Chat logic
  const form = document.getElementById('ai-chat-form');
  const input = document.getElementById('ai-chat-input');
  const messages = document.getElementById('ai-chat-messages');
  // Voice recognition (opsional, bisa diaktifkan jika ingin)
  // ... (kode voice recognition bisa ditambahkan jika ingin tetap ada)

  function addMessage({text, from}) {
    const msgDiv = document.createElement('div');
    msgDiv.style.display = 'flex';
    msgDiv.style.justifyContent = from === 'user' ? 'flex-end' : 'flex-start';
    // Tambahkan wrapper agar tombol bisa di kanan atas bubble
    const bubbleDiv = document.createElement('div');
    bubbleDiv.style.maxWidth = '75%';
    bubbleDiv.style.padding = '10px 14px';
    bubbleDiv.style.borderRadius = '14px';
    bubbleDiv.style.fontSize = '15px';
    bubbleDiv.style.lineHeight = '1.5';
    bubbleDiv.style.boxShadow = '0 2px 8px rgba(0,0,0,0.08)';
    bubbleDiv.style.background = from==='user'?'linear-gradient(90deg,#6c47ff,#ec4899)':'#23233a';
    bubbleDiv.style.color = from==='user'?'#fff':'#d1d5db';
    bubbleDiv.style.marginBottom = '2px';
    bubbleDiv.style.position = 'relative';
    bubbleDiv.innerHTML = `<b style="font-size:13px;">${from==='user'?'Anda':'AI'}</b><br>${text}`;
    // Jika dari AI, tambahkan tombol suara dan salin
    if(from === 'ai') {
      // Tombol suara
      const ttsBtn = document.createElement('button');
      ttsBtn.title = 'Dengarkan';
      ttsBtn.innerHTML = '<svg width="18" height="18" fill="currentColor" viewBox="0 0 16 16"><path d="M9 9.5a.5.5 0 0 1-.5.5h-2A.5.5 0 0 1 6 9.5v-3A.5.5 0 0 1 6.5 6h2a.5.5 0 0 1 .5.5v3z"/><path d="M11.536 14.01a.5.5 0 0 1-.707-.707A6.978 6.978 0 0 0 13 8a6.978 6.978 0 0 0-2.17-5.303.5.5 0 1 1 .707-.707A7.978 7.978 0 0 1 14 8a7.978 7.978 0 0 1-2.464 6.01z"/><path d="M10.354 12.354a.5.5 0 0 1-.708-.708A4.978 4.978 0 0 0 11 8a4.978 4.978 0 0 0-1.354-3.646.5.5 0 1 1 .708-.708A5.978 5.978 0 0 1 12 8a5.978 5.978 0 0 1-1.646 4.354z"/></svg>';
      ttsBtn.style.position = 'absolute';
      ttsBtn.style.top = '6px';
      ttsBtn.style.right = '36px';
      ttsBtn.style.background = 'none';
      ttsBtn.style.border = 'none';
      ttsBtn.style.cursor = 'pointer';
      ttsBtn.style.color = '#a855f7';
      ttsBtn.style.padding = '2px';
      ttsBtn.style.zIndex = '2';
      ttsBtn.onmouseover = () => ttsBtn.style.color = '#ec4899';
      ttsBtn.onmouseout = () => ttsBtn.style.color = '#a855f7';
      ttsBtn.onclick = async function(e) {
        e.stopPropagation();
        ttsBtn.disabled = true;
        ttsBtn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
        try {
          const res = await fetch('/api/tts-elevenlabs', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text })
          });
          if (!res.ok) throw new Error('Gagal generate suara');
          const blob = await res.blob();
          const url = URL.createObjectURL(blob);
          const audio = new Audio(url);
          audio.play();
          audio.onended = () => {
            URL.revokeObjectURL(url);
          };
        } catch (err) {
          alert('Gagal memutar suara: ' + err.message);
        }
        ttsBtn.disabled = false;
        ttsBtn.innerHTML = '<svg width="18" height="18" fill="currentColor" viewBox="0 0 16 16"><path d="M9 9.5a.5.5 0 0 1-.5.5h-2A.5.5 0 0 1 6 9.5v-3A.5.5 0 0 1 6.5 6h2a.5.5 0 0 1 .5.5v3z"/><path d="M11.536 14.01a.5.5 0 0 1-.707-.707A6.978 6.978 0 0 0 13 8a6.978 6.978 0 0 0-2.17-5.303.5.5 0 1 1 .707-.707A7.978 7.978 0 0 1 14 8a7.978 7.978 0 0 1-2.464 6.01z"/><path d="M10.354 12.354a.5.5 0 0 1-.708-.708A4.978 4.978 0 0 0 11 8a4.978 4.978 0 0 0-1.354-3.646.5.5 0 1 1 .708-.708A5.978 5.978 0 0 1 12 8a5.978 5.978 0 0 1-1.646 4.354z"/></svg>';
      };
      bubbleDiv.appendChild(ttsBtn);
      // Tombol salin
      const copyBtn = document.createElement('button');
      copyBtn.title = 'Salin';
      copyBtn.innerHTML = '<svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M10 1.5A1.5 1.5 0 0 1 11.5 3v1h-1V3a.5.5 0 0 0-.5-.5h-6A.5.5 0 0 0 3 3v10a.5.5 0 0 0 .5.5H6v1H3.5A1.5 1.5 0 0 1 2 13.5v-10A1.5 1.5 0 0 1 3.5 2h6z"/><path d="M5 5.5A1.5 1.5 0 0 1 6.5 4h6A1.5 1.5 0 0 1 14 5.5v7A1.5 1.5 0 0 1 12.5 14h-6A1.5 1.5 0 0 1 5 12.5v-7zm1.5-.5a.5.5 0 0 0-.5.5v7a.5.5 0 0 0 .5.5h6a.5.5 0 0 0 .5-.5v-7a.5.5 0 0 0-.5-.5h-6z"/></svg>';
      copyBtn.style.position = 'absolute';
      copyBtn.style.top = '6px';
      copyBtn.style.right = '6px';
      copyBtn.style.background = 'none';
      copyBtn.style.border = 'none';
      copyBtn.style.cursor = 'pointer';
      copyBtn.style.color = '#a855f7';
      copyBtn.style.padding = '2px';
      copyBtn.style.zIndex = '2';
      copyBtn.onmouseover = () => copyBtn.style.color = '#ec4899';
      copyBtn.onmouseout = () => copyBtn.style.color = '#a855f7';
      copyBtn.onclick = function(e) {
        e.stopPropagation();
        navigator.clipboard.writeText(text);
        copyBtn.innerHTML = '<svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M13.485 1.929a.75.75 0 0 1 1.06 1.06l-8.25 8.25a.75.75 0 0 1-1.06 0l-3.25-3.25a.75.75 0 1 1 1.06-1.06l2.72 2.72 7.72-7.72z"/></svg>';
        setTimeout(()=>{
          copyBtn.innerHTML = '<svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16"><path d="M10 1.5A1.5 1.5 0 0 1 11.5 3v1h-1V3a.5.5 0 0 0-.5-.5h-6A.5.5 0 0 0 3 3v10a.5.5 0 0 0 .5.5H6v1H3.5A1.5 1.5 0 0 1 2 13.5v-10A1.5 1.5 0 0 1 3.5 2h6z"/><path d="M5 5.5A1.5 1.5 0 0 1 6.5 4h6A1.5 1.5 0 0 1 14 5.5v7A1.5 1.5 0 0 1 12.5 14h-6A1.5 1.5 0 0 1 5 12.5v-7zm1.5-.5a.5.5 0 0 0-.5.5v7a.5.5 0 0 0 .5.5h6a.5.5 0 0 0 .5-.5v-7a.5.5 0 0 0-.5-.5h-6z"/></svg>';
        }, 1500);
      };
      bubbleDiv.appendChild(copyBtn);
    }
    msgDiv.appendChild(bubbleDiv);
    messages.appendChild(msgDiv);
    messages.scrollTop = messages.scrollHeight;
  }

  form.onsubmit = async (e) => {
    e.preventDefault();
    const userMsg = input.value;
    if (!userMsg) return;
    addMessage({text: userMsg, from: 'user'});
    input.value = '';
    // Kirim ke backend
    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({message: userMsg})
      });
      const data = await res.json();
      addMessage({text: data.response, from: 'ai'});
    } catch (err) {
      addMessage({text: 'Gagal terhubung ke server.', from: 'ai'});
    }
  };

  const voiceBtn = document.getElementById('ai-voice-btn');
  const voiceIcon = document.getElementById('ai-voice-icon');
  let recognizing = false;
  let recognition;
  if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();
    recognition.lang = 'id-ID';
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.onstart = function() {
      recognizing = true;
      voiceBtn.style.background = 'linear-gradient(90deg,#ec4899,#6c47ff)';
      voiceBtn.style.boxShadow = '0 0 0 4px #ec489955, 0 2px 8px #6c47ff33';
      voiceIcon.setAttribute('fill', '#fff');
    };
    recognition.onend = function() {
      recognizing = false;
      voiceBtn.style.background = 'linear-gradient(135deg,#6c47ff 0%,#ec4899 100%)';
      voiceBtn.style.boxShadow = '0 2px 8px #6c47ff33';
      voiceIcon.setAttribute('fill', '#fff');
    };
    recognition.onerror = function(e) {
      recognizing = false;
      voiceBtn.style.background = 'linear-gradient(135deg,#6c47ff 0%,#ec4899 100%)';
      voiceBtn.style.boxShadow = '0 2px 8px #6c47ff33';
      voiceIcon.setAttribute('fill', '#fff');
    };
    recognition.onresult = function(event) {
      const transcript = event.results[0][0].transcript;
      if (transcript) {
        input.value = transcript;
        // Otomatis submit form
        form.requestSubmit();
      }
    };
    voiceBtn.onmouseover = function() {
      if (!recognizing) voiceBtn.style.boxShadow = '0 0 0 2px #6c47ff99, 0 2px 8px #6c47ff33';
    };
    voiceBtn.onmouseout = function() {
      if (!recognizing) voiceBtn.style.boxShadow = '0 2px 8px #6c47ff33';
    };
    voiceBtn.onclick = function(e) {
      e.preventDefault();
      if (recognizing) {
        recognition.stop();
      } else {
        recognition.start();
      }
    };
  } else {
    voiceBtn.style.display = 'none';
  }
}); 