"""
Polpoo Agent - Backend API
FastAPI app que recibe mensajes del chat junto con las credenciales del cliente
y los procesa con GPT-4o + Polpoo API.
Las credenciales NUNCA se almacenan en el servidor.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Literal
import os

from claude_agent import chat

app = FastAPI(
    title="Polpoo AI Agent",
    description="Backend del agente IA para Polpoo",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── MODELOS ──────────────────────────────────────────────────────────────────

class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str

class ChatRequest(BaseModel):
    messages: list[Message]
    polpoo_username: str
    polpoo_password: str

class ChatResponse(BaseModel):
    response: str


# ─── ENDPOINTS ────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "polpoo-agent"}


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    if not request.messages:
        raise HTTPException(status_code=400, detail="El historial de mensajes no puede estar vacío")
    if not request.polpoo_username or not request.polpoo_password:
        raise HTTPException(status_code=400, detail="Las credenciales de Polpoo son requeridas")

    try:
        messages = [{"role": m.role, "content": m.content} for m in request.messages]
        response_text = await chat(
            messages=messages,
            polpoo_username=request.polpoo_username,
            polpoo_password=request.polpoo_password,
        )
        return ChatResponse(response=response_text)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")
