# Polpoo AI Agent — Instrucciones de instalación

## ¿Qué es esto?

Una extensión de Chrome con un panel lateral de chat. El usuario escribe en lenguaje natural y el agente llama automáticamente a la API de Polpoo para ejecutar la acción.

**Ejemplo:**
> "¿Qué rutas hay para mañana?"
> → El agente consulta la API y responde con el listado de rutas planificadas.

---

## Arquitectura

```
[Chrome - Side Panel]  →  [Backend FastAPI en Railway]  →  [API de Polpoo]
                                      ↕
                              [Claude Sonnet API]
```

---

## PASO 1 — Desplegar el backend en Railway

### 1.1 Crear cuenta y nuevo proyecto

1. Ve a [railway.app](https://railway.app) y crea una cuenta
2. Crea un nuevo proyecto → "Deploy from GitHub repo"
3. Sube la carpeta `backend/` a un repositorio de GitHub (o usa "Deploy from local")

### 1.2 Variables de entorno en Railway

En tu proyecto de Railway, ve a **Variables** y añade:

| Variable | Valor |
|----------|-------|
| `ANTHROPIC_API_KEY` | Tu API key de Anthropic (empieza por `sk-ant-`) |
| `POLPOO_USERNAME` | El email del usuario técnico de Polpoo |
| `POLPOO_PASSWORD` | La contraseña del usuario técnico de Polpoo |

### 1.3 Obtener la URL del backend

Una vez desplegado, Railway te dará una URL del tipo:
```
https://polpoo-agent-production.up.railway.app
```
**Guarda esta URL, la necesitarás en el Paso 3.**

---

## PASO 2 — Instalar la extensión en Chrome

1. Abre Chrome y ve a `chrome://extensions/`
2. Activa el **Modo desarrollador** (arriba a la derecha)
3. Haz clic en **"Cargar extensión sin empaquetar"**
4. Selecciona la carpeta `extension/` de este proyecto
5. La extensión aparecerá con el icono de Polpoo en la barra de Chrome

---

## PASO 3 — Configurar la extensión

1. Haz clic derecho en el icono de la extensión → **"Opciones"**
2. Introduce la URL de tu backend de Railway (ej: `https://polpoo-agent-production.up.railway.app`)
3. Haz clic en **"Probar conexión"** para verificar que todo funciona
4. Guarda la configuración

---

## PASO 4 — Usar el agente

1. Haz clic en el icono de la extensión en Chrome → se abre el panel lateral
2. Escribe lo que quieres hacer en lenguaje natural
3. El agente ejecuta las acciones automáticamente

---

## Funciones disponibles

| Función | Ejemplo de uso |
|---------|----------------|
| Enviar rutas | "Envía estas rutas para mañana: cliente A en Madrid, cliente B en Alcalá" |
| Enviar albaranes | "Registra el albarán 123 para el cliente 1050 con estos productos..." |
| Enviar cobros | "Marca la factura F-2024-001 del cliente 0061 como cobrada" |
| Consultar cobros | "¿Qué cobros tiene pendientes el cliente 1052?" |
| Orden de rutas | "¿Qué rutas hay planificadas para hoy?" |
| Seguimiento entregas | "¿Cuál es el estado de las entregas de hoy?" |
| Geolocalización chófer | "¿Dónde está el chófer Víctor ahora mismo?" |
| Maestro de clientes | "Búscame el cliente Bar Xaloc" |
| Tracking eventos | "Registra la entrega al cliente C001 en la ruta 67daf077..." |

---

## Estructura del proyecto

```
polpoo-agent/
├── backend/
│   ├── main.py              ← FastAPI app (endpoint /chat y /health)
│   ├── polpoo_client.py     ← Cliente de la API de Polpoo (todas las funciones)
│   ├── claude_agent.py      ← Loop agéntico Claude + herramientas Polpoo
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── railway.toml
│   └── .env.example
└── extension/
    ├── manifest.json        ← Chrome MV3
    ├── background.js        ← Abre el side panel al clicar
    ├── sidepanel.html       ← UI del chat
    ├── sidepanel.js         ← Lógica del chat
    ├── options.html         ← Página de configuración
    └── options.js
```

---

## Desarrollo local (opcional)

Si quieres probar el backend en local antes de subir a Railway:

```bash
cd backend
cp .env.example .env
# Edita .env con tus credenciales reales

pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Luego en la extensión pon `http://localhost:8000` como URL del backend.

---

## Preguntas frecuentes

**¿El agente tiene acceso a mis datos de Polpoo?**
Sí, accede usando las credenciales que configures. Las credenciales se guardan en el servidor (variables de entorno de Railway), nunca en la extensión.

**¿Cuánto cuesta?**
Railway tiene un plan gratuito suficiente para empezar. El coste real es la API de Anthropic (Claude), que se paga por uso (~$0.003 por mensaje típico).

**¿Puedo añadir más funciones?**
Sí: añade un método en `polpoo_client.py`, define la herramienta en `TOOLS` dentro de `claude_agent.py`, y añade el caso en `_execute_tool`. El agente la usará automáticamente.
