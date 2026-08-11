# ==============================================================================
#   NEXA · AI SERVICE NAVIGATOR · main.py
#   ECCU / ECCB Generative AI & Python Summer Camp 2026
#   Client: Outsource Development Studio, Dominica
#
#   Integrates the camp skeleton (Day 1–18) + client changes:
#     · Day 6  — Authority axis (never answer case-specific questions)
#     · Day 7  — Register axis + TCRDEI prompt engineering
#     · Day 8  — Territory/service axis + three-axis router
#     · Day 9  — safe_call + bug logging (never crash to user)
#     · Day 11 — PII redaction (redact BEFORE the LLM sees it)
#     · Day 14 — Agentic journey + Distress Break-Glass safeguard
#     · Day 18 — Resilience fallbacks (Gemini → Grok → static reply)
#
#   Client requests:
#     · Camp-managed Gemini key = primary brain
#     · Grok = optional fallback
#     · Thumbs up/down rating after every chat
#     · NO document upload
# ==============================================================================

# --- IMPORTS ---------------------------------------------------------------
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import re
import csv
import uuid
from typing import Optional, Dict
from datetime import datetime

import google.generativeai as genai      # Camp-managed Gemini (primary brain)
from dotenv import load_dotenv           # Loads secret keys from .env

# Optional Grok fallback (only used if GROK_API_KEY is set)
try:
    from openai import OpenAI
    OPENAI_SDK_AVAILABLE = True
except ImportError:
    OPENAI_SDK_AVAILABLE = False

load_dotenv()

app = FastAPI(title="Nexa · AI Service Navigator")

# CORS so the frontend can talk to the backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the /assets folder (avatars, logo) if it exists
try:
    app.mount("/assets", StaticFiles(directory="assets"), name="assets")
except Exception:
    pass  # App still runs if the folder is missing


# ==============================================================================
# 🛡️ CONFIG & IDENTITY
# ==============================================================================
BOT_NAME      = "Nexa"
BOT_ROLE      = "AI Service Navigator"
CLIENT_NAME   = "Outsource Development Studio"
CLIENT_EMAIL  = "hello@outsourcedom.com"
CLIENT_PHONE  = "our booking form"

# Central Rule (Day 5 / Day 10): "The bot is the GPS; the human is the driver."
CENTRAL_RULE = "The bot is the GPS; the human is the driver. Never over-promise."


# ==============================================================================
# 🧭 SERVICES (Axis 3 — Territory/Service routing)
# ==============================================================================
SERVICES = {
    "bpo": {
        "name": "BPO Services",
        "plain": "Business Process Outsourcing, customer support, and back-office operations.",
        "keywords": ["bpo", "outsourcing", "call center", "call centre", "support", "back office", "back-office"],
        "escalate_to": CLIENT_EMAIL,
    },
    "recruitment": {
        "name": "Recruitment",
        "plain": "Talent acquisition, staffing, and HR consulting.",
        "keywords": ["recruitment", "recruit", "hire", "hiring", "staffing", "talent", "job", "jobs", "hr"],
        "escalate_to": CLIENT_EMAIL,
    },
    "uwi": {
        "name": "UWI Cave Hill Training",
        "plain": "Professional development and training programmes with UWI Cave Hill.",
        "keywords": ["uwi", "training", "cave hill", "course", "courses", "education", "workshop"],
        "escalate_to": CLIENT_EMAIL,
    },
    "logistics": {
        "name": "Logistics",
        "plain": "Supply chain, freight, and delivery coordination.",
        "keywords": ["logistics", "shipping", "freight", "supply chain", "delivery", "transport"],
        "escalate_to": CLIENT_EMAIL,
    },
    "resilience": {
        "name": "Resilience Planning",
        "plain": "Business continuity, disaster preparedness, and resilience planning.",
        "keywords": ["resilience", "continuity", "disaster", "emergency planning", "preparedness"],
        "escalate_to": CLIENT_EMAIL,
    },
}


# ==============================================================================
# 🚫 AXIS 1 — AUTHORITY (Day 6): questions the bot must NEVER answer
# ==============================================================================
AUTHORITY_TRIGGERS = [
    "my case", "my application", "am i eligible", "my balance",
    "my account", "for me", "my status", "price", "cost", "how much", "quote",
]

def classify_authority(msg: str) -> Optional[str]:
    """Returns None (= escalate) if the message is case-specific or asks pricing."""
    m = msg.lower()
    if any(t in m for t in AUTHORITY_TRIGGERS):
        return None
    return "ok"


# ==============================================================================
# 🎭 AXIS 2 — REGISTER (Day 7): detect the user's emotional tone
# ==============================================================================
GRIEF_WORDS    = {"passed away", "died", "funeral", "loss", "mourning", "grief"}
URGENT_WORDS   = {"now", "asap", "urgent", "emergency", "today", "immediately"}
FORMAL_WORDS   = {"regarding", "hereby", "kindly", "please advise", "advise"}

def classify_register(msg: str) -> str:
    m = msg.lower()
    if any(w in m for w in GRIEF_WORDS):   return "bereaved"
    if any(w in m for w in URGENT_WORDS):  return "urgent"
    if any(w in m for w in FORMAL_WORDS):  return "professional"
    return "warm"


# ==============================================================================
# 🧭 AXIS 3 — TERRITORY/SERVICE (Day 8): which service is the user asking about
# ==============================================================================
def detect_service(msg: str) -> Optional[str]:
    m = msg.lower()
    for key, data in SERVICES.items():
        if any(kw in m for kw in data["keywords"]):
            return key
    return None


# ==============================================================================
# 🚨 DAY 14 — DISTRESS TRIGGERS + BREAK-GLASS SAFEGUARD
# ==============================================================================
DISTRESS_TRIGGERS = {
    "grief":     ["passed away", "died", "funeral", "lost my", "she's gone", "he's gone"],
    "panic":     ["can't breathe", "can't cope", "help now", "overwhelmed"],
    "self_harm": ["hurt myself", "end it", "no way out", "don't want to live"],
    "aggrieved": ["nobody listens", "you people never", "sick of this", "useless"],
}

ESCALATION_PATH = {
    "grief":     f"our support team at {CLIENT_EMAIL}",
    "panic":     "a real human agent right away",
    "self_harm": "a trained human — please reach out to someone you trust now",
    "aggrieved": f"our client-relations desk at {CLIENT_EMAIL}",
    "unknown":   "a human agent",
}

def detect_distress(msg: str) -> Optional[str]:
    m = msg.lower()
    for category, words in DISTRESS_TRIGGERS.items():
        if any(w in m for w in words):
            return category
    return None

def break_glass_reply(category: str) -> str:
    """Drops the standard persona. Low-cognitive-load, empathetic, immediate escalation."""
    target = ESCALATION_PATH.get(category, ESCALATION_PATH["unknown"])
    if category == "grief":
        return (f"I'm so sorry. You don't have to do anything right now. "
                f"I'm connecting you with {target}. 💛")
    if category == "self_harm":
        return (f"Thank you for telling me — you matter. Please reach out to "
                f"{target}. You are not alone.")
    return f"I hear you. Let me connect you with {target} right now."


# ==============================================================================
# 🧭 DAY 14 — AGENTIC JOURNEY (5-step state machine)
# ==============================================================================
JOURNEY_STEPS = ["greeting", "identify_need", "collect_facts", "offer_next_step", "confirm_close"]
session_states: Dict[str, int] = {}


# ==============================================================================
# 🔒 DAY 11 — PII REDACTION (redact BEFORE the LLM ever sees the text)
# ==============================================================================
PII_REGEXES = {
    "national_insurance": r"\b\d{9}\b",                 # 9-digit NIN
    "phone":              r"\b\d{3}[- ]?\d{4}\b",
    "email":              r"\b[\w\.-]+@[\w\.-]+\.\w+\b",
    "address_zip":        r"\b[A-Z]{2}\d{4}\b",         # ECCU postal-code shape
}

def redact(text: str) -> str:
    for label, pattern in PII_REGEXES.items():
        text = re.sub(pattern, f"[REDACTED:{label}]", text)
    return text


# ==============================================================================
# 📝 DAY 7 — TCRDEI PROMPT LIBRARY
#   T·Thoughtfully  C·Create  R·Really  D·Defined  E·Excellent  I·Inputs
# ==============================================================================
PROMPT_TEMPLATE = """\
[T] You are {bot_name}, a {bot_role} serving prospective clients of {client}.
[C] Context: {service_plain}. Known pains: users want fast, clear answers.
    Ethical rule: {central_rule}. Never quote prices or handle personal data.
[R] Reference — ideal response:
    User: "What is BPO?"
    Bot:  "BPO means we handle support and back-office tasks for you. Want a consultation?"
[D] Success = the user feels informed, respected, and guided toward booking a human consultation.
[E] Before answering, check: does this satisfy [D]? If not, reroute.
[I] If the answer feels off, ask ONE clarifying question and iterate.
Register: {register}.
"""

def make_prompt(register: str, service_plain: str) -> str:
    return PROMPT_TEMPLATE.format(
        bot_name=BOT_NAME,
        bot_role=BOT_ROLE,
        client=CLIENT_NAME,
        service_plain=service_plain,
        central_rule=CENTRAL_RULE,
        register=register,
    )


# ==============================================================================
# 🧠 AI BRAIN — Gemini (camp-managed, PRIMARY) + Grok (optional FALLBACK)
# ==============================================================================
# --- Primary: camp-managed Gemini key ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
gemini_model = None
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel("gemini-1.5-flash")  # stable + generous free tier
    print("✅ Camp-managed Gemini API key loaded (PRIMARY).")
else:
    print("⚠️ No GEMINI_API_KEY found — the bot will rely on fallbacks.")

# --- Fallback: Grok (only if GROK_API_KEY is set) ---
GROK_API_KEY = os.getenv("GROK_API_KEY")
grok_client = None
if GROK_API_KEY and OPENAI_SDK_AVAILABLE:
    grok_client = OpenAI(api_key=GROK_API_KEY, base_url="https://api.x.ai/v1")
    print("✅ Grok API key loaded (FALLBACK).")
else:
    print("ℹ️ No Grok key — Gemini is the only live brain.")


# ==============================================================================
# 🛡️ DAY 18 — safe_call(): every external call goes through here
# ==============================================================================
def safe_call(fn, *args, fallback: str = None, on_error=None, **kwargs):
    """Wraps ANY function so a crash never leaks to the user."""
    try:
        return fn(*args, **kwargs)
    except Exception as exc:
        if on_error:
            on_error(exc)
        return fallback or "I hit a snag. Let me connect you with a human agent right now."


def gemini_generate(system_prompt: str, user_msg: str) -> str:
    full_prompt = f"{system_prompt}\n\nUser: {user_msg}"
    response = gemini_model.generate_content(full_prompt)
    return response.text


def grok_generate(system_prompt: str, user_msg: str) -> str:
    response = grok_client.chat.completions.create(
        model="grok-2-latest",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_msg},
        ],
        temperature=0.4,
    )
    return response.choices[0].message.content


def call_llm(system_prompt: str, user_msg: str) -> str:
    """Resilience chain: Gemini (camp) → Grok → static safe reply."""
    # 1) Primary: Gemini
    if gemini_model:
        result = safe_call(gemini_generate, system_prompt, user_msg,
                           fallback=None,
                           on_error=lambda e: log_bug(user_msg, f"Gemini error: {e}", "none"))
        if result:
            return result

    # 2) Fallback: Grok
    if grok_client:
        result = safe_call(grok_generate, system_prompt, user_msg,
                           fallback=None,
                           on_error=lambda e: log_bug(user_msg, f"Grok error: {e}", "none"))
        if result:
            return result

    # 3) Final static fallback — user NEVER sees a crash
    return (f"I'm having trouble connecting right now, but I don't want to leave you waiting. "
            f"Please email {CLIENT_EMAIL} or use the booking form and a real person will help you. 💛")


# ==============================================================================
# 🐞 DAY 9 — BUG LOGGING
# ==============================================================================
BUG_LOG_FILE = "bug_log.csv"

def log_bug(input_str: str, error: str, axis_tag: str = "none"):
    try:
        file_exists = os.path.exists(BUG_LOG_FILE)
        with open(BUG_LOG_FILE, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if not file_exists:
                w.writerow(["timestamp", "input", "error", "axis_tag"])
            w.writerow([datetime.utcnow().isoformat(timespec="seconds"),
                        input_str[:80], error, axis_tag])
    except Exception as e:
        print(f"Could not write bug log: {e}")


# ==============================================================================
# 👍 RATINGS (client request) — thumbs up/down after every chat
# ==============================================================================
RATINGS_FILE = "ratings.csv"

def init_ratings_log():
    if not os.path.exists(RATINGS_FILE):
        with open(RATINGS_FILE, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(
                ["timestamp", "message_id", "session_id", "rating", "comment", "bot_response_snippet"]
            )

init_ratings_log()

def log_rating(message_id: str, session_id: str, rating: str, comment: str, bot_response: str):
    with open(RATINGS_FILE, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            datetime.utcnow().isoformat(timespec="seconds"),
            message_id, session_id, rating, comment, bot_response[:150],
        ])


# ==============================================================================
# 🧭 DAY 8 — THE THREE-AXIS ROUTER (the heart of the bot)
# ==============================================================================
def route(user_msg: str, session_id: str) -> Dict:
    message_id = str(uuid.uuid4())

    # 0) PII redaction FIRST (Day 11) — before anything else touches the text
    safe_msg = redact(user_msg)

    # 1) DISTRESS check (Day 14) — Break-Glass fires immediately, skips the LLM
    distress = detect_distress(safe_msg)
    if distress:
        return {
            "message_id": message_id,
            "response": break_glass_reply(distress),
            "register": "bereaved",
            "service": None,
            "escalated": True,
            "distress": True,
            "journey_step": "break_glass",
        }

    # 2) Advance the journey state machine (Day 14)
    step_index = session_states.get(session_id, 0)
    journey_step = JOURNEY_STEPS[step_index]
    if step_index < len(JOURNEY_STEPS) - 1:
        session_states[session_id] = step_index + 1

    # 3) AUTHORITY axis (Day 6) — escalate case-specific / pricing questions
    if classify_authority(safe_msg) is None:
        return {
            "message_id": message_id,
            "response": (f"That's a personal/pricing question, so I'll hand you to a real person "
                         f"who can give you an accurate answer. Please email {CLIENT_EMAIL} "
                         f"or use the booking form. 🙏"),
            "register": classify_register(safe_msg),
            "service": None,
            "escalated": True,
            "distress": False,
            "journey_step": journey_step,
        }

    # 4) REGISTER axis (Day 7)
    register = classify_register(safe_msg)

    # 5) TERRITORY/SERVICE axis (Day 8)
    service_key = detect_service(safe_msg)
    service = SERVICES.get(service_key)
    service_plain = service["plain"] if service else (
        f"{CLIENT_NAME} offers BPO, Recruitment, UWI Training, Logistics, and Resilience Planning. "
        "Which one are you curious about?"
    )

    # 6) Build the TCRDEI prompt (Day 7) and call the LLM (Day 18 resilience)
    system_prompt = make_prompt(register, service_plain)
    response_text = call_llm(system_prompt, safe_msg)

    return {
        "message_id": message_id,
        "response": response_text,
        "register": register,
        "service": service_key,
        "escalated": False,
        "distress": False,
        "journey_step": journey_step,
    }


# ==============================================================================
# 📦 PYDANTIC MODELS (validate incoming JSON)
# ==============================================================================
class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"

class RatingRequest(BaseModel):
    message_id: str
    session_id: str = "default"
    rating: str                       # "up" or "down"
    response_text: str = ""
    comment: Optional[str] = ""


# ==============================================================================
# 🌐 ENDPOINTS
# ==============================================================================
@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the frontend chat interface."""
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), status_code=200)
    except FileNotFoundError:
        return HTMLResponse(
            "<h1>Nexa backend is running 🤖</h1><p>index.html not found in root directory.</p>",
            status_code=404,
        )

@app.get("/health")
async def health():
    """Render health-check + a quick status of the AI brains."""
    return {
        "status": "ok",
        "gemini_loaded": gemini_model is not None,
        "grok_loaded": grok_client is not None,
    }

@app.post("/chat")
async def chat(request: ChatRequest):
    result = route(request.message, request.session_id)
    return result

@app.post("/rate")
async def rate_message(request: RatingRequest):
    try:
        log_rating(
            request.message_id,
            request.session_id,
            request.rating,
            request.comment or "",
            request.response_text,
        )
        return {"status": "success", "message": "Thanks for the feedback! 💛"}
    except Exception as e:
        log_bug("rating", str(e), "none")
        raise HTTPException(status_code=500, detail="Could not save rating.")
