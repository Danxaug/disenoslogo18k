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
# CONFIGURACIÓN DE GROQ (CORREGIDO PARA VERCEL)
# ==========================================
# Vercel usa GROQ_API_KEY, no GROQ_KEY
CLAVES_GROQ = [
    os.getenv("GROQ_API_KEY"),
    os.getenv("GROQ_KEY"),  # Respaldo por si usaste ese nombre
    os.getenv("GROQ_API_KEY_2") 
]
CLAVES_GROQ = [k for k in CLAVES_GROQ if k]

MODELOS_GROQ = [
    "llama-3.3-70b-versatile", 
    "llama-3.1-8b-instant",    
    "openai/gpt-oss-20b"       
]

# Base de datos en memoria para Vercel (los datos se pierden al reiniciar)
DB_PATH = ":memory:" 

def init_db():
    conn = sqlite3.connect(DB_PATH)
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
    conn = sqlite3.connect(DB_PATH)
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
        print("❌ ERROR CRÍTICO: No se encontró GROQ_API_KEY ni GROQ_KEY en Vercel.")
        return {"response": "Error de configuración del servidor. Por favor contáctanos por WhatsApp."}
    else:
        print(f"✅ Conectando a Groq con clave: {CLAVES_GROQ[0][:8]}...")

    system_prompt = """
    Eres el Asesor Comercial VIP y Maestro Orfebre de "Diseños Logo Oro 18k", en Cali, Colombia.
    Tu tono es elegante, empático y muy conversacional. NO eres un robot.

    TU MISIÓN:
    Guiar al cliente a agendar una cita en C.C. Jardín Plaza, ayudándole primero a elegir su joya ideal.

    FLUJO:
    1. Valida su motivación con empatía.
    2. Ofrece opciones (oro amarillo/blanco/rosado, tipo de joya, grabados).
    3. Pide nombre completo.
    4. Pregunta presupuesto ("inversión").
    5. Pregunta día/hora preferida.

    REGLAS:
    - Máximo 1-2 preguntas por mensaje.
    - Destaca que el Oro 18k no se oxida.
    - NUNCA uses asteriscos (**).

    CIERRE (solo con los 4 datos):
    "¡Listo! He reservado tu espacio VIP. Haz clic abajo para confirmar por WhatsApp."
    Y agrega: [RESUMEN] Nombre: X, Presupuesto: Y, Interés: Z, Cita: W [/RESUMEN]
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
                print(f"✅ Éxito con modelo: {modelo}")
                return {"response": chat_completion.choices[0].message.content}
            except Exception as e:
                print(f"⚠️ Falló modelo {modelo}: {e}")
                continue 

    return {"response": "Nuestros asesores están ocupados. Haz clic en WhatsApp para atención inmediata."}