from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List
from groq import Groq
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import sqlite3
import urllib.parse
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ==========================================
# CONFIGURACIÓN DE GROQ
# ==========================================
CLAVES_GROQ = [
    os.getenv("GROQ_API_KEY"),
    os.getenv("GROQ_API_KEY_2") 
]
CLAVES_GROQ = [k for k in CLAVES_GROQ if k]

MODELOS_GROQ = [
    "llama-3.3-70b-versatile", # El más inteligente y estable actualmente
    "llama-3.1-8b-instant",    # El más rápido como respaldo
    "openai/gpt-oss-20b"       # Tercer respaldo
]

def init_db():
    conn = sqlite3.connect("pedidos.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT, telefono TEXT, interes TEXT,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

@app.api_route("/health", methods=["GET", "HEAD"])
async def health_check():
    return {"status": "ok"}

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.post("/procesar_pedido")
@limiter.limit("5/minute")
async def procesar_pedido(request: Request, nombre: str = Form(...), telefono: str = Form(...), interes: str = Form(...)):
    conn = sqlite3.connect("pedidos.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO pedidos (nombre, telefono, interes) VALUES (?, ?, ?)", (nombre, telefono, interes))
    conn.commit()
    conn.close()
    
    mensaje = f"Hola, soy {nombre}. Me gustaría agendar una cita VIP. Mi número es {telefono} y estoy interesado(a) en: {interes}."
    numero_whatsapp = "573174827958" 
    url_whatsapp = f"https://wa.me/{numero_whatsapp}?text={urllib.parse.quote(mensaje)}"
    return RedirectResponse(url=url_whatsapp, status_code=303)

class Mensaje(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: List[Mensaje]

@app.post("/chat")
@limiter.limit("20/minute")
async def chat_with_ai(request: Request, data: ChatRequest):
    # --- DIAGNÓSTICO EN LOGS ---
    if not CLAVES_GROQ:
        print("❌ ERROR CRÍTICO: No se encontró la variable GROQ_API_KEY en Render.")
        return {"response": "Error de configuración en el servidor. (Falta API Key)."}
    else:
        print(f"✅ Intentando conectar a Groq usando la clave que empieza con: {CLAVES_GROQ[0][:8]}...")

    system_prompt = """
    Eres el Asesor Comercial VIP y Maestro Orfebre de "Diseños Logo Oro 18k", en Cali, Colombia.
    Eres un experto en ventas consultivas de alta joyería. Tu tono es elegante, empático, persuasivo y muy conversacional.
    NO eres un robot. Eres como un amigo experto que asesora con calma.

    TU MISIÓN:
    Guiar al cliente a agendar una cita presencial en nuestro local (C.C. Jardín Plaza), pero ANTES debes ayudarle a elegir su joya ideal mediante una conversación fluida.

    FLUJO DE ASESORÍA:
    1. Escucha su motivación y valídala con empatía.
    2. Ofrécele opciones (Tipo de oro: Amarillo/Blanco/Rosado, Tipo de joya, Grabados, Piedras).
    3. Pídele su nombre completo.
    4. Pregunta su presupuesto aproximado (enmárcalo como "inversión").
    5. Pregunta qué día y a qué hora le gustaría visitarnos.

    REGLAS DE ORO:
    - NUNCA cierres la conversación bruscamente. Responde sus dudas antes de pedir otro dato.
    - Destaca que el Oro 18k es la mejor inversión y no se oxida.
    - Haz máximo 1 o 2 preguntas por mensaje.

    REGLA DE CIERRE:
    SOLO cuando tengas los 4 datos (Nombre, Presupuesto, Joya, Fecha/Hora), despídete con:
    "¡Listo! He reservado tu espacio VIP. Haz clic en el botón de abajo para confirmar por WhatsApp."
    Y genera el bloque:
    [RESUMEN]
    Nombre: (Nombre)
    Presupuesto: (Presupuesto)
    Interés: (Joya y detalles)
    Cita: (Día y hora)
    [/RESUMEN]
    
    NUNCA uses doble asterisco (**).
    """
    
    messages = [{'role': 'system', 'content': system_prompt}]
    for msg in data.history:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({'role': 'user', 'content': data.message})

    # SISTEMA DE RESPALDO
    for clave in CLAVES_GROQ:
        client = Groq(api_key=clave)
        for modelo in MODELOS_GROQ:
            try:
                chat_completion = client.chat.completions.create(
                    messages=messages,
                    model=modelo, 
                    temperature=0.5, 
                    max_tokens=800,
                )
                print(f"✅ Éxito con el modelo: {modelo}")
                return {"response": chat_completion.choices[0].message.content}
            except Exception as e:
                # ESTO ES LO QUE VERÁS EN LOS LOGS SI FALLA
                print(f"⚠️ Falló con el modelo {modelo}. Error: {e}")
                continue 

    return {"response": "En este momento nuestros asesores están ocupados. Por favor, haz clic en el botón de WhatsApp para una atención inmediata."}