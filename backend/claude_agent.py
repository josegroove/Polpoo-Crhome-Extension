"""
Agente OpenAI con herramientas Polpoo.
Implementa el loop agéntico: GPT decide qué herramienta llamar,
el backend la ejecuta, el resultado vuelve a GPT hasta que responde al usuario.
"""
import json
import os
import asyncio
from openai import AsyncOpenAI
from polpoo_client import PolpooClient

openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ─── DEFINICIÓN DE HERRAMIENTAS (formato OpenAI function calling) ─────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "enviar_rutas",
            "description": (
                "Envía rutas de reparto a Polpoo con los puntos de entrega del día. "
                "Úsala cuando el usuario quiera planificar o cargar rutas."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Nombre de la sesión de rutas"},
                    "description": {"type": "string", "description": "Descripción de la sesión"},
                    "dateSession": {"type": "string", "description": "Fecha en formato YYYY-MM-DD"},
                    "deliveryPoints": {
                        "type": "array",
                        "description": "Lista de puntos de entrega",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "name": {"type": "string"},
                                "address": {"type": "string"},
                                "deliveryZoneId": {"type": "string"},
                                "coordinates": {
                                    "type": "object",
                                    "properties": {
                                        "latitude": {"type": "number"},
                                        "longitude": {"type": "number"},
                                    },
                                },
                                "demand": {"type": "integer"},
                                "volumetric": {"type": "number"},
                                "serviceTime": {"type": "integer"},
                                "phoneNumber": {"type": "string"},
                                "email": {"type": "string"},
                                "orderNumber": {"type": "string"},
                                "deliveryNotes": {"type": "string"},
                                "deliveryType": {"type": "string", "enum": ["shipment", "pickup"]},
                            },
                            "required": ["id", "name", "address", "deliveryZoneId"],
                        },
                    },
                },
                "required": ["name", "description", "dateSession", "deliveryPoints"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "enviar_albaranes",
            "description": "Envía albaranes de entrega con productos a Polpoo para clientes específicos.",
            "parameters": {
                "type": "object",
                "properties": {
                    "dateDeliveryStart": {"type": "string", "description": "Fecha en formato YYYY-MM-DD"},
                    "deliveryPoints": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "deliveryNotes": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "deliveryNoteCode": {"type": "string"},
                                            "products": {"type": "array", "items": {"type": "object"}},
                                            "totalPrice": {"type": "number"},
                                        },
                                        "required": ["deliveryNoteCode"],
                                    },
                                },
                            },
                            "required": ["id", "deliveryNotes"],
                        },
                    },
                },
                "required": ["dateDeliveryStart", "deliveryPoints"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "enviar_cobros",
            "description": "Envía facturas o cobros pendientes a clientes en Polpoo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "bills": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "deliveryPointId": {"type": "string"},
                                "code": {"type": "string"},
                                "total": {"type": "number"},
                                "archiveUrl": {"type": "string"},
                                "status": {"type": "integer", "enum": [1, 2]},
                            },
                            "required": ["deliveryPointId", "code", "total", "archiveUrl", "status"],
                        },
                    }
                },
                "required": ["bills"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_cobros",
            "description": "Consulta el estado de cobros y pagos de un cliente.",
            "parameters": {
                "type": "object",
                "properties": {
                    "delivery_point_id": {"type": "string"},
                    "code": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "obtener_orden_rutas",
            "description": "Obtiene el orden planificado de rutas para una fecha: chóferes, vehículos, puntos de entrega y horarios.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "Fecha en formato YYYY-MM-DD"}
                },
                "required": ["date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "seguimiento_rutas",
            "description": "Consulta el estado actual de entregas para una fecha. Puede filtrar por pedido, ruta o cliente.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {"type": "string"},
                    "order_number": {"type": "string"},
                    "route_id": {"type": "string"},
                    "client_id": {"type": "string"},
                },
                "required": ["date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "geolocalizacion_chofer",
            "description": "Obtiene la última posición GPS registrada de un chófer en reparto.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_number": {"type": "string"},
                    "name": {"type": "string"},
                    "username": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "maestro_clientes",
            "description": "Consulta la base de datos de clientes de Polpoo. Sin parámetros devuelve todos.",
            "parameters": {
                "type": "object",
                "properties": {
                    "client_id": {"type": "string"},
                    "name": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "listar_usuarios",
            "description": "Lista los usuarios de la cuenta Polpoo. Permite buscar por nombre, email o filtrar por tipo de usuario y perfil. Devuelve nombre, apellido, email, teléfono, perfil, tipo y último acceso.",
            "parameters": {
                "type": "object",
                "properties": {
                    "search": {"type": "string", "description": "Texto para buscar por nombre, email o apellido"},
                    "show_active": {"type": "boolean", "description": "true = solo activos, false = todos. Por defecto true"},
                    "profile_id": {"type": "string", "description": "ID de perfil para filtrar (opcional)"},
                    "user_type_id": {"type": "string", "description": "ID de tipo de usuario para filtrar (opcional)"},
                    "start": {"type": "integer", "description": "Índice de inicio para paginación (por defecto 0)"},
                    "length": {"type": "integer", "description": "Número de resultados a devolver (por defecto 50)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "tracking_evento",
            "description": "Registra un evento de tracking: 10=inicio ruta, 11=fin ruta, 1=entrega, 2=anulación.",
            "parameters": {
                "type": "object",
                "properties": {
                    "routeId": {"type": "string"},
                    "event": {"type": "integer", "enum": [1, 2, 10, 11]},
                    "clientId": {"type": "string"},
                    "comment": {"type": "string"},
                    "comments": {"type": "string"},
                    "detail": {"type": "string"},
                    "signatureTime": {"type": "string"},
                    "driverArrivalTime": {"type": "string"},
                },
                "required": ["routeId", "event"],
            },
        },
    },
]

SYSTEM_PROMPT = """Eres un asistente de operaciones logísticas integrado en Polpoo, software de planificación de rutas.
Tienes acceso directo a la API de Polpoo y puedes ejecutar acciones reales.

Capacidades:
- Enviar y gestionar rutas de reparto
- Gestionar albaranes con líneas de producto
- Enviar y consultar cobros/facturas
- Consultar seguimiento de entregas en tiempo real
- Localizar chóferes por GPS
- Consultar y buscar clientes
- Registrar eventos de tracking

Reglas:
- Responde siempre en español, de forma concisa y directa
- Cuando ejecutes una acción confirma el resultado claramente
- Si falta información crítica (ej: fecha para rutas), pregunta solo lo estrictamente necesario
- Para fechas relativas como "hoy" o "mañana", usa la fecha actual del sistema
- Ante errores de la API, explica qué salió mal en lenguaje claro, sin tecnicismos
"""


async def _execute_tool(tool_name: str, tool_input: dict, polpoo: PolpooClient) -> str:
    """Ejecuta la herramienta correspondiente usando el cliente Polpoo del usuario."""
    try:
        if tool_name == "enviar_rutas":
            result = await polpoo.enviar_rutas(tool_input)
        elif tool_name == "enviar_albaranes":
            result = await polpoo.enviar_albaranes(tool_input)
        elif tool_name == "enviar_cobros":
            result = await polpoo.enviar_cobros(tool_input["bills"])
        elif tool_name == "consultar_cobros":
            result = await polpoo.consultar_cobros(
                tool_input.get("delivery_point_id"),
                tool_input.get("code"),
            )
        elif tool_name == "obtener_orden_rutas":
            result = await polpoo.obtener_orden_rutas(tool_input["date"])
        elif tool_name == "seguimiento_rutas":
            result = await polpoo.seguimiento_rutas(
                tool_input["date"],
                tool_input.get("order_number"),
                tool_input.get("route_id"),
                tool_input.get("client_id"),
            )
        elif tool_name == "geolocalizacion_chofer":
            result = await polpoo.geolocalizacion_chofer(
                tool_input.get("order_number"),
                tool_input.get("name"),
                tool_input.get("username"),
            )
        elif tool_name == "maestro_clientes":
            result = await polpoo.maestro_clientes(
                tool_input.get("client_id"),
                tool_input.get("name"),
            )
        elif tool_name == "listar_usuarios":
            result = await polpoo.listar_usuarios(
                search=tool_input.get("search"),
                show_active=tool_input.get("show_active", True),
                profile_id=tool_input.get("profile_id"),
                user_type_id=tool_input.get("user_type_id"),
                start=tool_input.get("start", 0),
                length=tool_input.get("length", 50),
            )
        elif tool_name == "tracking_evento":
            result = await polpoo.tracking_evento(tool_input)
        else:
            result = {"error": f"Herramienta desconocida: {tool_name}"}

        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


# Máximo de caracteres por respuesta de herramienta (evita context overflow con listas enormes)
MAX_TOOL_RESULT_CHARS = 8000

def _truncate_tool_result(result: str) -> str:
    """Trunca resultados muy grandes para no superar el límite de contexto de OpenAI."""
    if len(result) <= MAX_TOOL_RESULT_CHARS:
        return result
    truncated = result[:MAX_TOOL_RESULT_CHARS]
    return truncated + f'\n\n[RESULTADO TRUNCADO — se muestran los primeros {MAX_TOOL_RESULT_CHARS} caracteres de {len(result)} totales]'


# Máximo de mensajes del historial que se envían a OpenAI (los más recientes)
MAX_HISTORY_MESSAGES = 20

def _trim_history(messages: list[dict]) -> list[dict]:
    """Mantiene solo los últimos N mensajes para no superar el contexto."""
    if len(messages) <= MAX_HISTORY_MESSAGES:
        return messages
    return messages[-MAX_HISTORY_MESSAGES:]


async def chat(messages: list[dict], polpoo_username: str, polpoo_password: str) -> str:
    """
    Loop agéntico principal con OpenAI.
    Crea un cliente Polpoo aislado por petición con las credenciales del usuario.
    Las credenciales nunca se almacenan en el servidor.
    """
    from datetime import date

    # Cliente Polpoo aislado para este usuario — sin estado compartido
    polpoo = PolpooClient(username=polpoo_username, password=polpoo_password)

    system_with_date = f"{SYSTEM_PROMPT}\n\nFecha actual del sistema: {date.today().isoformat()}"
    openai_messages = [{"role": "system", "content": system_with_date}] + _trim_history(messages)

    response = await openai_client.chat.completions.create(
        model="gpt-4o",
        tools=TOOLS,
        messages=openai_messages,
    )

    # ── Loop agéntico ──────────────────────────────────────────────────────────
    while response.choices[0].finish_reason == "tool_calls":
        assistant_message = response.choices[0].message
        openai_messages.append(assistant_message)

        tool_calls = assistant_message.tool_calls
        results = await asyncio.gather(*[
            _execute_tool(tc.function.name, json.loads(tc.function.arguments), polpoo)
            for tc in tool_calls
        ])

        # Añadir resultados truncados al historial
        for tc, result in zip(tool_calls, results):
            openai_messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": _truncate_tool_result(result),
            })

        response = await openai_client.chat.completions.create(
            model="gpt-4o",
            tools=TOOLS,
            messages=openai_messages,
        )

    return response.choices[0].message.content or "No se pudo generar una respuesta."
