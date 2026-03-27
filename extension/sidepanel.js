/**
 * Polpoo Agent - Side Panel Logic
 * Gestiona el chat, historial de conversación y comunicación con el backend.
 * Las credenciales de cada cliente viajan en cada petición y nunca se almacenan en el servidor.
 */

const messagesEl = document.getElementById('messages');
const welcomeEl = document.getElementById('welcome');
const inputEl = document.getElementById('input');
const sendBtn = document.getElementById('sendBtn');
const clearBtn = document.getElementById('clearBtn');
const settingsBtn = document.getElementById('settingsBtn');
const statusBar = document.getElementById('statusBar');
const notConfigured = document.getElementById('notConfigured');
const goToSettings = document.getElementById('goToSettings');

let conversationHistory = [];
let isLoading = false;
let backendUrl = '';
let polpooUsername = '';
let polpooPassword = '';

// ─── INICIALIZACIÓN ───────────────────────────────────────────────────────────

async function init() {
  // Leer de storage LOCAL (las credenciales nunca se sincronizan con la nube)
  const settings = await chrome.storage.local.get(['backendUrl', 'polpooUsername', 'polpooPassword']);
  backendUrl = settings.backendUrl || '';
  polpooUsername = settings.polpooUsername || '';
  polpooPassword = settings.polpooPassword || '';

  const isConfigured = backendUrl && polpooUsername && polpooPassword;

  if (!isConfigured) {
    messagesEl.style.display = 'none';
    document.querySelector('.input-area').style.display = 'none';
    notConfigured.style.display = 'flex';
  } else {
    checkConnection();
  }
}

async function checkConnection() {
  try {
    const resp = await fetch(`${backendUrl}/health`, { signal: AbortSignal.timeout(5000) });
    if (resp.ok) {
      showStatus('✅ Conectado', 'success', 2000);
    } else {
      showStatus('⚠️ Backend responde con error', 'error');
    }
  } catch {
    showStatus('❌ No se puede conectar al backend. Verifica la URL en configuración.', 'error');
  }
}

// ─── STATUS BAR ───────────────────────────────────────────────────────────────

function showStatus(message, type = 'warning', autohide = 0) {
  statusBar.textContent = message;
  statusBar.className = `status-bar visible ${type}`;
  if (autohide > 0) setTimeout(() => { statusBar.className = 'status-bar'; }, autohide);
}

function hideStatus() {
  statusBar.className = 'status-bar';
}

// ─── MENSAJES ─────────────────────────────────────────────────────────────────

function addMessage(role, content) {
  if (welcomeEl) welcomeEl.style.display = 'none';

  const div = document.createElement('div');
  div.className = `message ${role}`;

  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.innerHTML = formatMessage(content);

  div.appendChild(bubble);
  messagesEl.appendChild(div);
  scrollToBottom();
  return div;
}

function addTypingIndicator() {
  const div = document.createElement('div');
  div.className = 'message assistant typing-indicator';
  div.id = 'typing';
  div.innerHTML = `<div class="bubble"><div class="dots">
    <div class="dot"></div><div class="dot"></div><div class="dot"></div>
  </div></div>`;
  messagesEl.appendChild(div);
  scrollToBottom();
}

function removeTypingIndicator() {
  const el = document.getElementById('typing');
  if (el) el.remove();
}

function formatMessage(text) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/```([\s\S]*?)```/g, '<pre>$1</pre>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/\n/g, '<br>');
}

function scrollToBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

// ─── ENVÍO DE MENSAJE ─────────────────────────────────────────────────────────

async function sendMessage() {
  const text = inputEl.value.trim();
  if (!text || isLoading) return;

  if (!backendUrl || !polpooUsername || !polpooPassword) {
    showStatus('❌ Configura el backend y tus credenciales primero', 'error');
    return;
  }

  inputEl.value = '';
  inputEl.style.height = 'auto';
  isLoading = true;
  sendBtn.disabled = true;
  hideStatus();

  addMessage('user', text);
  conversationHistory.push({ role: 'user', content: text });
  addTypingIndicator();

  try {
    const response = await fetch(`${backendUrl}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        messages: conversationHistory,
        // Las credenciales viajan en cada petición, nunca se guardan en el servidor
        polpoo_username: polpooUsername,
        polpoo_password: polpooPassword,
      }),
      signal: AbortSignal.timeout(120000),
    });

    removeTypingIndicator();

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Error desconocido' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    const data = await response.json();
    conversationHistory.push({ role: 'assistant', content: data.response });
    addMessage('assistant', data.response);

  } catch (err) {
    removeTypingIndicator();
    let errorMsg = '❌ Error al conectar con el agente.';
    if (err.name === 'TimeoutError') errorMsg = '⏱️ Tiempo de espera agotado.';
    else if (err.message) errorMsg = `❌ ${err.message}`;
    addMessage('assistant', errorMsg);
    showStatus(errorMsg, 'error');
  } finally {
    isLoading = false;
    sendBtn.disabled = false;
    inputEl.focus();
  }
}

// ─── EVENTOS ──────────────────────────────────────────────────────────────────

inputEl.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
});

inputEl.addEventListener('input', () => {
  inputEl.style.height = 'auto';
  inputEl.style.height = Math.min(inputEl.scrollHeight, 120) + 'px';
});

sendBtn.addEventListener('click', sendMessage);

clearBtn.addEventListener('click', () => {
  conversationHistory = [];
  messagesEl.querySelectorAll('.message').forEach(m => m.remove());
  if (welcomeEl) welcomeEl.style.display = '';
  hideStatus();
});

settingsBtn.addEventListener('click', () => chrome.runtime.openOptionsPage());
goToSettings.addEventListener('click', () => chrome.runtime.openOptionsPage());

document.querySelectorAll('.suggestion-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    inputEl.value = btn.textContent.replace(/^[^\s]+\s/, '');
    sendMessage();
  });
});

init();
