# ==============================================================================
# 🤖 NEXA · OPTION A: ALL-IN-ONE DEPLOYMENT (Render)
# ==============================================================================
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import os, re, json, httpx, base64
from typing import Optional
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Nexa All-In-One")

# 🌐 MAGIC CORS FIX: Serve the frontend directly from this same server!
@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

# ==============================================================================
# 📚 KNOWLEDGE BASE & CLIENT DATA
# ==============================================================================
BOT_NAME = "Nexa"
CLIENT_EMAIL = "admin@outsourcejobsda.com"
CLIENT_CONTACTS = "Dr. Favour Anthony & Amara Dupuis"

SERVICES = {
    "bpo": {"name": "Business Process Outsourcing (BPO)", "plain": "We handle your admin tasks so your team can focus on growth.", "keywords": ["outsource", "bpo", "admin"]},
    "recruitment": {"name": "Recruitment & Talent Matching", "plain": "We find the right people for your team.", "keywords": ["recruit", "hire", "talent", "eor"]},
    "training": {"name": "Corporate Training & Seminars", "plain": "Quarterly training with UWI Cave Hill School of Business.", "keywords": ["training", "seminar", "uwi", "cave hill"]},
    "logistics": {"name": "Logistics & Supply Chain", "plain": "Trucking, import-export, and getting goods where they need to go.", "keywords": ["logistics", "trucking", "import", "export"]},
    "resilience": {"name": "Resilience & Sustainability Planning", "plain": "Climate action and business continuity planning.", "keywords": ["resilience", "climate", "sustainability"]},
    "consulting": {"name": "Strategic Consulting", "plain": "One-on-one expert advice to grow your business.", "keywords": ["consult", "strategy", "advice"]}
}

AUTHORITY_TRIGGERS = ["price", "cost", "fee", "how much", "quote", "my case", "my application", "eligible", "passport", "nin", "bank account", "contract", "guarantee"]

# ==============================================================================
# 🛡️ THE THREE-AXIS ROUTER & PRIVACY
# ==============================================================================
def check_authority(msg: str) -> bool:
    return not any(trigger in msg.lower() for trigger in AUTHORITY_TRIGGERS)

def detect_service(msg: str) -> Optional[str]:
    for key, data in SERVICES.items():
        if any(kw in msg.lower() for kw in data["keywords"]):
            return key
    return None

def redact_pii(text: str) -> str:
    for label, pattern in {"phone": r"\b\d{3}[-.\s]?\d{4}\b", "email": r"\b[\w\.-]+@[\w\.-]+\.\w+\b", "nin": r"\b\d{9}\b"}.items():
        text = re.sub(pattern, f"[REDACTED:{label}]", text)
    return text

# ==============================================================================
# 🧠 AI BRAIN (Google Gemini)
# ==============================================================================
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
gemini_model = genai.GenerativeModel("gemini-2.0-flash")

def get_ai_response(user_msg: str, service: Optional[str]) -> str:
    safe_msg = redact_pii(user_msg)
    
    if not check_authority(safe_msg):
        return f"I appreciate you reaching out! 🙏 For pricing, personal data, or specific case details, our team needs to handle this personally. Please email {CLIENT_EMAIL} or contact {CLIENT_CONTACTS} to book a consultation."
    
    svc = SERVICES.get(service, {"name": "our services", "plain": "Please visit our website for details."}) if service else {"name": "our services", "plain": "Please specify which service you need help with."}
    
    prompt = f"""You are {BOT_NAME} for Outsource Development Studio in Dominica.
    GOLDEN RULE: You are the GPS. The human is the driver. NEVER quote prices or handle personal data.
    TOPIC: {svc['name']}. Plain English: {svc['plain']}.
    TONE: Friendly, professional, and concise. Add a 💛 emoji."""
    
    try:
        return gemini_model.generate_content(prompt + "\n\nUser: " + safe_msg).text
    except Exception as e:
        return f"😅 I had a hiccup connecting to the AI. (Error: {e})"

# ==============================================================================
# 🌐 API ENDPOINT
# ==============================================================================
class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
async def chat(request: ChatRequest):
    service = detect_service(request.message)
    response_text = get_ai_response(request.message, service)
    return {"response": response_text, "escalated": not check_authority(request.message)}

@app.get("/health")
async def health():
    return {"status": "online", "bot": BOT_NAME}
