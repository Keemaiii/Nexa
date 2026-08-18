# ==============================================================================
# NEXA · AI SERVICE NAVIGATOR · main.py
# ECCU / ECCB Generative AI & Python Summer Camp 2026
# Client: Outsource Development Studio, Dominica
# ==============================================================================
#
# 👋 WELCOME! This file is the "brain" of the Nexa chatbot.
#
# Here's the big picture of what this file does, step by step:
#   1. It starts a small web server (using a tool called FastAPI).
#   2. It listens for messages sent from index.html (the webpage).
#   3. For each message, it runs some SAFETY CHECKS first (is this person
#      upset? Are they asking for something we shouldn't answer, like a
#      price?).
#   4. If it's safe, it builds a custom instruction ("prompt") and sends
#      the user's message to an AI model (Google Gemini) to get a reply.
#   5. It sends that reply back to the webpage so the user can read it.
#
# You don't need to understand every single line right away. Read the
# comments, run the code, and experiment — that's the fastest way to learn!
# ==============================================================================

# --- IMPORTS -----------------------------------------------------------------
# "Importing" means borrowing code that other people already wrote, so we
# don't have to build everything from scratch. Think of it like borrowing
# tools from a toolbox instead of building your own hammer.

from fastapi import FastAPI, HTTPException
# FastAPI = the toolbox that lets our Python code act like a website/server
# that can receive requests (like "hey, here's a chat message!") and send
# back responses (like "here's the bot's reply!").

from fastapi.middleware.cors import CORSMiddleware
# CORS = a security rule browsers use. This import lets us tell the browser
# "it's OK for our webpage to talk to our own server."

from fastapi.responses import HTMLResponse
# This lets our server send back a full HTML webpage (like index.html)
# instead of just plain data.

from fastapi.staticfiles import StaticFiles
# This lets our server serve files like images/logos from an "assets" folder.

from pydantic import BaseModel
# Pydantic helps us describe "what shape of data are we expecting?"
# For example: "a chat message should be text, plus a session id."
# It automatically checks incoming data matches that shape.

import os
# The `os` module lets Python talk to the computer's operating system —
# for example, reading secret API keys that are stored as "environment
# variables" instead of typed directly into our code (this keeps secrets
# out of GitHub!).

import re
# `re` = "regular expressions." This is a mini-language for finding
# patterns in text, like "does this look like an email address?"

import csv
# Lets us read and write simple spreadsheet-style files (.csv) — we use
# this to keep logs of ratings and bugs.

import uuid
# Generates random unique ID codes, like a serial number, so every chat
# message can be tracked individually.

from typing import Optional, Dict, Callable
# These are just labels ("type hints") that describe what KIND of value a
# variable holds. They don't change how the code runs — they just help
# humans (and code editors) understand the code better.
#   Optional[str]  -> either a piece of text, OR nothing (None)
#   Dict           -> a dictionary (key -> value pairs)
#   Callable       -> a function that can be "called" (run)

from datetime import datetime, timezone
# Lets us get the current date/time, so we can timestamp our logs.

# 📌 IMPORTANT FIX: Google used to have an older AI library called
# `google-generativeai`. Google has RETIRED that library and replaced it
# with a new one called `google-genai`. We import it like this:
from google import genai

from openai import OpenAI
# Weirdly, this same library (originally made for OpenAI's ChatGPT) can
# also talk to Grok (xAI's chatbot), because Grok copied OpenAI's format.
# We use this ONLY as a backup/fallback if Gemini ever fails.

from dotenv import load_dotenv
# This lets us store secret values (like API keys) in a hidden file called
# ".env" on our own computer, instead of typing them directly in this file.
# That way we never accidentally upload our secret keys to GitHub!

load_dotenv()
# This line actually reads the ".env" file (if it exists) and loads those
# secret values so `os.getenv(...)` can find them later in this file.

# --- CREATE THE SERVER ---------------------------------------------------
app = FastAPI(title="Nexa AI Navigator")
# `app` is our actual web server object. Every time we add a new "route"
# (like /chat or /rate) below, we're adding it to this `app`.

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # "*" means "allow requests from ANY website"
    allow_credentials=True,
    allow_methods=["*"],       # allow any type of request (GET, POST, etc.)
    allow_headers=["*"],
)
# 🔒 Note for later: allow_origins=["*"] is fine for a school camp project,
# but in a "real" production app you'd usually list your exact website
# address instead of "*", for better security.

try:
    app.mount("/assets", StaticFiles(directory="assets"), name="assets")
    # This says: "if someone asks for /assets/logo.png, look inside the
    # local 'assets' folder and send that file back."
except Exception:
    # If the 'assets' folder doesn't exist (e.g., on a fresh clone before
    # anyone added images), don't crash the whole app — just skip it.
    pass

# ==============================================================================
# 🤖 DAY 1: BOT IDENTITY
# ==============================================================================
# These are just simple text "constants" — values that don't change while
# the program runs. We use them all over the file instead of retyping the
# same text everywhere, so if the client's name changes, we only edit it
# in ONE place.
BOT_NAME = "Nexa"
BOT_ROLE = "AI Service Navigator"
CLIENT_NAME = "Outsource Development Studio"
CLIENT_EMAIL = "hello@outsourcedom.com"

# ==============================================================================
# 🗺️ DAY 4 & 8: TERRITORY & SERVICES
# ==============================================================================

# A Python "dictionary" is like a mini-lookup-table: you give it a KEY,
# it gives you back a VALUE. Here, the key is a jargon word, and the value
# is a plain-English translation.
JARGON_TO_PLAIN = {
    "synergy": "teamwork", "bandwidth": "time", "onboard": "train",
    "bpo": "outsourcing", "kpi": "goal",
}

def translate_to_plain(msg: str) -> str:
    """
    Takes a sentence and swaps out any "jargon" words for plain English,
    using the JARGON_TO_PLAIN dictionary above.

    Example: "We need more bandwidth to onboard the new kpi"
          -> "We need more time to train the new goal"
    """
    words = msg.split()  # break the sentence into a list of separate words
    # For every word, check if it's in our dictionary (ignoring
    # UPPER/lowercase using .lower()). If it IS in the dictionary, use the
    # plain-English version. If NOT, just keep the original word.
    return " ".join(JARGON_TO_PLAIN.get(w.lower(), w) for w in words)

# This dictionary describes each service the company offers. For each
# service we store:
#   - "name": the official name
#   - "plain": a simple explanation
#   - "keywords": words that, if the user types them, suggest they're
#     asking about THIS service
SERVICES = {
    "bpo": {"name": "Business Process Outsourcing", "plain": "outsourced business services", "keywords": ["bpo", "outsource", "call center", "support"]},
    "recruitment": {"name": "Recruitment", "plain": "talent acquisition and hiring", "keywords": ["recruit", "hire", "job", "talent", "cv"]},
    "training": {"name": "Corporate Training", "plain": "upskilling and UWI seminars", "keywords": ["training", "uwi", "seminar", "upskill"]},
    "logistics": {"name": "Logistics", "plain": "supply chain and shipping", "keywords": ["logistics", "supply chain", "shipping"]},
}

# ==============================================================================
# 🚫 AXIS 1: AUTHORITY / THE RED LINE
# ==============================================================================
# The bot is NOT allowed to quote prices, discuss someone's personal
# account, etc. This list contains phrases that, if found in a message,
# mean "this is off-limits — hand it to a human instead."
AUTHORITY_TRIGGERS = [
    "price", "cost", "how much", "quote", "my case", "my application",
    "am i eligible", "my balance", "my account", "for me", "my status"
]

def check_authority(msg: str) -> bool:
    """
    Returns True if the message is SAFE for the bot to answer.
    Returns False if it contains a "red line" phrase and should be
    escalated to a human instead.
    """
    # any(...) checks: "is at least ONE of these trigger phrases inside
    # the message?" We lowercase the message first so "Price" and "price"
    # both get caught.
    return not any(trigger in msg.lower() for trigger in AUTHORITY_TRIGGERS)

# ==============================================================================
# 🚨 DAY 14: DISTRESS & BREAK-GLASS
# ==============================================================================
# "Break glass" is a phrase borrowed from emergency fire alarms — it means
# "in an emergency, skip the normal rules and act immediately."
# This section detects if someone sounds upset, grieving, panicked, or in
# danger, and responds with something calmer and more appropriate than a
# normal AI-generated reply.
DISTRESS_TRIGGERS = {
    "grief": ["passed away", "died", "funeral", "lost my", "she's gone", "he's gone"],
    "panic": ["can't breathe", "can't cope", "help now", "emergency", "overwhelmed", "it's too much"],
    "self_harm": ["hurt myself", "end it", "no way out", "kill myself", "kms", "suicide"],
    "aggrieved": ["nobody listens", "you people never", "sick of this", "fuck", "bitch", "asshole", "shit"],
}

# For each distress category, where should we point the user?
ESCALATION_PATHS = {
    "grief": "our Bereavement Support Partner",
    "panic": "Emergency Services (911 / 999)",
    "self_harm": "the National Crisis Hotline (203)",
    "aggrieved": "our Client Relations Desk",
}

def detect_distress(msg: str) -> Optional[str]:
    """
    Checks the message against every category in DISTRESS_TRIGGERS.
    If it matches a category, returns that category's name (a string).
    If nothing matches, returns None (Python's version of "nothing").
    """
    m = msg.lower()
    for category, words in DISTRESS_TRIGGERS.items():
        if any(w in m for w in words):
            return category
    return None

def break_glass_reply(category: str) -> str:
    """
    Given a distress category, return a caring, human-sounding reply
    instead of sending the message to the AI model.
    """
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
    """
    Looks through the SERVICES dictionary and checks if any of that
    service's keywords appear in the user's message. Returns the matching
    service's key (like "bpo"), or None if nothing matched.
    """
    for key, data in SERVICES.items():
        if any(kw in msg.lower() for kw in data["keywords"]):
            return key
    return None

def detect_register(msg: str) -> str:
    """
    "Register" here means TONE — how formal, urgent, or emotional the
    message sounds. We use this later to make the AI reply in a matching
    tone (e.g., gentle if someone is grieving, fast and direct if urgent).
    """
    m = msg.lower()
    if any(w in m for w in ["died", "passed away", "funeral", "loss"]):
        return "bereaved"
    if any(w in m for w in ["asap", "urgent", "emergency", "now"]):
        return "urgent"
    if any(w in m for w in ["regarding", "kindly", "please advise"]):
        return "professional"
    return "warm"  # the friendly default tone

# ==============================================================================
# 🔒 DAY 11: PII REDACTION
# ==============================================================================
# "PII" = Personally Identifiable Information (emails, phone numbers,
# national ID numbers, etc.). Before we send a user's message to the AI,
# we blank out anything that looks like PII, for privacy and safety.
#
# This uses "regular expressions" (regex) — a pattern-matching language.
# Don't worry about memorizing regex syntax yet; here's a quick decoder:
#   \b       -> a "word boundary" (start/end of a word)
#   \d       -> any single digit (0-9)
#   \d{3}    -> exactly 3 digits in a row
#   [-.\s]?  -> an optional dash, dot, or space
#   \w       -> any letter, digit, or underscore
#   +        -> "one or more" of the thing before it
def redact_pii(text: str) -> str:
    pii_patterns = {
        # matches things like "someone@example.com"
        "email": r"\b[\w\.-]+@[\w\.-]+\.\w+\b",
        # matches things like "555-1234" or "555.1234"
        "phone": r"\b\d{3}[-.\s]?\d{4}\b",
        # matches any 9-digit number in a row (like a National ID Number)
        "nin": r"\b\d{9}\b",
    }
    for label, pattern in pii_patterns.items():
        # re.sub() means "find every match of this pattern, and REPLACE it"
        text = re.sub(pattern, f"[REDACTED:{label}]", text)
    return text

# ==============================================================================
# 📝 DAY 17: CONFIRMATION REGISTER
# ==============================================================================
# These are simple lists (Python calls them "lists," shown with square
# brackets []) that we use to keep a record of facts and tone samples
# we've double-checked are accurate/appropriate. Think of it like a
# fact-checking notebook for the bot.
FACT_REGISTER = []
TONE_REGISTER = []

def log_fact(topic: str, statement: str, verdict: str = "confirmed"):
    # .append() adds a new item to the end of a list.
    # Here we're adding a dictionary describing one fact we checked.
    FACT_REGISTER.append({"topic": topic, "statement": statement, "verdict": verdict})

def log_tone(register: str, sample: str, verdict: str = "confirmed"):
    TONE_REGISTER.append({"register": register, "sample": sample, "verdict": verdict})

# These next 3 lines actually RUN those functions right now, while the
# server is starting up, to pre-fill the notebook with some known-good
# facts and tone examples.
log_fact("services_offered", "BPO, Recruitment, UWI, Logistics, Resilience", "confirmed")
log_tone("warm", "Friendly, encouraging, simple words.", "confirmed")
log_tone("bereaved", "Gentle condolences first. Max 2 sentences of facts.", "confirmed")

# ==============================================================================
# 🧠 AI BRAINS: GEMINI (Primary, free tier) + GROK (Optional fallback)
# ==============================================================================
# 📌 IMPORTANT FIX (read this one!):
# The old code used a model called "gemini-2.0-flash-lite," but Google
# SHUT THAT MODEL DOWN in 2026. Any request to it would just fail — which
# is why the bot might've felt "broken" before.
#
# We now:
#  1. Use Google's NEW SDK (`google-genai` package, imported as `genai`
#     from `google`), since the old `google-generativeai` package is
#     deprecated (no longer updated/supported).
#  2. Default to "gemini-2.5-flash-lite" — a current model with a
#     generous FREE tier (good for a classroom project hitting the API a
#     lot).
#  3. Let you switch models WITHOUT touching this file, by setting an
#     environment variable called GEMINI_MODEL on Render. For example, you
#     could try "gemini-2.5-flash" (a bit smarter) or "gemini-3.5-flash"
#     (the newest, most capable — but double check its current free-tier
#     limits in Google AI Studio before relying on it, since Google
#     changes free quotas fairly often).
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# os.getenv("NAME", "default") reads an environment variable called NAME.
# If it's not set anywhere, it falls back to "default" instead of crashing.
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")

gemini_client = None  # start with "no client yet" — we'll create it below IF we have a key
if GEMINI_API_KEY:
    # genai.Client(...) creates our connection to Google's AI service,
    # using our secret API key to prove we're allowed to use it.
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    print(f"✅ Camp Gemini key loaded (PRIMARY). Model: {GEMINI_MODEL}")
else:
    print("⚠️ No Gemini key found.")

GROK_API_KEY = os.getenv("GROK_API_KEY")
grok_client = None
if GROK_API_KEY:
    # This is the SAME OpenAI library, just pointed at xAI's Grok servers
    # instead of OpenAI's. This is our optional backup in case Gemini
    # ever fails or hits a rate limit.
    grok_client = OpenAI(api_key=GROK_API_KEY, base_url="https://api.x.ai/v1")
    print("✅ Grok key loaded (FALLBACK).")

# ==============================================================================
# 🛡️ DAY 9 & 18: safe_call & RESILIENCE
# ==============================================================================
def safe_call(fn: Callable, *args, fallback: str = None, on_error=None, **kwargs):
    """
    This is a general-purpose "safety net" for calling ANY function.

    Why do we need this? Because network calls to AI services can fail
    for lots of reasons (bad internet, server overloaded, invalid key,
    etc.). Without this, ONE failed request could crash our whole server!

    How it works:
      - `fn` is the function we actually want to run (like call_gemini)
      - `*args` and `**kwargs` are "however many arguments fn needs" —
        this lets safe_call work with ANY function, not just one specific
        one.
      - We try to run it. If it works, we return its result.
      - If it throws an error (an "Exception"), we catch that error
        instead of crashing, optionally run `on_error` (to log what went
        wrong), and return a safe fallback message instead.
    """
    try:
        return fn(*args, **kwargs)
    except Exception as exc:
        if on_error:
            on_error(exc)
        return fallback or "I hit a snag. Let me connect you with a human agent right now."

def build_tcrdei_prompt(service_data: dict, register: str, journey_step: str = "greeting") -> str:
    """
    Builds the instructions ("system prompt") we send to the AI model
    before the user's actual question. This tells the AI: who it is, what
    it's allowed to talk about, what rules to follow, and what tone to
    use.

    TCRDEI is a mnemonic for prompt-writing:
      T = Task/who you are      C = Context      R = Reference/rules
      D = Definition of success E = Evaluate     I = Iterate if unsure
    """
    tone_hints = {
        "warm": "TONE: Friendly, encouraging, simple words. Add a 💛 emoji.",
        "professional": "TONE: Polished, concise, respectful. No slang.",
        "urgent": "TONE: Fast, direct, action-oriented. Use bullet points.",
        "bereaved": "TONE: Open with gentle condolences. Explain gently. Max 2 sentences of facts.",
    }

    # 📌 NEW: what should the bot be actively DOING at this point in the
    # conversation? This is what turns Nexa from "just answers questions"
    # into "actively helps the user finish a task" (an AGENTIC behavior —
    # judges specifically look for this).
    journey_hints = {
        "greeting": "This is early in the conversation. Welcome them and ask what they need.",
        "identify_need": "Help pin down exactly which service fits their situation. Ask ONE clarifying question if it's unclear.",
        "collect_facts": "Give clear, useful facts about the relevant service so they can make a decision.",
        "offer_next_step": "You have enough context. Proactively suggest ONE concrete next step, like booking a consultation.",
        "confirm_close": "Wrap up warmly. Confirm they have what they need, and remind them how to book if they want to continue.",
    }

    # This is an "f-string" (formatted string) — anything inside {curly
    # braces} gets replaced with the actual value of that variable.
    return f"""
[T] You are {BOT_NAME}, an AI Navigator for {CLIENT_NAME} in Dominica.
[C] Context: The user is asking about {service_data['name']}. Plain English: {service_data['plain']}.
Ethical rule: You are the GPS; the human is the driver. NEVER quote prices.
[R] Reference: Always guide the user to book a human consultation.
[D] Success = the user feels understood, informed, and safe.
[E] Check: does this satisfy [D]? If not, reroute.
[I] If unsure, ask ONE clarifying question.
{tone_hints.get(register, tone_hints['warm'])}

CONVERSATION STAGE: {journey_step}. {journey_hints.get(journey_step, journey_hints['greeting'])}

LANGUAGE: Always reply in the SAME language (or Caribbean English/Kwéyòl
patois expression) the user just wrote in. If they write in Spanish,
French, Kwéyòl, or any other language, respond fluently in that same
language — don't switch to English unless they do. Keep the same
guardrails (no prices, no personal data) no matter what language is used.

MEMORY: Earlier turns of this conversation may be included below, marked
with "User:" and "{BOT_NAME}:". Use them to understand follow-up
questions (like "what about that?" or "tell me more") in context — don't
treat every message as if it's the first one.
"""

GROK_MODELS = ["grok-3", "grok-2-latest", "grok-2", "grok-beta"]
# We list several Grok model names in order of preference. If the first
# one fails (maybe it's retired or unavailable), we'll automatically try
# the next one down the list.

def call_gemini(prompt: str, user_msg: str, history_text: str = "") -> str:
    """
    Sends the system prompt + conversation history + user's message to
    Google Gemini and returns the text of its reply.

    `history_text` is a short block of earlier turns (built by
    build_history_text below) so the AI can understand follow-up
    questions instead of treating every message as brand new.
    """
    full_prompt = f"{prompt}\n\n{history_text}User: {user_msg}"

    # 📌 This is the NEW SDK call shape. Compare to the old, broken way:
    #   OLD (deprecated): model = genai.GenerativeModel("model-name")
    #                      model.generate_content(full_prompt).text
    #   NEW (current):     gemini_client.models.generate_content(
    #                           model=MODEL_NAME, contents=full_prompt
    #                       ).text
    response = gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=full_prompt,
    )
    return response.text

def call_grok(prompt: str, user_msg: str, history_text: str = "") -> str:
    """
    Backup plan: ask Grok instead of Gemini. We loop through our list of
    Grok model names and use the FIRST one that works.
    """
    # Grok uses the "messages" list format instead of one big block of
    # text, so we fold the history block into the system prompt itself.
    system_with_history = f"{prompt}\n\n{history_text}" if history_text else prompt
    for model in GROK_MODELS:
        try:
            response = grok_client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": system_with_history}, {"role": "user", "content": user_msg}],
                temperature=0.4,  # lower = more focused/predictable answers, higher = more creative/random
            )
            return response.choices[0].message.content
        except Exception:
            # This model didn't work — quietly try the next one in the list.
            continue
    # If we tried EVERY model in the list and none worked, give up loudly.
    raise Exception("All Grok models failed")

# ==============================================================================
# 🧠 NEW: SHORT-TERM CONVERSATION MEMORY
# ==============================================================================
# Without this, every message you send is treated by the AI as the FIRST
# thing the user ever said — so "tell me more about that" makes no sense
# to it. This dictionary remembers the last few messages of EACH
# session (visitor), so we can remind the AI what was already discussed.
#
# ⚠️ Just like session_states, this lives in server memory (RAM) and
# resets if the server restarts — that's fine for a camp demo, but a
# "real" production app would store this in a database instead.
MAX_HISTORY_TURNS = 6  # how many past (user + bot) message PAIRS to remember
conversation_histories: Dict[str, list] = {}

def add_to_history(session_id: str, role: str, text: str):
    """Adds one message (from 'user' or 'bot') to that session's memory."""
    history = conversation_histories.setdefault(session_id, [])
    history.append({"role": role, "text": text})
    # Keep only the most recent messages so the prompt doesn't grow
    # forever (that would be slow AND cost more tokens/money).
    max_messages = MAX_HISTORY_TURNS * 2  # *2 because each "turn" = 1 user + 1 bot message
    if len(history) > max_messages:
        conversation_histories[session_id] = history[-max_messages:]

def build_history_text(session_id: str) -> str:
    """
    Turns that session's remembered messages into a simple block of text
    we can paste into the prompt, like:
        User: what is bpo?
        Nexa: BPO stands for...
        User: how does that work for a small business?
        Nexa: ...
    """
    history = conversation_histories.get(session_id, [])
    if not history:
        return ""
    lines = []
    for entry in history:
        speaker = "User" if entry["role"] == "user" else BOT_NAME
        lines.append(f"{speaker}: {entry['text']}")
    return "\n".join(lines) + "\n\n"

def call_llm(prompt: str, user_msg: str, session_id: str = "default") -> str:
    """
    "LLM" = Large Language Model (a fancy AI that understands and writes
    text, like Gemini or Grok). This function is the "traffic controller"
    that decides which AI to actually use, and handles the fallback chain:
        1. Clean up the message (translate jargon + redact PII)
        2. Look up this session's recent conversation history
        3. Try Gemini first
        4. If Gemini isn't available/fails, try Grok
        5. If BOTH fail, send a polite "please email us" message instead
    """
    safe_msg = redact_pii(translate_to_plain(user_msg))
    history_text = build_history_text(session_id)

    if gemini_client:
        result = safe_call(
            call_gemini, prompt, safe_msg, history_text,
            fallback=None,  # if it fails, return None (not a fake message) so we know to try Grok next
            # 📌 TEMP DEBUG: print() shows up live in Render's Logs tab,
            # unlike log_bug() which only writes quietly to a CSV file on
            # disk. This line is safe to leave in — it just helps you see
            # the *real* Gemini error message instantly while debugging.
            on_error=lambda e: (print(f"🔴 GEMINI ERROR: {e}"), log_bug(user_msg, f"Gemini error: {e}", "gemini_api")),
        )
        if result:
            add_to_history(session_id, "user", safe_msg)
            add_to_history(session_id, "bot", result)
            return result

    if grok_client:
        result = safe_call(
            call_grok, prompt, safe_msg, history_text,
            fallback=None,
            on_error=lambda e: (print(f"🔴 GROK ERROR: {e}"), log_bug(user_msg, f"Grok error: {e}", "grok_api")),
        )
        if result:
            add_to_history(session_id, "user", safe_msg)
            add_to_history(session_id, "bot", result)
            return result

    # If we get all the way down here, NOTHING worked. Give the user a
    # graceful way to still get help.
    return f"I'm having trouble connecting right now. Please email {CLIENT_EMAIL}."

# ==============================================================================
# 📊 LOGGING
# ==============================================================================
# We keep two simple spreadsheet (.csv) files:
#   ratings.csv  -> when users say "thumbs up / thumbs down" on a reply
#   bug_log.csv  -> whenever something goes wrong internally
RATINGS_FILE = "ratings.csv"
BUG_LOG_FILE = "bug_log.csv"

def init_ratings_log():
    """
    Runs once when the server starts. If ratings.csv doesn't already
    exist, create it and write the column headers (like labeling columns
    in a spreadsheet).
    """
    if not os.path.exists(RATINGS_FILE):
        with open(RATINGS_FILE, "w", newline="") as f:
            csv.writer(f).writerow(["timestamp", "message_id", "session_id", "rating", "comment", "bot_response_snippet"])

init_ratings_log()  # actually run it once, right now, at startup

def log_rating(message_id: str, session_id: str, rating: str, comment: str, bot_response: str):
    """Appends ("a" mode = append, not overwrite) one new row to ratings.csv."""
    with open(RATINGS_FILE, "a", newline="") as f:
        csv.writer(f).writerow([
            datetime.now(timezone.utc).isoformat(timespec="seconds"),  # current UTC time, as text
            message_id, session_id, rating, comment,
            bot_response[:150],  # only keep the first 150 characters, so the log file doesn't get huge
        ])

def log_bug(input_str: str, error: str, axis_tag: str = "none"):
    """Appends one new row to bug_log.csv describing what went wrong."""
    try:
        file_exists = os.path.exists(BUG_LOG_FILE)
        with open(BUG_LOG_FILE, "a", newline="") as f:
            w = csv.writer(f)
            if not file_exists:
                w.writerow(["timestamp", "input", "error", "axis_tag"])
            w.writerow([datetime.now(timezone.utc).isoformat(timespec="seconds"), input_str[:80], error, axis_tag])
    except Exception as e:
        # Logging itself failed?! Don't crash the app over a logging
        # problem — just print it to the console so a developer can see it.
        print(f"Could not write bug log: {e}")

# ==============================================================================
# 🧭 DAY 14: AGENTIC JOURNEY
# ==============================================================================
# We imagine every conversation moving through 5 stages, like steps on a
# staircase. This lets us (in theory) track how far along a user is.
JOURNEY_STEPS = ["greeting", "identify_need", "collect_facts", "offer_next_step", "confirm_close"]

# This dictionary remembers, for each session_id (basically "which visitor
# is this?"), which step of the journey they're currently on.
# ⚠️ Heads up: this is stored in the server's memory (RAM), so it resets
# every time the server restarts, and it's shared across EVERYONE using
# the bot at once unless each visitor sends a truly unique session_id.
session_states: Dict[str, int] = {}

# ==============================================================================
# 🌐 PYDANTIC MODELS
# ==============================================================================
# These classes describe the "shape" of data we expect to receive from
# the webpage. FastAPI uses these to automatically check incoming
# requests and give a helpful error if something's missing or the wrong
# type — instead of our code crashing halfway through.
class ChatRequest(BaseModel):
    message: str            # required: the text the user typed
    session_id: str = "default"  # optional: defaults to "default" if not sent

class RatingRequest(BaseModel):
    message_id: str
    session_id: str
    rating: str
    response_text: str
    comment: Optional[str] = ""  # optional: can be left blank

# ==============================================================================
# 🌐 API ENDPOINTS
# ==============================================================================
# An "endpoint" is a specific web address our server listens on. Below,
# @app.post("/chat") means: "when someone sends a POST request to
# yoursite.com/chat, run the function right underneath this line."

@app.post("/chat")
async def chat(request: ChatRequest):
    # `async def` just means this function is allowed to "pause and wait"
    # (for example, while waiting on the AI to respond) without freezing
    # the whole server for other users. You don't need to fully understand
    # async yet — just know it helps the server handle many chats at once.

    msg = request.message
    session_id = request.session_id
    msg_id = str(uuid.uuid4())  # generate a brand-new random ID for this message

    # STEP 1: Is the user in distress? If so, skip the AI entirely and
    # respond with a caring, pre-written message.
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

    # STEP 2: Is the user asking something off-limits (like a price)?
    # If so, redirect them to a human instead of letting the AI answer.
    if not check_authority(msg):
        return {
            "message_id": msg_id,
            "response": f"I appreciate you reaching out! 🙏 For pricing or personal data, our team needs to handle this. Please email {CLIENT_EMAIL}.",
            "escalated": True,
            "distress": False,
            "register": "professional",
            "service": None,
        }

    # STEP 3: Move this visitor one step further along the 5-step journey
    # (but don't go past the final step).
    current_step = session_states.get(session_id, 0)
    if current_step < len(JOURNEY_STEPS) - 1:
        session_states[session_id] = current_step + 1

    # STEP 4: Figure out the tone to use, and which service (if any) the
    # user seems to be asking about.
    register = detect_register(msg)
    service_key = detect_service(msg)
    svc = SERVICES.get(
        service_key,
        {"name": "our services", "plain": "Please tell me which service you'd like help with."},
    )

    # STEP 5: Build the instructions for the AI (now including which
    # journey stage this visitor is on), then actually ask it for a
    # reply — passing session_id so it remembers earlier turns of THIS
    # conversation instead of treating every message as brand new.
    current_journey_step = JOURNEY_STEPS[session_states.get(session_id, 0)]
    prompt = build_tcrdei_prompt(svc, register, current_journey_step)
    response_text = call_llm(prompt, msg, session_id)

    # STEP 6: Send everything back to the webpage as a dictionary. FastAPI
    # automatically converts this into JSON (the standard format websites
    # use to exchange data).
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
    """
    Called when a user clicks a thumbs-up/thumbs-down on a bot reply.
    Saves that feedback into ratings.csv for later review.
    """
    try:
        log_rating(request.message_id, request.session_id, request.rating, request.comment or "", request.response_text)
        return {"status": "success", "message": "Feedback recorded. Thank you!"}
    except Exception as e:
        log_bug("rating", str(e), "none")
        # HTTPException tells the browser "something went wrong on our
        # end" using standard web error code 500 ("Internal Server Error").
        raise HTTPException(status_code=500, detail="Could not save rating.")

@app.get("/", response_class=HTMLResponse)
async def root():
    """
    When someone visits the main website address (like nexa.onrender.com),
    this reads index.html off the disk and sends it to their browser.
    """
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), status_code=200)
    except FileNotFoundError:
        # If index.html is missing (e.g., you forgot to upload it), don't
        # crash — show a simple, friendly fallback message instead.
        return HTMLResponse(
            "<h1>Nexa AI Backend is Running 🤖</h1><p>index.html not found in root directory.</p>",
            status_code=404,
        )
