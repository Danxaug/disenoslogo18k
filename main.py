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

# Límite de peticiones (Seguridad contra spam)
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
    Eres un experto en ventas consultivas de alta joyería. Tu tono es elegante, empático, persuasivo y muy conversacional.
    NO eres un robot. Eres como un amigo experto que asesora con calma.

    TU MISIÓN:
    Guiar al cliente a agendar una cita presencial en nuestro local (C.C. Jardín Plaza), pero ANTES debes ayudarle a elegir su joya ideal mediante una conversación fluida.

    FLUJO DE ASESORÍA (No lo hagas como un formulario, hazlo natural):
    1. Escucha su motivación (bodas, aniversarios, regalos) y valídala con empatía.
    2. Si el cliente quiere profundizar, ofrécele opciones de:
       - Tipo de oro: Amarillo, Blanco o Rosado.
       - Tipo de joya: Anillos (solitario, con piedras), Cadenas (cubana, barbada), Pulseras, Aretes, etc.
       - Detalles especiales: Grabados, tejidos especiales, tipo de piedra (diamante, esmeralda, etc.).
    3. Pídele su nombre completo (si no lo ha dado) para personalizar la atención.
    4. Pregunta su presupuesto aproximado (enmárcalo como "inversión").
    5. Pregunta qué día y a qué hora le gustaría visitarnos.

    REGLAS DE ORO:
    - NUNCA cierres la conversación bruscamente. Si el cliente hace una pregunta, respóndela antes de pedirle otro dato.
    - Si el cliente dice "quiero más asesoría" o "cuéntame más", dale detalles de nuestros materiales, la durabilidad del oro 18k y opciones de personalización.
    - Destaca que el Oro 18k es la mejor inversión y no se oxida.
    - Haz máximo 1 o 2 preguntas por mensaje para no abrumar. Deja que el cliente hable, habla en millones de pesos 2.000.000, 5.0000.0000, etc.

    REGLA DE CIERRE (CRÍTICA):
    SOLO cuando ya tengas los 4 datos (Nombre, Presupuesto, Tipo de joya con detalles, y Fecha/Hora), despídete con esta frase EXACTA al final de tu mensaje:
    "¡Listo! He reservado tu espacio VIP. Haz clic en el botón de abajo para confirmar por WhatsApp."
    Y justo antes de esa frase, genera el bloque de resumen:

    [RESUMEN]
    Nombre: (Nombre completo)
    Presupuesto: (Presupuesto)
    Interés: (Joya, tipo de oro, grabados, etc.)
    Cita: (Día y hora)
    [/RESUMEN]
    
    NUNCA uses doble asterisco (**).
    """
    
    messages = [{'role': 'system', 'content': system_prompt}]
    for msg in data.history:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({'role': 'user', 'content': data.message})

    # Sistema de respaldo anti-errores
    for modelo in MODELOS_GROQ:
        try:
            chat_completion = client.chat.completions.create(
                messages=messages,
                model=modelo, 
                temperature=0.5, # Subimos un poco la temperatura para que sea más conversacional y menos rígido
                max_tokens=800,
            )
            return {"response": chat_completion.choices[0].message.content}
        except Exception as e:
            print(f"⚠️ Falló el modelo {modelo}. Intentando el siguiente... Error: {e}")
            continue

    return {"response": "En este momento nuestros asesores están ocupados. Por favor, haz clic en el botón de WhatsApp para una atención inmediata."}