# ==============================================================================
# local_knowledge.py - Nexa's knowledge base
# ==============================================================================
# This file contains all the pre-written responses that Nexa can give
# without calling the AI. This makes responses FAST and FREE!
# 
# 📌 HOW TO USE:
# 1. This file is imported by main.py
# 2. It provides the SERVICES dictionary and detect_service() function
# 3. You can add new services by adding them to the SERVICES dictionary
# ==============================================================================

# ==============================================================================
# 🗺️ SERVICES - All the services Nexa knows about
# ==============================================================================
# Each service has:
#   - "name": The official name
#   - "plain": A simple explanation in plain English
#   - "keywords": Words that trigger this service
#
# Example: If someone types "Tell me about BPO"
#   - "bpo" is detected because "bpo" is in the keywords
#   - Nexa knows to talk about "Business Process Outsourcing"
# ==============================================================================

SERVICES = {
    "bpo": {
        "name": "Business Process Outsourcing",
        "plain": "outsourced business services where you hire experts to handle tasks",
        "keywords": ["bpo", "outsource", "call center", "support", "outsourcing"]
    },
    "recruitment": {
        "name": "Recruitment & EOR",
        "plain": "talent acquisition and Employer of Record services",
        "keywords": ["recruit", "hire", "job", "talent", "cv", "resume", "eor", "employee"]
    },
    "training": {
        "name": "Corporate Training",
        "plain": "upskilling and UWI Cave Hill seminars",
        "keywords": ["training", "uwi", "seminar", "upskill", "course", "learn"]
    },
    "logistics": {
        "name": "Logistics & Supply Chain",
        "plain": "shipping, trucking, import/export services",
        "keywords": ["logistics", "supply chain", "shipping", "trucking", "import", "export", "freight"]
    },
    "resilience": {
        "name": "Resilience & Sustainability",
        "plain": "business continuity and climate resilience planning",
        "keywords": ["resilience", "sustainability", "climate", "disaster", "continuity", "hurricane"]
    },
    "consulting": {
        "name": "Strategic Consulting",
        "plain": "one-on-one business strategy and growth advice",
        "keywords": ["consulting", "strategy", "advice", "consultation", "advisor"]
    },
}

# ==============================================================================
# 🔍 detect_service() - Find which service the user is asking about
# ==============================================================================
# This function looks at the user's message and checks if any of the
# keywords match. If they do, it returns the service key (like "bpo").
# If nothing matches, it returns None.
# ==============================================================================

def detect_service(msg: str) -> str:
    """
    Find which service the user is asking about.
    
    Args:
        msg: The user's message (string)
    
    Returns:
        The service key (like "bpo") if found, otherwise None
    """
    # Convert to lowercase so we match "BPO" and "bpo"
    m = msg.lower()
    
    # Loop through each service in our dictionary
    for key, data in SERVICES.items():
        # Check if ANY of the keywords appear in the message
        if any(kw in m for kw in data["keywords"]):
            return key
    
    # If we didn't find anything, return None
    return None


# ==============================================================================
# 🧪 TESTING - Try it out!
# ==============================================================================
# If you run this file directly, it will test the function.
# Example: python local_knowledge.py
# ==============================================================================

if __name__ == "__main__":
    # Test messages
    test_messages = [
        "Tell me about BPO services",
        "I need to hire someone",
        "What training do you offer?",
        "Can you help with shipping?",
        "Hello how are you?"
    ]
    
    print("🧪 Testing detect_service()...")
    print("-" * 40)
    
    for msg in test_messages:
        result = detect_service(msg)
        if result:
            service = SERVICES[result]
            print(f"✅ '{msg}' → {service['name']}")
        else:
            print(f"❌ '{msg}' → No service found")
    
    print("-" * 40)
    print("📝 Add more services by editing the SERVICES dictionary above!")
