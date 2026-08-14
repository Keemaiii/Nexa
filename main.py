# ==========================================
# 🛠️ THE TOOLBOX (Importing our supplies)
# ==========================================
import streamlit as st      # Streamlit turns Python into a website!
import google.generativeai as genai # The "phone" to call the Google Gemini AI brain.
import re                   # Search tool to find hidden patterns (like emails).
import os                   # Lets us read Render's secret Environment Variables.
import time                 # For counting seconds.

# ==========================================
# 🩺 DIAGNOSTIC PANEL (temporary — remove before demo!)
# ==========================================
# This runs every time the page loads so we can see if Render is passing our secret key.
_gemini_key = st.secrets.get("GOOGLE_API_KEY") or os.environ.get("GOOGLE_API_KEY")

with st.sidebar:
    st.error("🔍 **API DEBUG PANEL**")
    if _gemini_key:
        st.success(f"✅ Gemini key detected: `{_gemini_key[:8]}...`")
    else:
        st.warning("❌ No Gemini key found in Render Environment!")
    st.caption("If you see ❌, go to Render -> Environment and add GOOGLE_API_KEY.")

# ==========================================
# 🪪 1. THE BOT'S ID CARD (Client Info)
# ==========================================
CLIENT_NAME = "Outsource Development Studio Inc."
CLIENT_LOCATION = "Roseau, Dominica"
CLIENT_PHONE = "+1 (767) 225-8606"
CLIENT_EMAIL = "admin@outsourcejobsda.com"
CLIENT_WEBSITE = "https://outsourcedevelopment.org"

# ==========================================
# 👕 2. THE BOT'S WARDROBE (Themes & Colors)
# ==========================================
THEMES = [
    {"name": "Dark Monochrome & Red", "bg_primary": "#121212", "bg_sidebar": "#1a1a1a", "bg_secondary": "#242424", "bg_tertiary": "#2d2d2d", "text_primary": "#ffffff", "text_secondary": "#a3a3a3", "accent_primary": "#ef4444", "card_bg": "#242424", "border_color": "#404040"},
    {"name": "Light Monochrome & Red", "bg_primary": "#ffffff", "bg_sidebar": "#f4f4f5", "bg_secondary": "#e4e4e7", "bg_tertiary": "#f4f4f5", "text_primary": "#18181b", "text_secondary": "#52525b", "accent_primary": "#dc2626", "card_bg": "#ffffff", "border_color": "#d4d4d8"},
    {"name": "Slate & Crimson", "bg_primary": "#0f172a", "bg_sidebar": "#1e293b", "bg_secondary": "#334155", "bg_tertiary": "#1e293b", "text_primary": "#f8fafc", "text_secondary": "#94a3b8", "accent_primary": "#991b1b", "card_bg": "#334155", "border_color": "#475569"}
]

if "theme_index" not in st.session_state:
    st.session_state.theme_index = 0
current_theme = THEMES[st.session_state.theme_index]

st.markdown(f"""
<style>
    :root {{ --bg-primary: {current_theme['bg_primary']}; --bg-sidebar: {current_theme['bg_sidebar']}; --bg-secondary: {current_theme['bg_secondary']}; --bg-tertiary: {current_theme['bg_tertiary']}; --text-primary: {current_theme['text_primary']}; --text-secondary: {current_theme['text_secondary']}; --accent-primary: {current_theme['accent_primary']}; --card-bg: {current_theme['card_bg']}; --border-color: {current_theme['border_color']}; }}
    .stApp {{ background-color: var(--bg-primary) !important; color: var(--text-primary) !important; }}
    section[data-testid="stSidebar"] {{ background-color: var(--bg-sidebar) !important; border-right: 1px solid var(--border-color); }}
    section[data-testid="stSidebar"] * {{ color: var(--text-primary) !important; }}
    .ods-badge {{ width: 56px; height: 56px; border-radius: 9999px; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 1.125rem; background-color: var(--accent-primary); margin-right: 1rem; border: 2px solid var(--text-primary); }}
    .stChatInput {{ background-color: var(--bg-secondary) !important; border: 1px solid var(--border-color) !important; }}
    .stChatInput input {{ color: var(--text-primary) !important; }}
    .chat-bubble-user {{ display: flex; justify-content: flex-end; margin-bottom: 1rem; animation: fadeIn 0.3s ease-out; }}
    .chat-bubble-user > div {{ max-width: 80%; padding: 0.75rem 1rem; border-radius: 1rem 1rem 0.25rem 1rem; background-color: var(--accent-primary); color: white; font-size: 0.95rem; font-weight: 500; }}
    .chat-bubble-bot {{ display: flex; justify-content: flex-start; margin-bottom: 1rem; animation: fadeIn 0.3s ease-out; }}
    .chat-bubble-bot > div {{ max-width: 80%; padding: 0.75rem 1rem; border-radius: 1rem 1rem 1rem 0.25rem; background-color: var(--card-bg); color: var(--text-primary); font-size: 0.95rem; border: 1px solid var(--border-color); }}
    .stButton>button {{ background-color: var(--accent-primary) !important; color: white !important; border: none !important; border-radius: 0.5rem !important; font-weight: 500 !important; width: 100%; }}
    .stButton>button:hover {{ opacity: 0.9 !important; }}
    #MainMenu {{ visibility: hidden; }} footer {{ visibility: hidden; }} .viewerBadge_container__1QSob {{ display: none; }}
    @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(8px); }} to {{ opacity: 1; transform: translateY(0); }} }}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🛡️ 3. THE BOUNCERS (Security & Guardrails)
# ==========================================
DISTRESS_TRIGGERS = {
    "grief": ["passed away", "died", "funeral", "mourning", "lost my husband", "lost my wife"],
    "panic": ["can't breathe", "can't cope", "panic attack", "mental emergency"],
    "self_harm": ["hurt myself", "end it", "no way out", "suicide"],
    "aggrieved": ["nobody listens", "you people never", "sick of this", "scam", "ruined my life"]
}

def detect_distress(msg):
    m = msg.lower()
    for category, words in DISTRESS_TRIGGERS.items():
        if any(w in m for w in words): return category
    return None

def break_glass_reply(category):
    if category == "grief": return f"I am so incredibly sorry for your loss. Please don't worry about business matters right now. Reach out to our human team at {CLIENT_EMAIL}. 🕊️"
    if category in ["self_harm", "panic"]: return "I hear you, and your safety is the most important thing. Please step away and call a local emergency hotline immediately."
    return f"I hear how frustrating this is. Let me connect you with a human right now. Please email {CLIENT_EMAIL}."

def redact_pii(text):
    text = re.sub(r'\b[\w\.-]+@[\w\.-]+\.\w+\b', '[REDACTED:EMAIL]', text)
    text = re.sub(r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b', '[REDACTED:PHONE]', text)
    text = re.sub(r'\b\d{9}\b', '[REDACTED:NIN]', text)
    return text

def check_authority(user_message):
    triggers = ["price", "cost", "fee", "salary", "contract terms", "my personal file", "my cv", "my application status", "am i eligible"]
    return not any(word in user_message.lower() for word in triggers)

def detect_register(msg):
    m = msg.lower()
    if any(w in m for w in ["passed away", "died", "funeral", "loss", "mourning"]): return "bereaved"
    if any(w in m for w in ["asap", "urgent", "emergency", "now", "immediately"]): return "urgent"
    if any(w in m for w in ["regarding", "hereby", "kindly", "formal", "contract"]): return "professional"
    return "warm"

# ==========================================
# 🧠 5. THE GEMINI BRAIN & THE MICROWAVE
# ==========================================
def setup_gemini():
    """Connects to the Google Gemini Kitchen."""
    api_key = st.secrets.get("GOOGLE_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
        # 📝 TEACHER NOTE: If your teacher specifically wants "gemini-3.1-flashlite", 
        # just change the string below to whatever exact name they gave you!
        return genai.GenerativeModel('gemini-1.5-flash') 
    return None

def build_system_prompt(register="warm"):
    tone_instructions = {
        "warm": "Be warm, encouraging, and use plain language. Add a 💛.",
        "professional": "Be formal, concise, and professional. Use 'Dear user'.",
        "urgent": "Be extremely concise, direct, and fast. No filler words. Add a ⚡.",
        "bereaved": "Open with sincere condolences. Be gentle. Never more than 2 sentences of facts. Add a 🕊️."
    }
    return f"""
    [T] TASK: You are the official AI Assistant for {CLIENT_NAME}, a consultancy in {CLIENT_LOCATION}.
    [C] CONTEXT: You help with BPO, recruitment, corporate training (UWI Cave Hill), and logistics.
    [D] DEFINED SUCCESS: The user feels guided. The bot is the GPS; the human is the driver.
    [I] INPUTS: Register: {register}. Tone Rule: {tone_instructions.get(register, tone_instructions['warm'])}
    STRICT RULES:
    1. NEVER quote pricing. Say: "Our team will provide a custom quote. Please email {CLIENT_EMAIL}."
    2. NEVER ask for personal candidate data.
    3. Translate jargon into plain language.
    """

def smart_mock_response(user_msg, register="warm"):
    """🍲 THE MICROWAVE: Fakes a smart response if the API fails!"""
    msg = user_msg.lower()
    if any(w in msg for w in ["bpo", "outsource"]): text = "We specialize in outsourced business services in Dominica."
    elif any(w in msg for w in ["training", "uwi"]): text = "We partner with UWI Cave Hill for corporate training."
    elif any(w in msg for w in ["recruit", "hire"]): text = "Our talent acquisition team connects Dominican talent with employers."
    else: text = f"I am the {CLIENT_NAME} AI. I can help with BPO, Recruitment, Training, or Logistics."
    
    if register == "bereaved": return "I am so sorry. Please don't worry about business right now. 🕊️"
    elif register == "urgent": return f"{text.upper()} ⚡ EMAIL {CLIENT_EMAIL} NOW."
    elif register == "professional": return f"Dear user — {text} Kindly contact {CLIENT_EMAIL}."
    else: return f"{text} 💛"

def safe_llm_call(user_msg, chat_history):
    """The Manager: Tries Gemini. If it fails, uses the microwave."""
    register = detect_register(user_msg)
    system_prompt = build_system_prompt(register)
    
    # Gemini likes things simple. We will stitch the history and prompt into one big text block.
    history_text = ""
    for msg in chat_history[:-1]:
        role = "User" if msg["role"] == "user" else "Bot"
        history_text += f"{role}: {msg['content']}\n"
        
    full_prompt = f"{system_prompt}\n\n{history_text}User: {user_msg}\nBot:"
    
    model = setup_gemini()
    if model:
        try:
            response = model.generate_content(full_prompt)
            return response.text
        except Exception as e:
            return smart_mock_response(user_msg, register) + f"\n\n*(Note: API fallback. Error: {type(e).__name__})*"
    else:
        return smart_mock_response(user_msg, register)

# ==========================================
# 🖥️ 6. BUILDING THE SCREEN (Streamlit UI)
# ==========================================
st.set_page_config(page_title=f"{CLIENT_NAME} Assistant", page_icon="🇩🇲", layout="wide")
if "messages" not in st.session_state: st.session_state.messages = []

with st.sidebar:
    st.markdown(f"""
    <div style="display: flex; align-items: center; margin-bottom: 1.5rem;">
        <div class="ods-badge">ODS</div>
        <div>
            <h3 style="margin: 0; font-size: 1.1rem; font-weight: 700; color: var(--text-primary);">Outsource Development Studio</h3>
            <p style="margin: 0; font-size: 0.8rem; color: var(--accent-primary); font-weight: 600;">Online • Ready to help</p>
        </div>
    </div>
    <div style="margin-bottom: 1.5rem; font-size: 0.9rem; color: var(--text-secondary); line-height: 1.6;">
        <p>📍 {CLIENT_LOCATION}</p><p>📞 {CLIENT_PHONE}</p><p>✉️ {CLIENT_EMAIL}</p>
    </div>
    <div style="border-top: 1px solid var(--border-color); padding-top: 1rem;">
        <p style="font-size: 0.85rem; font-weight: 600; margin-bottom: 0.5rem; color: var(--text-primary);">📅 Book a Consultation</p>
        <a href="mailto:{CLIENT_EMAIL}" style="display: block; text-align: center; padding: 0.6rem; background-color: var(--accent-primary); color: white; text-decoration: none; border-radius: 0.5rem; margin-bottom: 0.5rem;">Send Email</a>
        <a href="{CLIENT_WEBSITE}" target="_blank" style="display: block; text-align: center; padding: 0.6rem; background-color: var(--bg-secondary); color: var(--text-primary); text-decoration: none; border-radius: 0.5rem; border: 1px solid var(--border-color);">Visit Website</a>
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    if st.button("Cycle Colors 🔄"):
        st.session_state.theme_index = (st.session_state.theme_index + 1) % len(THEMES)
        st.rerun()

st.markdown(f"<h2 style='color: var(--text-primary);'>🤖 Welcome to {CLIENT_NAME}</h2>", unsafe_allow_html=True)

for message in st.session_state.messages:
    if message["role"] == "user":
        st.markdown(f'<div class="chat-bubble-user"><div>{message["content"]}</div></div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="chat-bubble-bot"><div>{message["content"]}</div></div>', unsafe_allow_html=True)

# ==========================================
# 🎮 7. THE GAME LOOP
# ==========================================
if prompt := st.chat_input("Ask about our services..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    distress_category = detect_distress(prompt)
    if distress_category:
        st.session_state.messages.append({"role": "assistant", "content": break_glass_reply(distress_category)})
        st.rerun()

    if not check_authority(prompt):
        st.session_state.messages.append({"role": "assistant", "content": f"For questions regarding pricing or personal files, please reach out to **{CLIENT_EMAIL}**."})
        st.rerun()

    safe_prompt = redact_pii(prompt)
    api_history = st.session_state.messages[:-1] + [{"role": "user", "content": safe_prompt}]
    
    with st.spinner("Consulting the knowledge base..."):
        response_text = safe_llm_call(safe_prompt, api_history)
        
    st.session_state.messages.append({"role": "assistant", "content": response_text})
    st.rerun()
