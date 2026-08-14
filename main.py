# ==============================================================================
#   NEXA · AI SERVICE NAVIGATOR · main.py
#   ECCU / ECCB Generative AI & Python Summer Camp 2026
#   Client: Outsource Development Studio, Dominica
# ==============================================================================

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import re
import csv
import uuid
from typing import Optional, Dict, Callable
from datetime import datetime
import google.generativeai as genai
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Nexa AI Navigator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    app.mount("/assets", StaticFiles(directory="assets"), name="assets")
except Exception:
    pass

# ==============================================================================
# 🤖 DAY 1: BOT IDENTITY
# ==============================================================================
BOT_NAME = "Nexa"
BOT_ROLE = "AI Service Navigator"
CLIENT_NAME = "Outsource Development Studio"
CLIENT_EMAIL = "hello@outsourcedom.com"

# ==============================================================================
# 🗺️ DAY 4 & 8: TERRITORY & SERVICES
# ==============================================================================
JARGON_TO_PLAIN = {
    "synergy": "teamwork", "bandwidth": "time", "onboard": "train",
    "bpo": "outsourcing", "kpi": "goal",
}

def translate_to_plain(msg: str) -> str:
    words = msg.split()
    return " ".join(JARGON_TO_PLAIN.get(w.lower(), w) for w in words)

# 📌 ADDED: The missing SERVICES dictionary so the bot doesn't crash!
SERVICES = {
    "bpo": {"name": "Business Process Outsourcing", "plain": "outsourced business services", "keywords": ["bpo", "outsource", "call center", "support"]},
    "recruitment": {"name": "Recruitment", "plain": "talent acquisition and hiring", "keywords": ["recruit", "hire", "job", "talent", "cv"]},
    "training": {"name": "Corporate Training", "plain": "upskilling and UWI seminars", "keywords": ["training", "uwi", "seminar", "upskill"]},
    "logistics": {"name": "Logistics", "plain": "supply chain and shipping", "keywords": ["logistics", "supply chain", "shipping"]},
}

# ==============================================================================
# 🚫 AXIS 1: AUTHORITY / THE RED LINE
# ==============================================================================
AUTHORITY_TRIGGERS = [
    "price", "cost", "how much", "quote", "my case", "my application", 
    "am i eligible", "my balance", "my account", "for me", "my status"
]

def check_authority(msg: str) -> bool:
    return not any(trigger in msg.lower() for trigger in AUTHORITY_TRIGGERS)

# ==============================================================================
# 🚨 DAY 14: DISTRESS & BREAK-GLASS
# ==============================================================================
DISTRESS_TRIGGERS = {
    "grief": ["passed away", "died", "funeral", "lost my", "she's gone", "he's gone"],
    "panic": ["can't breathe", "can't cope", "help now", "emergency", "overwhelmed", "it's too much"],
    "self_harm": ["hurt myself", "end it", "no way out", "kill myself", "kms", "suicide"],
    "aggrieved": ["nobody listens", "you people never", "sick of this", "fuck", "bitch", "asshole", "shit"],
}

ESCALATION_PATHS = {
    "grief": "our Bereavement Support Partner",
    "panic": "Emergency Services (911 / 999)",
    "self_harm": "the National Crisis Hotline (203)",
    "aggrieved": "our Client Relations Desk",
}

def detect_distress(msg: str) -> Optional[str]:
    m = msg.lower()
    for category, words in DISTRESS_TRIGGERS.items():
        if any(w in m for w in words): return category
    return None

def break_glass_reply(category: str) -> str:
    target = ESCALATION_PATHS.get(category, "a human agent")
    if category == "grief":
        return f"I'm so sorry for your loss. You don't have to do anything right now. I'm connecting you with {target}."
    if category == "self_harm":
        return f"Thank you for telling me. You matter. Please reach out to {target} right now."
    return f"I hear you. Let me connect you with {target} right now."

# ==============================================================================
# 🧭 AXIS 2 & 3: REGISTER + SERVICE
# ==============================================================================
def detect_service(msg: str) -> Optional[str]:
    for key, data in SERVICES.items():
        if any(kw in msg.lower() for kw in data["keywords"]): return key
    return None

def detect_register(msg: str) -> str:
    m = msg.lower()
    if any(w in m for w in ["died", "passed away", "funeral", "loss"]): return "bereaved"
    if any(w in m for w in ["asap", "urgent", "emergency", "now"]):      return "urgent"
    if any(w in m for w in ["regarding", "kindly", "please advise"]):    return "professional"
    return "warm"

# ==============================================================================
# 🔒 DAY 11: PII REDACTION
# ==============================================================================
def redact_pii(text: str) -> str:
    pii_patterns = {
        "phone": r"\b\d{3}[-.\s]?\d{4}\b",
        "email": r"\b[\w\.-]+@[\w\.-]+\.\w+\b",
        "nin":   r"\b\d{9}\b",
    }
    for label, pattern in pii_patterns.items():
        text = re.sub(pattern, f"[REDACTED:{label}]", text)
    return text

# ==============================================================================
# 📝 DAY 17: CONFIRMATION REGISTER
# ==============================================================================
FACT_REGISTER = []
TONE_REGISTER = []

def log_fact(topic: str, statement: str, verdict: str = "confirmed"):
    FACT_REGISTER.append({"topic": topic, "statement": statement, "verdict": verdict})

def log_tone(register: str, sample: str, verdict: str = "confirmed"):
    TONE_REGISTER.append({"register": register, "sample": sample, "verdict": verdict})

log_fact("services_offered", "BPO, Recruitment, UWI, Logistics, Resilience", "confirmed")
log_tone("warm", "Friendly, encouraging, simple words.", "confirmed")
log_tone("bereaved", "Gentle condolences first. Max 2 sentences of facts.", "confirmed")

# ==============================================================================
# 🧠 AI BRAINS: GEMINI (Primary) + GROK (Fallback)
# ==============================================================================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
gemini_model = None
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    # 📌 UPDATED: Changed to the actual "flash-lite" model name!
    gemini_model = genai.GenerativeModel("gemini-2.0-flash-lite") 
    print("✅ Camp Gemini key loaded (PRIMARY).")
else:
    print("⚠️ No Gemini key found.")

GROK_API_KEY = os.getenv("GROK_API_KEY")
grok_client = None
if GROK_API_KEY:
    grok_client = OpenAI(api_key=GROK_API_KEY, base_url="https://api.x.ai/v1")
    print("✅ Grok key loaded (FALLBACK).")

# ==============================================================================
# 🛡️ DAY 9 & 18: safe_call & RESILIENCE
# ==============================================================================
def safe_call(fn: Callable, *args, fallback: str = None, on_error=None, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception as exc:
        if on_error: on_error(exc)
        return fallback or "I hit a snag. Let me connect you with a human agent right now."

def build_tcrdei_prompt(service_data: dict, register: str) -> str:
    tone_hints = {
        "warm":         "TONE: Friendly, encouraging, simple words. Add a 💛 emoji.",
        "professional": "TONE: Polished, concise, respectful. No slang.",
        "urgent":       "TONE: Fast, direct, action-oriented. Use bullet points.",
        "bereaved":     "TONE: Open with gentle condolences. Explain gently. Max 2 sentences of facts.",
    }
    return f"""
[T] You are {BOT_NAME}, an AI Navigator for {CLIENT_NAME} in Dominica.
[C] Context: The user is asking about {service_data['name']}. Plain English: {service_data['plain']}.
    Ethical rule: You are the GPS; the human is the driver. NEVER quote prices.
[R] Reference: Always guide the user to book a human consultation.
[D] Success = the user feels understood, informed, and safe.
[E] Check: does this satisfy [D]? If not, reroute.
[I] If unsure, ask ONE clarifying question.
{tone_hints.get(register, tone_hints['warm'])}
"""

GROK_MODELS = ["grok-3", "grok-2-latest", "grok-2", "grok-beta"]

def call_gemini(prompt: str, user_msg: str) -> str:
    full_prompt = f"{prompt}\n\nUser: {user_msg}"
    return gemini_model.generate_content(full_prompt).text

def call_grok(prompt: str, user_msg: str) -> str:
    for model in GROK_MODELS:
        try:
            response = grok_client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": prompt}, {"role": "user", "content": user_msg}],
                temperature=0.4,
            )
            return response.choices[0].message.content
        except Exception:
            continue
    raise Exception("All Grok models failed")

def call_llm(prompt: str, user_msg: str) -> str:
    safe_msg = redact_pii(translate_to_plain(user_msg))

    if gemini_model:
        result = safe_call(call_gemini, prompt, safe_msg, fallback=None,
                           on_error=lambda e: log_bug(user_msg, f"Gemini error: {e}", "gemini_api"))
        if result: return result

    if grok_client:
        result = safe_call(call_grok, prompt, safe_msg, fallback=None,
                           on_error=lambda e: log_bug(user_msg, f"Grok error: {e}", "grok_api"))
        if result: return result

    return f"I'm having trouble connecting right now. Please email {CLIENT_EMAIL}."

# ==============================================================================
# 📊 LOGGING
# ==============================================================================
RATINGS_FILE = "ratings.csv"
BUG_LOG_FILE = "bug_log.csv"

def init_ratings_log():
    if not os.path.exists(RATINGS_FILE):
        with open(RATINGS_FILE, "w", newline="") as f:
            csv.writer(f).writerow(["timestamp", "message_id", "session_id", "rating", "comment", "bot_response_snippet"])
init_ratings_log()

def log_rating(message_id: str, session_id: str, rating: str, comment: str, bot_response: str):
    with open(RATINGS_FILE, "a", newline="") as f:
        csv.writer(f).writerow([datetime.utcnow().isoformat(timespec="seconds"), message_id, session_id, rating, comment, bot_response[:150]])

def log_bug(input_str: str, error: str, axis_tag: str = "none"):
    try:
        file_exists = os.path.exists(BUG_LOG_FILE)
        with open(BUG_LOG_FILE, "a", newline="") as f:
            w = csv.writer(f)
            if not file_exists: w.writerow(["timestamp", "input", "error", "axis_tag"])
            w.writerow([datetime.utcnow().isoformat(timespec="seconds"), input_str[:80], error, axis_tag])
    except Exception as e:
        print(f"Could not write bug log: {e}")

# ==============================================================================
# 🧭 DAY 14: AGENTIC JOURNEY
# ==============================================================================
JOURNEY_STEPS = ["greeting", "identify_need", "collect_facts", "offer_next_step", "confirm_close"]
session_states: Dict[str, int] = {}

# ==============================================================================
# 🌐 PYDANTIC MODELS
# ==============================================================================
class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"

class RatingRequest(BaseModel):
    message_id: str
    session_id: str
    rating: str
    response_text: str
    comment: Optional[str] = ""

# ==============================================================================
# 🌐 API ENDPOINTS
# ==============================================================================
@app.post("/chat")
async def chat(request: ChatRequest):
    msg = request.message
    session_id = request.session_id
    msg_id = str(uuid.uuid4())

    distress = detect_distress(msg)
    if distress:
        return {"message_id": msg_id, "response": break_glass_reply(distress), "escalated": True, "distress": True, "register": "bereaved", "service": None}

    if not check_authority(msg):
        return {"message_id": msg_id, "response": f"I appreciate you reaching out! 🙏 For pricing or personal data, our team needs to handle this. Please email {CLIENT_EMAIL}.", "escalated": True, "distress": False, "register": "professional", "service": None}

    current_step = session_states.get(session_id, 0)
    if current_step < len(JOURNEY_STEPS) - 1:
        session_states[session_id] = current_step + 1

    register = detect_register(msg)
    service_key = detect_service(msg)
    svc = SERVICES.get(service_key, {"name": "our services", "plain": "Please tell me which service you'd like help with."})

    prompt = build_tcrdei_prompt(svc, register)
    response_text = call_llm(prompt, msg)

    return {"message_id": msg_id, "response": response_text, "escalated": False, "distress": False, "register": register, "service": service_key, "journey_step": JOURNEY_STEPS[session_states.get(session_id, 0)]}

@app.post("/rate")
async def rate_message(request: RatingRequest):
    try:
        log_rating(request.message_id, request.session_id, request.rating, request.comment or "", request.response_text)
        return {"status": "success", "message": "Feedback recorded. Thank you!"}
    except Exception as e:
        log_bug("rating", str(e), "none")
        raise HTTPException(status_code=500, detail="Could not save rating.")

# 📌 FIXED: Completed the cut-off root endpoint
@app.get("/", response_class=HTMLResponse)
async def root():
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), status_code=200)
    except FileNotFoundError:
        return HTMLResponse(
            "<h1>Nexa AI Backend is Running 🤖</h1><p>index.html not found in root directory.</p>",
            status_code=404,
        )
