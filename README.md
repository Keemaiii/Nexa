# 🤖 Nexa | AI Service Navigator

> **Built for the ECCU / ECCB Generative AI & Python Summer Camp 2026**  
> *Client: Outsource Development Studio, Dominica*

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688.svg)](https://fastapi.tiangolo.com/)
[![Render](https://img.shields.io/badge/Deployed%20on-Render-45E075.svg)](https://render.com/)

---

## 🌟 Overview
**Nexa** is an intelligent, accessibility-focused AI chatbot designed to help prospective clients navigate the services of *Outsource Development Studio*. Instead of getting lost in a website, users can instantly learn about BPO, Recruitment, UWI Cave Hill Training, Logistics, and Resilience Planning, and seamlessly book a human consultation.

### 🧭 The Golden Rule
> *"The Bot is the GPS. The Human is the Driver."*  
Nexa is designed with a strict **Autonomy Ceiling**. It guides, informs, and qualifies users, but it *never* quotes prices, handles personal data, or makes final decisions. Those are safely escalated to human experts.

---

## 🚀 Key Features

- 🛡️ **Guardrails & PII Hygiene:** Features a custom A.R.T. (Authority, Register, Territory) classifier. If a user inputs sensitive data (NIN, phone, email) or asks for pricing, the system instantly redacts the PII and triggers a safe, pre-written human escalation message.
- ⚡ **Hybrid Response System:** Uses a fast, local keyword-matching knowledge base for instant answers to common questions, falling back to the Google Gemini API for complex, dynamic queries.
- 🎨 **Figma-Inspired UI:** A sleek, responsive interface featuring smooth dark/light mode toggling, custom brand avatars, and CSS variable-based theming.
- 🎙️ **Native Accessibility:** Integrated browser-based Web Speech API for both Voice-to-Text (microphone) and Text-to-Speech (speaker), ensuring the bot is usable for everyone without expensive third-party API costs.
- 📅 **Frictionless Booking:** A seamless, embedded Jotform modal that allows users to book consultations without ever leaving the chat interface.

---

## 🛠️ Tech Stack

| Category | Technologies Used |
| :--- | :--- |
| **Frontend** | HTML5, CSS3 (Custom Variables), Vanilla JavaScript |
| **Backend** | Python, FastAPI, Uvicorn |
| **AI Engine** | Google Gemini API (`google-generativeai`) |
| **Deployment** | Render (Option A: All-in-One Web Service) |
| **Design** | Figma (UI/UX Prototyping) |
| **Forms** | Jotform (Embedded via iframe) |

---

## ⚙️ How It Works (Architecture)

1. **User Input:** The user types or speaks a query into the frontend.
2. **Local Check:** The JavaScript first checks the `localKnowledge` dictionary for instant, zero-latency responses to common service questions.
3. **API Request:** If no local match is found, the frontend sends a `POST` request to the `/chat` endpoint.
4. **Guardrail Check:** The Python backend scans the message for authority triggers and PII. If detected, it redacts the data and returns a safe escalation response.
5. **AI Generation:** If the query is safe, it is passed to Google Gemini with a strict system prompt grounded in the client's actual service offerings.
6. **Response:** The formatted, safe response is returned to the UI, complete with a Text-to-Speech button.

---

## 💻 Local Development Setup

Want to run Nexa on your own machine? Follow these steps:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Keemaiii/Nexa.git
   cd Nexa
