const backendUrlInput = document.getElementById('backendUrl');
const polpooUsernameInput = document.getElementById('polpooUsername');
const polpooPasswordInput = document.getElementById('polpooPassword');
const saveBtn = document.getElementById('saveBtn');
const testBtn = document.getElementById('testBtn');
const togglePass = document.getElementById('togglePass');
const alertEl = document.getElementById('alert');

function showAlert(message, type) {
  alertEl.textContent = message;
  alertEl.className = `alert ${type} visible`;
  setTimeout(() => { alertEl.className = 'alert'; }, 4000);
}

// Mostrar/ocultar contraseña
togglePass.addEventListener('click', () => {
  const isPassword = polpooPasswordInput.type === 'password';
  polpooPasswordInput.type = isPassword ? 'text' : 'password';
  togglePass.textContent = isPassword ? '🙈' : '👁️';
});

// Cargar configuración guardada
async function loadSettings() {
  // Las credenciales se guardan en storage LOCAL (no sync) para que no salgan del dispositivo
  const settings = await chrome.storage.local.get(['backendUrl', 'polpooUsername', 'polpooPassword']);
  if (settings.backendUrl) backendUrlInput.value = settings.backendUrl;
  if (settings.polpooUsername) polpooUsernameInput.value = settings.polpooUsername;
  if (settings.polpooPassword) polpooPasswordInput.value = settings.polpooPassword;
}

// Guardar configuración
saveBtn.addEventListener('click', async () => {
  const url = backendUrlInput.value.trim().replace(/\/$/, '');
  const username = polpooUsernameInput.value.trim();
  const password = polpooPasswordInput.value;

  if (!url) { showAlert('❌ Introduce la URL del backend', 'error'); return; }
  if (!username) { showAlert('❌ Introduce tu usuario de Polpoo', 'error'); return; }
  if (!password) { showAlert('❌ Introduce tu contraseña de Polpoo', 'error'); return; }

  // Guardar en storage LOCAL (nunca se sincroniza con la nube de Google)
  await chrome.storage.local.set({ backendUrl: url, polpooUsername: username, polpooPassword: password });
  showAlert('✅ Configuración guardada correctamente', 'success');
});

// Probar conexión
testBtn.addEventListener('click', async () => {
  const url = backendUrlInput.value.trim().replace(/\/$/, '');
  if (!url) { showAlert('❌ Introduce la URL del backend primero', 'error'); return; }

  testBtn.textContent = 'Probando...';
  testBtn.disabled = true;
  try {
    const resp = await fetch(`${url}/health`, { signal: AbortSignal.timeout(8000) });
    if (resp.ok) {
      const data = await resp.json();
      showAlert(`✅ Conexión exitosa: ${data.service || 'ok'}`, 'success');
    } else {
      showAlert(`⚠️ El servidor respondió con error ${resp.status}`, 'error');
    }
  } catch (err) {
    showAlert(`❌ No se pudo conectar: ${err.message}`, 'error');
  } finally {
    testBtn.textContent = 'Probar conexión';
    testBtn.disabled = false;
  }
});

loadSettings();
