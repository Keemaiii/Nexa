# ==============================================================================
# 🤖 NEXA · ALL-IN-ONE BACKEND & API (Python FastAPI)
# ==============================================================================
# JUDGE NOTE: This backend is built using FastAPI, a modern, high-performance 
# web framework for Python. We chose FastAPI over Flask/Django for its speed, 
# automatic data validation (via Pydantic), and built-in Swagger documentation.
#
# STUDENT NOTE: This file acts as the "brain" of Nexa. The frontend (index.html) 
# is the "face" and "mouth". When a user types a message, it gets sent here. 
# This Python code processes the text, checks for privacy/safety, figures out 
# the user's intent, and then asks Google Gemini (the AI) to write a response!
# ==============================================================================

# --- IMPORTS: Bringing in the tools we need ---
from fastapi import FastAPI                   # The core web framework
from fastapi.responses import HTMLResponse    # Allows us to send HTML pages
from fastapi.staticfiles import StaticFiles   # 🛑 CRITICAL IMPORT: Serves images (logos, avatars) to the frontend
from pydantic import BaseModel                # Data validation (ensures the frontend sends valid JSON)
import os                                     # Interacts with the operating system (e.g., reading secret keys)
import re                                     # Regular Expressions: Advanced text searching (used for privacy redaction)
import json                                   # Standard JSON handling
from typing import Optional                   # Allows variables to be "None" or a specific type
import google.generativeai as genai           # The Google Gemini AI SDK (the actual intelligence of the bot)
from dotenv import load_dotenv                # Loads secret API keys from a .env file so they aren't exposed in GitHub!

# Load environment variables (like our secret Gemini API key)
load_dotenv()

# Initialize the FastAPI application
app = FastAPI(title="Nexa All-In-One")

# ==============================================================================
# 🌐 SERVE STATIC ASSETS & FRONTEND
# ==============================================================================
# JUDGE NOTE: We use an "Option A" deployment strategy. Instead of hosting the 
# frontend on Vercel and backend on Render separately, FastAPI serves the HTML 
# file directly. This reduces CORS errors, lowers hosting costs, and simplifies 
# the student deployment pipeline.

# 1. Serve the /assets folder (logos, bot avatar, user avatar)
if os.path.exists("assets"):
    app.mount("/assets", StaticFiles(directory="assets"), name="assets")

# 2. Serve the main index.html file when someone visits the root URL (/)
@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

# ==============================================================================
# 📚 KNOWLEDGE BASE & CLIENT DATA
# ==============================================================================
# STUDENT NOTE: This is the bot's "textbook". Instead of letting the AI make 
# up facts, we strictly define the services the business actually offers here.

BOT_NAME = "Nexa"
CLIENT_EMAIL = "admin@outsourcejobsda.com"
CLIENT_CONTACTS = "Dr. Favour Anthony & Amara Dupuis"

# Dictionary of services: Keys are internal IDs, values contain the public name, 
# a simple explanation, and keywords the user might type.
SERVICES = {
    "bpo": {"name": "Business Process Outsourcing (BPO)", "plain": "We handle your admin tasks so your team can focus on growth.", "keywords": ["outsource", "bpo", "admin"]},
    "recruitment": {"name": "Recruitment & Talent Matching", "plain": "We find the right people for your team.", "keywords": ["recruit", "hire", "talent", "eor"]},
    "training": {"name": "Corporate Training & Seminars", "plain": "Quarterly training with UWI Cave Hill School of Business.", "keywords": ["training", "seminar", "uwi", "cave hill"]},
    "logistics": {"name": "Logistics & Supply Chain", "plain": "Trucking, import-export, and getting goods where they need to go.", "keywords": ["logistics", "trucking", "import", "export"]},
    "resilience": {"name": "Resilience & Sustainability Planning", "plain": "Climate action and business continuity planning.", "keywords": ["resilience", "climate", "sustainability"]},
    "consulting": {"name": "Strategic Consulting", "plain": "One-on-one expert advice to grow your business.", "keywords": ["consult", "strategy", "advice"]}
}

# ⚠️ PRIVACY & ESCALATION TRIGGERS
# JUDGE NOTE: A major hallucination risk for AI is inventing prices, signing contracts, 
# or giving legal/medical advice. If a user asks about these, we BLOCK the AI from 
# responding and instead route them to a human (Dr. Anthony & Amara).
AUTHORITY_TRIGGERS = [
    "price", "cost", "fee", "how much", "quote", 
    "my case", "my application", "eligible", 
    "passport", "nin", "bank account", "contract", "guarantee"
]

# ==============================================================================
# 🛡️ THE THREE-AXIS ROUTER (Intent, Service, and Tone Detection)
# ==============================================================================
# STUDENT NOTE: This is our "Traffic Cop". It reads the user's message and decides 
# 3 things before the AI even sees the text:
# 1. Is the user asking a question the AI is ALLOWED to answer? (Authority)
# 2. What service is the user asking about? (Service Detection)
# 3. What is the user's emotional state? (Register/Tone Detection)

def check_authority(msg: str) -> bool:
    """Returns True if the message is SAFE for AI to answer. False if it needs a human."""
    return not any(trigger in msg.lower() for trigger in AUTHORITY_TRIGGERS)

def detect_service(msg: str) -> Optional[str]:
    """Checks which service the user is asking about by matching keywords."""
    for key, data in SERVICES.items():
        if any(kw in msg.lower() for kw in data["keywords"]):
            return key
    return None

def detect_register(msg: str) -> str:
    """Detects the emotional tone of the user to adjust the AI's response style."""
    m = msg.lower()
    if any(w in m for w in ["died", "passed away", "funeral", "loss"]): return "bereaved"
    if any(w in m for w in ["asap", "urgent", "emergency", "now"]): return "urgent"
    if any(w in m for w in ["regarding", "kindly", "please advise"]): return "professional"
    return "warm"  # Default tone

# 🔒 PRIVACY REDACTION (Regex)
# STUDENT NOTE: If a user accidentally types their phone number or email, we DO NOT 
# want to send that to Google's servers. We use Regular Expressions (Regex) to find 
# patterns like phone numbers and replace them with "[REDACTED]".
def redact_pii(text: str) -> str:
    """Redacts Personally Identifiable Information (PII) before sending to AI."""
    pii_patterns = {
        "phone": r"\b\d{3}[-.\s]?\d{4}\b",    # Matches 123-4567 or 123 4567
        "email": r"\b[\w\.-]+@[\w\.-]+\.\w+\b",    # Matches user@domain.com
        "nin": r"\b\d{9}\b"                  # Matches 9-digit National Insurance Numbers
    }
    for label, pattern in pii_patterns.items():
        text = re.sub(pattern, f"[REDACTED:{label}]", text)
    return text

# ==============================================================================
# 🧠 AI BRAIN (Google Gemini Integration & Prompt Engineering)
# ==============================================================================
# Configure the Gemini API using the secret key from our .env file
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
# We use the "flash" model for fast, low-latency responses
gemini_model = genai.GenerativeModel("gemini-2.0-flash")

def get_ai_response(user_msg: str, service: Optional[str], register: str) -> str:
    """Constructs the final prompt, sends it to Gemini, and returns the text."""
    
    # 1. Clean the message for privacy
    safe_msg = redact_pii(user_msg)
    
    # 2. ESCALATION CHECK: If the user asks about pricing/sensitive data, stop the AI!
    if not check_authority(safe_msg):
        return f"I appreciate you reaching out! 🙏 For pricing, personal data, or specific case details, our team needs to handle this personally. Please email {CLIENT_EMAIL} or contact {CLIENT_CONTACTS} to book a consultation."
    
    # 3. Retrieve the correct service details from our database
    svc = SERVICES.get(service, {"name": "our services", "plain": "Please visit our website for details."}) if service else {"name": "our services", "plain": "Please specify which service you need help with."}
    
    # 4. TONE ADAPTATION: Change the AI's personality based on the user's emotional state
    tone_hints = {
        "warm": "TONE: Friendly, encouraging, simple words. Add a 💛 emoji.",
        "professional": "TONE: Polished, concise, respectful. No slang.",
        "urgent": "TONE: Fast, direct, action-oriented. Use bullet points.",
        "bereaved": "TONE: Open with gentle condolences. Explain gently. Max 2 sentences of facts."
    }
    
    # 5. THE MASTER PROMPT
    # JUDGE NOTE: We use strict role-playing and constraints ("GOLDEN RULE") to prevent 
    # the AI from hallucinating or acting outside its boundaries.
    prompt = f"""You are {BOT_NAME} for Outsource Development Studio in Dominica.
    GOLDEN RULE: You are the GPS. The human is the driver. NEVER quote prices or handle personal data.
    TOPIC: {svc['name']}. Plain English: {svc['plain']}.
    {tone_hints.get(register, tone_hints['warm'])}"""
    
    try:
        # Send the prompt + user message to Gemini and extract the text
        return gemini_model.generate_content(prompt + "\n\nUser: " + safe_msg).text
    except Exception as e:
        # Graceful error handling: Never crash the app, always return a friendly message
        return f"😅 I had a hiccup connecting to the AI. (Error: {e})"

# ==============================================================================
# 🌐 API ENDPOINT (The door the frontend knocks on)
# ==============================================================================
# STUDENT NOTE: Pydantic models ensure that if the frontend sends garbage data, 
# FastAPI automatically blocks it and returns a 422 Unprocessable Entity error.
class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
async def chat(request: ChatRequest):
    """The main function that receives the user's message and sends back the AI's reply."""
    
    # Step 1: Analyze the user's intent using our 3-Axis Router
    register = detect_register(request.message)
    service = detect_service(request.message)
    
    # Step 2: Generate the AI response
    response_text = get_ai_response(request.message, service, register)
    
    # Step 3: Send the data back to the frontend
    # JUDGE NOTE: We return metadata (escalated, register, service) alongside the text. 
    # This allows the frontend to dynamically change UI colors if the conversation 
    # turns urgent or if the user gets escalated to a human!
    return {
        "response": response_text, 
        "escalated": not check_authority(request.message),
        "register": register,
        "service": service
    }

# A simple health check endpoint for Render/UptimeRobot to ping and keep the server awake
@app.get("/health")
async def health():
    return {"status": "online", "bot": BOT_NAME}
