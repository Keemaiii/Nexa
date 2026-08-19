🤖 Nexa: Your AI Chatbot Project!
Created for the ECCU / ECCB Generative AI & Python Summer Camp 2026
Made for: Outsource Development Studio, Dominica

🌟 What is Nexa?
Hey there! Nexa is an AI chatbot we built for a real company called Outsource Development Studio. Imagine a company's website is a huge library, and finding what you need is like searching for a single book in the dark. Nexa is the friendly librarian who instantly shows you where to go!

It helps visitors learn about the company's services—like helping businesses hire people, train their staff, or manage their shipping—and lets them book a meeting with a real human expert, all without leaving the chat.

🧭 The Most Important Rule
"The Bot is the GPS. The Human is the Driver."

This is our golden rule. Think of Nexa like Google Maps. It gives directions and helps you plan your route, but it never drives the car or makes the final decisions. Nexa guides people, but it never gives prices, makes deals, or handles personal info like phone numbers. That's what the humans at Outsource Development Studio are for! This makes the bot safe and trustworthy.

🚀 What Can Nexa Do? (The Cool Features)
Here's a list of the awesome features you're building:

🛡️ Safety Guards: Nexa has built-in "guardrails." If someone asks for a price or types in their email or ID number, the bot instantly recognizes it as off-limits and politely stops, saying, "A human needs to help you with that." This is super important for privacy!

⚡ Hybrid Brain: It uses two "brains." For simple questions, it has a local cheat sheet (a list of keywords and answers) that responds instantly. For more complex or unique questions, it taps into the Google Gemini AI to think and create a custom answer. (This is the "fallback" system.)

🎨 Cool, Custom UI: The user interface looks sleek and professional. It has a dark/light mode (like your phone!), custom avatars for the bot and user, and is fully responsive (works on phones and desktops). This is your HTML, CSS, and JavaScript skills at work!

🎙️ Voice Commands: You've integrated the Web Speech API, so users can ask questions by speaking and listen to the bot's answers. No third-party costs, just pure browser magic!

📅 Easy Booking: There's a seamless "Book Consultation" button that opens a form (using Jotform) right inside the chat window. Users don't have to leave the conversation to schedule a meeting.

🛠️ The Tech Stack (What We're Using)
Think of a "tech stack" as the ingredients for your recipe. Here's what we're using to build Nexa:

Category	Technology
The Website (Frontend)	HTML5, CSS3 (with cool custom variables for theming), Vanilla JavaScript
The Brain (Backend)	Python, FastAPI (a web framework), Uvicorn (a server to run it)
The AI Engine	Google Gemini API (google-genai)
Where it Lives (Deployment)	Render (a cloud hosting service)
The Design	Figma (a design tool to plan the look and feel)
The Forms	Jotform (used to create the booking iframe)
⚙️ How It Works (From Your Code to the User)
This is the journey of a single message:

A User Asks a Question: They type or speak a question into the chat box on the website (index.html).

The "Cheat Sheet" Check: The JavaScript code in your index.html first checks its localKnowledge dictionary. If the question is about a simple topic like "What is BPO?", it finds the answer instantly and replies. Boom! Zero delay.

Calling the Brain (The API): If it's not a simple question, the JavaScript sends a POST request to the /chat endpoint on your Python backend (main.py). This is like saying, "Hey Python, I need you to think about this one."

Safety Check (The Guardrail): The Python code (main.py) then performs its security checks. It scans the message for anything dangerous, like personal info (PII) or pricing questions. If it finds something, it stops immediately and sends a safe, pre-written message.

The AI Thinks: If the message is safe, main.py builds a special set of instructions (called a "prompt") and sends it, along with the user's question, to the Google Gemini AI.

The Reply: Gemini generates a smart, on-brand answer and sends it back. The Python code sends that response back to the website, where it appears in the chat with a "Listen" (Text-to-Speech) button.

💻 Running Nexa on Your Computer
Want to get this bot running on your own laptop? It's easier than you think! Follow these steps:

Grab the Code: Open your terminal (or command prompt) and type this to download a copy of the project to your computer:

bash
git clone https://github.com/Keemaiii/Nexa.git
cd Nexa
Create a Virtual Environment (Optional but Recommended): This is like giving your project its own little "bubble" so it doesn't mess with other Python projects.

bash
python3 -m venv venv
source venv/bin/activate  # On Windows, it's: venv\Scripts\activate
Install the Requirements: This command installs all the "ingredients" (libraries) your project needs, like FastAPI and the Google AI library. It reads the requirements.txt file.

bash
pip install -r requirements.txt
Set Up Your Secret Key: The AI needs a secret key to work. Create a file called .env in your project folder and add your Google Gemini API key inside it:

text
GEMINI_API_KEY="YOUR_ACTUAL_API_KEY_HERE"
(You'll get this key from Google AI Studio.)

Run the Server: Start the backend with this single command:

bash
uvicorn main:app --reload
Open Your Browser: Go to http://127.0.0.1:8000 and start chatting with your very own Nexa!

