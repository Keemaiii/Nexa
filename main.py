# --- IMPORTS: Bringing in the tools we need ---
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import re
import csv
import uuid # To generate unique message IDs for the rating system
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
    return not any(trigger in msg.lower() for trigger in AUTHORITY_TRIGGERS)

def detect_distress(msg: str) -> Optional[str]:
    m = msg.lower()
    for category, words in DISTRESS_TRIGGERS.items():
        if any(w in m for w in words): return category
    return None

def detect_service(msg: str) -> Optional[str]:
    for key, data in SERVICES.items():
        if any(kw in msg.lower() for kw in data["keywords"]): return key
    return None

def detect_register(msg: str) -> str:
    m = msg.lower()
    if any(w in m for w in ["died", "passed away", "funeral", "loss"]): return "bereaved"
    if any(w in m for w in ["asap", "urgent", "emergency", "now"]): return "urgent"
    if any(w in m for w in ["regarding", "kindly", "please advise"]): return "professional"
    return "warm"

# 🔒 PRIVACY REDACTION (Day 11)
def redact_pii(text: str) -> str:
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
GROK_API_KEY = os.getenv("GROK_API_KEY")
grok_client = OpenAI(api_key=GROK_API_KEY, base_url="https://api.x.ai/v1") if GROK_API_KEY else None

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel("gemini-2.0-flash") if GEMINI_API_KEY else None

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
    safe_msg = redact_pii(user_msg)
    if grok_client:
        try:
            response = grok_client.chat.completions.create(
                model="grok-beta", 
                messages=[{"role": "system", "content": prompt}, {"role": "user", "content": safe_msg}],
                temperature=0.4
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"⚠️ Grok API failed: {e}. Falling back to Gemini...")
            
    if gemini_model:
        try:
            return gemini_model.generate_content(f"{prompt}\n\nUser: {safe_msg}").text
        except Exception as e:
            print(f"⚠️ Gemini API failed: {e}.")
            
    return f"I'm currently having trouble connecting to my AI brain. Please reach out to {CLIENT_EMAIL} for immediate assistance!"

# ==============================================================================
# 📊 RATINGS & LOGGING (Client Requirement: Thumbs Up/Down)
# ==============================================================================
# Aligns with ECCU Camp Day 9 (Bug Hunter) & Day 15 (Feedback Capture)
RATINGS_FILE = "ratings.csv"

def init_ratings_log():
    """Creates the CSV header if the file doesn't exist."""
    if not os.path.exists(RATINGS_FILE):
        with open(RATINGS_FILE, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["timestamp", "message_id", "session_id", "rating", "comment", "bot_response_snippet"])

init_ratings_log()

def log_rating(message_id: str, session_id: str, rating: str, comment: str, bot_response: str):
    """Appends a user rating to the CSV for the Product Owner to analyze."""
    with open(RATINGS_FILE, "a", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            datetime.utcnow().isoformat(timespec="seconds"),
            message_id,
            session_id,
            rating,
            comment,
            bot_response[:150] # Truncate to keep CSV clean
        ])

def log_bug(input_str: str, error: str, axis_tag: str = "none"):
    with open("bug_log.csv", "a", newline="") as f:
        w = csv.writer(f)
        w.writerow([datetime.utcnow().isoformat(), input_str[:50], error, axis_tag])

# ==============================================================================
# 🌐 API ENDPOINTS
# ==============================================================================
class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"

class RatingRequest(BaseModel):
    message_id: str
    session_id: str
    rating: str  # "up" or "down"
    response_text: str
    comment: Optional[str] = ""

JOURNEY_STEPS = ["greeting", "identify_need", "collect_facts", "offer_next_step", "confirm_close"]
session_states: Dict[str, int] = {}

@app.post("/chat")
async def chat(request: ChatRequest):
    msg = request.message
    session_id = request.session_id
    
    # Generate a unique ID for this specific message so it can be rated later
    msg_id = str(uuid.uuid4())
    
    # 1. DISTRESS CHECK (Break-Glass Protocol)
    distress = detect_distress(msg)
    if distress:
        target = ESCALATION_PATHS.get(distress, "a human agent")
        response_text = f"I hear you, and I am so sorry. Let me connect you with {target} right now. You don't have to handle this alone."
        return {
            "message_id": msg_id,
            "response": response_text,
            "escalated": True, "distress": True, "register": "bereaved", "service": None
        }

    # 2. AUTHORITY CHECK
    if not check_authority(msg):
        response_text = f"I appreciate you reaching out! 🙏 For pricing, personal data, or specific case details, our team needs to handle this personally. Please email {CLIENT_EMAIL} or use our booking form."
        return {
            "message_id": msg_id,
            "response": response_text,
            "escalated": True, "distress": False, "register": "professional", "service": None
        }

    # 3. JOURNEY STATE & CLASSIFY
    current_step = session_states.get(session_id, 0)
    if current_step < len(JOURNEY_STEPS) - 1: session_states[session_id] = current_step + 1
    
    register = detect_register(msg)
    service_key = detect_service(msg)
    svc = SERVICES.get(service_key, {"name": "our services", "plain": "Please specify which service you need help with."})

    # 4. GENERATE RESPONSE
    prompt = build_tcrdei_prompt(svc, register)
    try:
        response_text = call_llm(prompt, msg)
    except Exception as e:
        log_bug(msg, str(e), "llm_crash")
        response_text = "😅 I had a slight hiccup connecting to my brain. Please give me a moment and try again!"

    return {
        "message_id": msg_id,
        "response": response_text, 
        "escalated": False, "distress": False, "register": register, "service": service_key,
        "journey_step": JOURNEY_STEPS[session_states.get(session_id, 0)]
    }

@app.post("/rate")
async def rate_message(request: RatingRequest):
    """Handles the thumbs up / thumbs down feedback from the frontend."""
    try:
        log_rating(
            request.message_id, 
            request.session_id, 
            request.rating, 
            request.comment or "", 
            request.response_text
        )
        return {"status": "success", "message": "Feedback recorded. Thank you!"}
    except Exception as e:
        print(f"Rating error: {e}")
        raise HTTPException(status_code=500, detail="Could not save rating.")

@app.get("/", response_class=HTMLResponse)
async def root():
    return "<h1>Nexa AI Backend is Running 🤖</h1><p>Use the frontend interface to chat.</p>"
