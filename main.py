# --- IMPORTS: Bringing in the tools we need ---
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import re
import csv
from typing import Optional, Dict
from datetime import datetime
import google.generativeai as genai
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
app = FastAPI(title="Nexa AI Navigator")

# Mount assets folder (Safe fallback if directory is missing)
try:
    app.mount("/assets", StaticFiles(directory="assets"), name="assets")
except Exception:
    pass 

# --- CONFIG & CONSTANTS ---
BOT_NAME = "Nexa"
CLIENT_EMAIL = "hello@outsourcedom.com" 
CLIENT_CONTACTS = "our booking form"

# Services Database
SERVICES = {
    "bpo": {"name": "BPO Services", "plain": "Business Process Outsourcing, customer support, and back-office operations.", "keywords": ["bpo", "outsourcing", "call center", "support"]},
    "recruitment": {"name": "Recruitment", "plain": "Talent acquisition, staffing, and HR consulting.", "keywords": ["hire", "recruitment", "staffing", "jobs", "talent"]},
    "uwi": {"name": "UWI Cave Hill Training", "plain": "Professional development and academic partnerships with UWI.", "keywords": ["uwi", "training", "cave hill", "courses", "education"]},
    "logistics": {"name": "Logistics", "plain": "Supply chain, freight, and local delivery coordination.", "keywords": ["logistics", "shipping", "freight", "supply chain", "delivery"]},
    "resilience": {"name": "Resilience Planning", "plain": "Climate adaptation, disaster recovery, and sustainable business continuity.", "keywords": ["resilience", "climate", "disaster", "sustainability", "continuity"]}
}

# ==============================================================================
# 🛡️ AXIS 1 & 3: AUTHORITY, TERRITORY & DISTRESS (The Red Lines)
# ==============================================================================
AUTHORITY_TRIGGERS = ["price", "cost", "how much", "quote", "my case", "my application", "am i eligible", "my balance"]

# Day 14: Distress Triggers (Break-Glass Protocol)
DISTRESS_TRIGGERS = {
    "grief":      ["passed away", "died", "funeral", "lost my", "she's gone", "he's gone"],
    "panic":      ["can't breathe", "can't cope", "help now", "emergency"],
    "self_harm":  ["hurt myself", "end it", "no way out"],
    "aggrieved":  ["nobody listens", "you people never", "sick of this"]
}

ESCALATION_PATHS = {
    "grief":     "our Bereavement Support Partner",
    "panic":     "Emergency Services (911 / 999)",
    "self_harm": "the National Crisis Hotline",
    "aggrieved": "our Client Relations Desk"
}

def check_authority(msg: str) -> bool:
    """Returns True if the message is SAFE for AI to answer."""
    return not any(trigger in msg.lower() for trigger in AUTHORITY_TRIGGERS)

def detect_distress(msg: str) -> Optional[str]:
    """Scans for distress keywords. If found, triggers Break-Glass protocol."""
    m = msg.lower()
    for category, words in DISTRESS_TRIGGERS.items():
        if any(w in m for w in words):
            return category
    return None

def detect_service(msg: str) -> Optional[str]:
    for key, data in SERVICES.items():
        if any(kw in msg.lower() for kw in data["keywords"]):
            return key
    return None

def detect_register(msg: str) -> str:
    m = msg.lower()
    if any(w in m for w in ["died", "passed away", "funeral", "loss"]): return "bereaved"
    if any(w in m for w in ["asap", "urgent", "emergency", "now"]): return "urgent"
    if any(w in m for w in ["regarding", "kindly", "please advise"]): return "professional"
    return "warm"

# 🔒 PRIVACY REDACTION (Day 11)
def redact_pii(text: str) -> str:
    """Redacts PII before sending to AI."""
    pii_patterns = {
        "phone": r"\b\d{3}[-.\s]?\d{4}\b",
        "email": r"\b[\w\.-]+@[\w\.-]+\.\w+\b",
        "nin": r"\b\d{9}\b"
    }
    for label, pattern in pii_patterns.items():
        text = re.sub(pattern, f"[REDACTED:{label}]", text)
    return text

# ==============================================================================
# 🧠 AI BRAIN: Grok (Primary) + Gemini (Fallback)
# ==============================================================================
# Grok API (xAI) - OpenAI Compatible
GROK_API_KEY = os.getenv("GROK_API_KEY")
grok_client = None
if GROK_API_KEY:
    grok_client = OpenAI(api_key=GROK_API_KEY, base_url="https://api.x.ai/v1")

# Google Gemini API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
gemini_model = None
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel("gemini-2.0-flash")

# Day 7: TCRDEI Prompt Template
def build_tcrdei_prompt(service_data: dict, register: str) -> str:
    tone_hints = {
        "warm": "TONE: Friendly, encouraging, simple words. Add a 💛 emoji.",
        "professional": "TONE: Polished, concise, respectful. No slang.",
        "urgent": "TONE: Fast, direct, action-oriented. Use bullet points.",
        "bereaved": "TONE: Open with gentle condolences. Explain gently. Max 2 sentences of facts."
    }
    
    return f"""
[T] You are {BOT_NAME}, an AI Navigator for Outsource Development Studio in Dominica.
[C] Context: User is asking about {service_data['name']}. Plain English explanation: {service_data['plain']}. 
    Ethical Rule: You are the GPS, the human is the driver. NEVER quote prices, guess facts, or handle PII.
[R] Reference: Always guide them to book a consultation for specific case details.
[D] Success = The user feels understood, informed on the basics, and safe.
[E] Before answering, check: does this satisfy [D] and respect the Ethical Rule?
[I] If unsure, ask ONE clarifying question.
{tone_hints.get(register, tone_hints['warm'])}
"""

def call_llm(prompt: str, user_msg: str) -> str:
    """Smart LLM Router: Tries Grok first, falls back to Gemini."""
    safe_msg = redact_pii(user_msg)
    
    # 1. Try Grok (xAI)
    if grok_client:
        try:
            response = grok_client.chat.completions.create(
                model="grok-beta", # Free/Preview tier model
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": safe_msg}
                ],
                temperature=0.4
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"⚠️ Grok API failed: {e}. Falling back to Gemini...")
            
    # 2. Fallback to Gemini
    if gemini_model:
        try:
            full_prompt = f"{prompt}\n\nUser: {safe_msg}"
            return gemini_model.generate_content(full_prompt).text
        except Exception as e:
            print(f"⚠️ Gemini API failed: {e}.")
            
    # 3. Ultimate Fallback
    return f"I'm currently having trouble connecting to my AI brain. Please reach out to {CLIENT_EMAIL} for immediate assistance!"

# Day 9: Bug Logging
def log_bug(input_str: str, error: str, axis_tag: str = "none"):
    """Logs critical errors for the QA team."""
    with open("bug_log.csv", "a", newline="") as f:
        w = csv.writer(f)
        w.writerow([datetime.utcnow().isoformat(), input_str[:50], error, axis_tag])

# ==============================================================================
# 🌐 API ENDPOINTS
# ==============================================================================
class ChatRequest(BaseModel):
    message: str
    session_id: str = "default" # To track journey state

# Day 14: Agentic Journey State Machine
JOURNEY_STEPS = ["greeting", "identify_need", "collect_facts", "offer_next_step", "confirm_close"]
session_states: Dict[str, int] = {}

@app.post("/chat")
async def chat(request: ChatRequest):
    msg = request.message
    session_id = request.session_id
    
    # 1. DISTRESS CHECK (Break-Glass Protocol - Day 14)
    distress = detect_distress(msg)
    if distress:
        target = ESCALATION_PATHS.get(distress, "a human agent")
        # 2-second SLA: Skip LLM, return immediate empathetic response
        return {
            "response": f"I hear you, and I am so sorry. Let me connect you with {target} right now. You don't have to handle this alone.",
            "escalated": True,
            "distress": True,
            "register": "bereaved",
            "service": None
        }

    # 2. AUTHORITY CHECK
    if not check_authority(msg):
        return {
            "response": f"I appreciate you reaching out! 🙏 For pricing, personal data, or specific case details, our team needs to handle this personally. Please email {CLIENT_EMAIL} or use our booking form.",
            "escalated": True,
            "distress": False,
            "register": "professional",
            "service": None
        }

    # 3. JOURNEY STATE TRACKING
    current_step = session_states.get(session_id, 0)
    if current_step < len(JOURNEY_STEPS) - 1:
        session_states[session_id] = current_step + 1

    # 4. CLASSIFY
    register = detect_register(msg)
    service_key = detect_service(msg)
    svc = SERVICES.get(service_key, {"name": "our services", "plain": "Please specify which service you need help with."}) if service_key else {"name": "our services", "plain": "Please specify which service you need help with."}

    # 5. GENERATE RESPONSE (Smart Router)
    prompt = build_tcrdei_prompt(svc, register)
    
    try:
        response_text = call_llm(prompt, msg)
    except Exception as e:
        log_bug(msg, str(e), "llm_crash")
        response_text = "😅 I had a slight hiccup connecting to my brain. Please give me a moment and try again!"

    return {
        "response": response_text, 
        "escalated": False,
        "distress": False,
        "register": register,
        "service": service_key,
        "journey_step": JOURNEY_STEPS[session_states.get(session_id, 0)]
    }

# Day 11: Document Reading / Vision Skeleton
@app.post("/upload")
async def upload_document(file: UploadFile = File(...), register: str = "warm"):
    """Skeleton for document upload. Redacts PII and summarizes."""
    try:
        contents = await file.read()
        raw_text = contents.decode('utf-8', errors='ignore') 
        safe_text = redact_pii(raw_text)
        
        summary = f"I've reviewed your document safely. I redacted any personal info like phone numbers or NINs. It looks like it's about general business operations."
        return {"summary": summary, "redactions_applied": safe_text.count("[REDACTED")}
    except Exception as e:
        log_bug("file_upload", str(e), "vision_api")
        raise HTTPException(status_code=500, detail="Could not process document safely.")

@app.get("/", response_class=HTMLResponse)
async def root():
    return "<h1>Nexa AI Backend is Running 🤖</h1><p>Use the frontend interface to chat.</p>"
