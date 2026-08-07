# ==============================================================================
#   NEXA · AI SERVICE NAVIGATOR · main.py
#   ECCU / ECCB Generative AI & Python Summer Camp 2026
#   Client: Outsource Development Studio, Dominica
#
#   Features integrated from the camp skeleton:
#     · Day 7  — TCRDEI Prompt Engineering
#     · Day 9  — QA Bug Logging (safe_call pattern)
#     · Day 11 — PII Redaction (privacy hygiene)
#     · Day 14 — Agentic Journey + Distress Safeguard (Break-Glass)
#     · Day 18 — Resilience Fallbacks (Grok → Gemini → static)
#   Client requests:
#     · Grok free API as primary brain, Gemini as fallback
#     · Thumbs Up/Down rating after every chat
#     · NO document upload
# ==============================================================================

# --- IMPORTS: Bringing in the tools we need ---
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware      # Allows frontend↔backend communication
from fastapi.responses import HTMLResponse               # Lets us serve the index.html page
from fastapi.staticfiles import StaticFiles              # Serves images (logos, avatars)
from pydantic import BaseModel                           # Data validation for incoming JSON
import os                                                # Read secret API keys from the environment
import re                                                # Regular Expressions for PII redaction
import csv                                               # Write ratings + bug logs to CSV
import uuid                                              # Generate unique message IDs for ratings
from typing import Optional, Dict                        # Type hints
from datetime import datetime                            # Timestamps for logs
import google.generativeai as genai                      # Google Gemini SDK (fallback brain)
from openai import OpenAI                                # xAI Grok uses the OpenAI SDK format
from dotenv import load_dotenv                           # Loads secret keys from a .env file

load_dotenv()

app = FastAPI(title="Nexa AI Navigator")

# CORS: allow the frontend to talk to this backend (safe for the camp demo)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the /assets folder (logos, avatars) if it exists
try:
    app.mount("/assets", StaticFiles(directory="assets"), name="assets")
except Exception:
    pass  # App still runs if the folder is missing

# ==============================================================================
# 🛡️ CONFIG & CONSTANTS
# ==============================================================================
BOT_NAME       = "Nexa"
CLIENT_EMAIL   = "hello@outsourcedom.com"
CLIENT_CONTACTS = "our booking form"

# The services Nexa can talk about (Axis 3 — Territory/Service detection)
SERVICES = {
    "bpo": {
        "name": "BPO Services",
        "plain": "Business Process Outsourcing, customer support, and back-office operations.",
        "keywords": ["bpo", "outsourcing", "call center", "support", "back office"],
    },
    "recruitment": {
        "name": "Recruitment",
        "plain": "Talent acquisition, staffing, and HR consulting.",
        "keywords": ["hire", "recruitment", "staffing", "jobs", "talent", "hr"],
    },
    "uwi": {
        "name": "UWI Cave Hill Training",
        "plain": "Professional development and academic partnerships with UWI Cave Hill.",
        "keywords": ["uwi", "training", "cave hill", "courses", "education"],
    },
    "logistics": {
        "name": "Logistics",
        "plain": "Supply chain, freight, and local delivery coordination.",
        "keywords": ["logistics", "shipping", "freight", "supply chain", "delivery"],
    },
    "resilience": {
        "name": "Resilience Planning",
        "plain": "Climate adaptation, disaster recovery, and sustainable business continuity.",
        "keywords": ["resilience", "climate", "disaster", "sustainability", "continuity"],
    },
}

# ==============================================================================
# 🚫 AXIS 1 — AUTHORITY (the Red Line: what the bot must NEVER answer)
# ==============================================================================
AUTHORITY_TRIGGERS = [
    "price", "cost", "how much", "quote",
    "my case", "my application", "am i eligible", "my balance",
]

def check_authority(msg: str) -> bool:
    """Returns True if the message is SAFE for the AI to answer."""
    return not any(trigger in msg.lower() for trigger in AUTHORITY_TRIGGERS)

# ==============================================================================
# 🚨 DAY 14 — DISTRESS TRIGGERS (Break-Glass Protocol)
# ==============================================================================
DISTRESS_TRIGGERS = {
    "grief":     ["passed away", "died", "funeral", "lost my", "she's gone", "he's gone"],
    "panic":     ["can't breathe", "can't cope", "help now", "emergency"],
    "self_harm": ["hurt myself", "end it", "no way out"],
    "aggrieved": ["nobody listens", "you people never", "sick of this"],
}

ESCALATION_PATHS = {
    "grief":     "our Bereavement Support Partner",
    "panic":     "Emergency Services (911 / 999)",
    "self_harm": "the National Crisis Hotline",
    "aggrieved": "our Client Relations Desk",
}

def detect_distress(msg: str) -> Optional[str]:
    """Scans for distress keywords. If found, triggers the Break-Glass protocol."""
    m = msg.lower()
    for category, words in DISTRESS_TRIGGERS.items():
        if any(w in m for w in words):
            return category
    return None

def break_glass_reply(category: str) -> str:
    """
    DAY 14: Drops the standard persona. Switches to a low-cognitive-load
    empathetic register and escalates immediately (2-second SLA).
    """
    target = ESCALATION_PATHS.get(category, "a human agent")
    if category == "grief":
        return (f"I'm so sorry for your loss. You don't have to do anything right now. "
                f"I'm connecting you with {target} — you don't have to handle this alone.")
    if category == "self_harm":
        return (f"Thank you for telling me. You matter. Please reach out to {target} "
                f"right now — they will answer and they want to help.")
    return f"I hear you. Let me connect you with {target} right now."

# ==============================================================================
# 🧭 SERVICE + REGISTER DETECTION (Axes 2 & 3)
# ==============================================================================
def detect_service(msg: str) -> Optional[str]:
    """Detects which service the user is asking about via keyword matching."""
    for key, data in SERVICES.items():
        if any(kw in msg.lower() for kw in data["keywords"]):
            return key
    return None

def detect_register(msg: str) -> str:
    """DAY 7: Detects the user's emotional tone to adapt the AI's response style."""
    m = msg.lower()
    if any(w in m for w in ["died", "passed away", "funeral", "loss"]): return "bereaved"
    if any(w in m for w in ["asap", "urgent", "emergency", "now"]):      return "urgent"
    if any(w in m for w in ["regarding", "kindly", "please advise"]):    return "professional"
    return "warm"  # default tone

# ==============================================================================
# 🔒 DAY 11 — PII REDACTION (privacy before the AI ever sees the text)
# ==============================================================================
def redact_pii(text: str) -> str:
    """Redacts Personally Identifiable Information before sending to any AI."""
    pii_patterns = {
        "phone": r"\b\d{3}[-.\s]?\d{4}\b",
        "email": r"\b[\w\.-]+@[\w\.-]+\.\w+\b",
        "nin":   r"\b\d{9}\b",
    }
    for label, pattern in pii_patterns.items():
        text = re.sub(pattern, f"[REDACTED:{label}]", text)
    return text

# ==============================================================================
# 🧠 AI BRAIN — Grok (primary) + Gemini (fallback)
# ==============================================================================
# --- Grok (xAI) uses the OpenAI SDK format ---
GROK_API_KEY = os.getenv("GROK_API_KEY")
grok_client = None
if GROK_API_KEY:
    grok_client = OpenAI(api_key=GROK_API_KEY, base_url="https://api.x.ai/v1")
    print("✅ Grok API key loaded.")
else:
    print("⚠️ No Grok key found — will rely on Gemini fallback.")

# --- Google Gemini (fallback brain) ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
gemini_model = None
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel("gemini-2.0-flash")
    print("✅ Gemini API key loaded.")

# ==============================================================================
# 📝 DAY 7 — TCRDEI PROMPT TEMPLATE
#   T·Thoughtfully  C·Create  R·Really  D·Defined  E·Excellent  I·Inputs
# ==============================================================================
def build_tcrdei_prompt(service_data: dict, register: str) -> str:
    tone_hints = {
        "warm":         "TONE: Friendly, encouraging, simple words. Add a 💛 emoji.",
        "professional": "TONE: Polished, concise, respectful. No slang.",
        "urgent":       "TONE: Fast, direct, action-oriented. Use bullet points.",
        "bereaved":     "TONE: Open with gentle condolences. Explain gently. Max 2 sentences of facts.",
    }
    return f"""
[T] You are {BOT_NAME}, an AI Navigator for Outsource Development Studio in Dominica.
[C] Context: The user is asking about {service_data['name']}.
    Plain English: {service_data['plain']}.
    Ethical rule: You are the GPS; the human is the driver. NEVER quote prices, guess facts, or handle personal data.
[R] Reference: Always guide the user to book a human consultation for case-specific details.
[D] Success = the user feels understood, informed on the basics, and safe.
[E] Before answering, check: does this satisfy [D] and respect the ethical rule? If not, reroute.
[I] If unsure, ask ONE clarifying question and iterate.
{tone_hints.get(register, tone_hints['warm'])}
"""

def call_llm(prompt: str, user_msg: str) -> str:
    """
    DAY 18 RESILIENCE: Smart router — tries Grok first, falls back to Gemini,
    then to a safe static message. The user NEVER sees a crash.
    """
    safe_msg = redact_pii(user_msg)

    # 1) Try Grok (primary)
    if grok_client:
        try:
            response = grok_client.chat.completions.create(
                model="grok-beta",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user",   "content": safe_msg},
                ],
                temperature=0.4,
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"⚠️ Grok failed: {e} — falling back to Gemini.")
            log_bug(user_msg, str(e), "grok_api")

    # 2) Fallback to Gemini
    if gemini_model:
        try:
            full_prompt = f"{prompt}\n\nUser: {safe_msg}"
            return gemini_model.generate_content(full_prompt).text
        except Exception as e:
            print(f"⚠️ Gemini failed: {e}")
            log_bug(user_msg, str(e), "gemini_api")

    # 3) Ultimate static fallback
    return (f"I'm having trouble connecting to my AI brain right now. "
            f"Please email {CLIENT_EMAIL} or use our booking form for immediate help.")

# ==============================================================================
# 📊 LOGGING — Ratings (client request) + Bug log (Day 9)
# ==============================================================================
RATINGS_FILE = "ratings.csv"
BUG_LOG_FILE = "bug_log.csv"

def init_ratings_log():
    """Creates the ratings CSV header if the file doesn't exist yet."""
    if not os.path.exists(RATINGS_FILE):
        with open(RATINGS_FILE, "w", newline="") as f:
            csv.writer(f).writerow(
                ["timestamp", "message_id", "session_id", "rating", "comment", "bot_response_snippet"]
            )

init_ratings_log()

def log_rating(message_id: str, session_id: str, rating: str, comment: str, bot_response: str):
    """Appends a thumbs up/down rating to the CSV for the Product Owner."""
    with open(RATINGS_FILE, "a", newline="") as f:
        csv.writer(f).writerow([
            datetime.utcnow().isoformat(timespec="seconds"),
            message_id, session_id, rating, comment, bot_response[:150],
        ])

def log_bug(input_str: str, error: str, axis_tag: str = "none"):
    """DAY 9: Logs critical errors so the QA team can triage them."""
    try:
        file_exists = os.path.exists(BUG_LOG_FILE)
        with open(BUG_LOG_FILE, "a", newline="") as f:
            w = csv.writer(f)
            if not file_exists:
                w.writerow(["timestamp", "input", "error", "axis_tag"])
            w.writerow([datetime.utcnow().isoformat(timespec="seconds"),
                        input_str[:80], error, axis_tag])
    except Exception as e:
        print(f"Could not write bug log: {e}")

# ==============================================================================
# 🌐 PYDANTIC MODELS (validate incoming JSON)
# ==============================================================================
class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"

class RatingRequest(BaseModel):
    message_id: str
    session_id: str
    rating: str                     # "up" or "down"
    response_text: str
    comment: Optional[str] = ""

# ==============================================================================
# 🧭 DAY 14 — AGENTIC JOURNEY STATE MACHINE
# ==============================================================================
JOURNEY_STEPS = ["greeting", "identify_need", "collect_facts", "offer_next_step", "confirm_close"]
session_states: Dict[str, int] = {}

# ==============================================================================
# 🌐 API ENDPOINTS
# ==============================================================================
@app.post("/chat")
async def chat(request: ChatRequest):
    """The main endpoint: receives a user message, returns the AI reply."""
    msg = request.message
    session_id = request.session_id
    msg_id = str(uuid.uuid4())   # Unique ID so this message can be rated later

    # 1) BREAK-GLASS: distress check fires BEFORE anything else (2s SLA)
    distress = detect_distress(msg)
    if distress:
        return {
            "message_id": msg_id,
            "response": break_glass_reply(distress),
            "escalated": True,
            "distress": True,
            "register": "bereaved",
            "service": None,
        }

    # 2) AUTHORITY: pricing / case-specific questions go to a human
    if not check_authority(msg):
        return {
            "message_id": msg_id,
            "response": (f"I appreciate you reaching out! 🙏 For pricing, personal data, or "
                         f"specific case details, our team needs to handle this personally. "
                         f"Please email {CLIENT_EMAIL} or use our booking form."),
            "escalated": True,
            "distress": False,
            "register": "professional",
            "service": None,
        }

    # 3) Advance the journey state machine
    current_step = session_states.get(session_id, 0)
    if current_step < len(JOURNEY_STEPS) - 1:
        session_states[session_id] = current_step + 1

    # 4) Classify register + service
    register = detect_register(msg)
    service_key = detect_service(msg)
    svc = SERVICES.get(service_key, {
        "name": "our services",
        "plain": "Please tell me which service you'd like help with.",
    })

    # 5) Generate the response via the smart router
    prompt = build_tcrdei_prompt(svc, register)
    try:
        response_text = call_llm(prompt, msg)
    except Exception as e:
        log_bug(msg, str(e), "llm_crash")
        response_text = "😅 I had a slight hiccup connecting to my brain. Please try again in a moment!"

    return {
        "message_id": msg_id,
        "response": response_text,
        "escalated": False,
        "distress": False,
        "register": register,
        "service": service_key,
        "journey_step": JOURNEY_STEPS[session_states.get(session_id, 0)],
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
            request.response_text,
        )
        return {"status": "success", "message": "Feedback recorded. Thank you!"}
    except Exception as e:
        log_bug("rating", str(e), "none")
        raise HTTPException(status_code=500, detail="Could not save rating.")

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serves the frontend HTML file directly to the browser."""
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), status_code=200)
    except FileNotFoundError:
        return HTMLResponse(
            "<h1>Nexa AI Backend is Running 🤖</h1><p>index.html not found in root directory.</p>",
            status_code=404,
        )
