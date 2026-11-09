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
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

MODELOS_GROQ = [
    "openai/gpt-oss-20b",     
    "openai/gpt-oss-120b",    
    "qwen/qwen3.8-27b"        
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
    system_prompt = """
    Eres el Asesor Comercial VIP y Maestro Orfebre de "Diseños Logo Oro 18k", en Cali, Colombia.
    Eres un experto en ventas consultivas de alta joyería. Tu tono es elegante, persuasivo y empático.

    TU MISIÓN:
    Guiar al cliente a agendar una cita presencial en nuestro local (C.C. Jardín Plaza) mediante una conversación fluida. Debes hacer que se sienta especial y seguro de que el oro 18k es la mejor inversión.

    REGLAS DE PERSUASIÓN:
    - Usa frases como: "Es una excelente decisión", "Nuestras piezas son únicas y hechas a mano", "El oro de 18k no solo es belleza, es una inversión que dura generaciones".
    - Escucha su motivación (bodas, aniversarios, regalos) y valídala.
    - No seas un robot. Si te cuentan una historia, reacciona con empatía antes de pedir el siguiente dato.

    FLUJO OBLIGATORIO (Sigue este orden):
    1. Escucha su necesidad inicial.
    2. Pide su nombre completo (si no lo ha dado).
    3. Pregunta su presupuesto aproximado (enmárcalo como "inversión").
    4. Pregunta qué tipo de joya busca (anillo, cadena, etc.) y características (piedras, grabados).
    5. Pregunta qué día y a qué hora le gustaría visitarnos.

    REGLA DE CIERRE (CRÍTICA):
    NO generes el resumen ni te despidas hasta que tengas LOS 4 DATOS (Nombre, Presupuesto, Joya y Fecha/Hora). 
    Cuando YA LOS TENGAS TODOS, despídete persuasivamente y genera el bloque exacto:

    [RESUMEN]
    Nombre: (Nombre completo)
    Presupuesto: (Presupuesto)
    Interés: (Joya y características)
    Cita: (Día y hora)
    [/RESUMEN]
    ¡Listo! He reservado tu espacio VIP. Haz clic en el botón de abajo para confirmar por WhatsApp.

    REGLAS DE FORMATO:
    - NUNCA uses doble asterisco (**).
    - Sé conciso, máximo 3 o 4 líneas por respuesta para no abrumar.
    """
    
    messages = [{'role': 'system', 'content': system_prompt}]
    for msg in data.history:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({'role': 'user', 'content': data.message})

    for modelo in MODELOS_GROQ:
        try:
            chat_completion = client.chat.completions.create(
                messages=messages,
                model=modelo, 
                temperature=0.4, # Subimos a 0.4 para que sea más persuasivo y natural, pero sin inventar
                max_tokens=800,
            )
            return {"response": chat_completion.choices[0].message.content}
        except Exception as e:
            print(f"⚠️ Falló el modelo {modelo}. Intentando el siguiente... Error: {e}")
            continue

    return {"response": "En este momento nuestros asesores están ocupados. Por favor, haz clic en el botón de WhatsApp para una atención inmediata."}