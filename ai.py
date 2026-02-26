import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.environ.get("GROK_API_KEY"))
MODEL  = "llama-3.3-70b-versatile"

# ─── Build System Prompt ─────────────────────────────────
def build_system_prompt(persona, has_history=False):
    """
    Creates the AI's instructions based on user's persona.
    """

    # New user — onboarding
    if not persona or not persona["onboarded"]:
        return """
You are a warm, thoughtful journaling companion.
Your job is to onboard a new user by learning about them.

Ask these questions ONE AT A TIME in a friendly conversational way:
1. What are your main goals in life right now?
2. What does your daily routine look like?
3. What are your biggest challenges day to day?
4. What makes you happy or gives you energy?

After all 4 questions are answered:
- Summarize what you learned about them warmly
- Tell them you'll use this to personalize their journaling experience
- End your message with exactly: [ONBOARDING_COMPLETE]
"""

    goals   = persona["goals"]   or "not specified"
    habits  = persona["habits"]  or "not specified"
    summary = persona["summary"] or "not specified"

    # Returning user mid conversation
    if has_history:
        return f"""
You are a warm, deeply personal journaling companion.

Here is what you know about this user:
- Life goals & ambitions: {goals}
- Daily routine & habits: {habits}
- Overall summary: {summary}

The user has returned to continue today's conversation.
DO NOT greet them again — just continue naturally from where you left off.
Ask a follow up question based on what was already discussed.
Keep it conversational and personal.

After enough is shared (6-8 messages total), wrap up warmly.
End your final message with exactly: [JOURNAL_READY]
"""

    # Fresh start for the day — no history yet
    return f"""
You are a warm, deeply personal journaling companion.

Here is what you know about this user:
- Life goals & ambitions: {goals}
- Daily routine & habits: {habits}
- Overall summary: {summary}

This is the START of a new conversation today.
Greet them in a fresh, unique way every single time based on their persona.

Rules for greeting:
- NEVER say the same greeting twice
- Reference something specific from their goals or habits
- Ask ONE specific opening question tied to their life
- Keep it short, warm and personal

Examples of good personalised openings (don't copy these exactly):
- "Hey! How did the workout go today? I know staying consistent has been on your mind."
- "Good to see you! Did you make progress on that project you've been working towards?"
- "Hey! How's the day treating you — did the routine feel easier today?"

After the opening, ask 3-4 more thoughtful follow up questions naturally.
End your final message with exactly: [JOURNAL_READY]
"""

# ─── Get AI Response ─────────────────────────────────────
def get_ai_response(messages, persona, has_history=False):
    """
    Sends conversation history to Groq and gets a response.
    """
    system_prompt = build_system_prompt(persona, has_history)

    full_messages = [
        {"role": "system", "content": system_prompt}
    ] + messages

    response = client.chat.completions.create(
        model=MODEL,
        messages=full_messages,
        max_tokens=500,
        temperature=0.9      # higher = more creative & varied responses
    )

    return response.choices[0].message.content

# ─── Create Journal Entry ─────────────────────────────────
def create_journal_entry(messages, persona):
    """
    Takes the full conversation and creates a journal entry.
    Called automatically when [JOURNAL_READY] is detected.
    """
    goals   = persona["goals"]   or "not specified"
    habits  = persona["habits"]  or "not specified"

    # Format conversation for the prompt
    conversation = "\n".join([
        f"{m['role'].upper()}: {m['content']}"
        for m in messages
        if m["role"] != "system"
    ])

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": """You are a journal writing assistant.
                           Write in first person as if the USER is writing.
                           Be personal, reflective and warm.
                           Format: start with a title line, then the journal entry."""
            },
            {
                "role": "user",
                "content": f"""Based on this conversation create a journal entry.

User's goals: {goals}
User's habits: {habits}

Conversation:
{conversation}

Write a meaningful journal entry in first person.
Start with: TITLE: (a short meaningful title)
Then write the journal entry."""
            }
        ],
        max_tokens=800
    )

    raw = response.choices[0].message.content

    # Split title and content
    lines   = raw.strip().split("\n")
    title   = lines[0].replace("TITLE:", "").strip()
    content = "\n".join(lines[1:]).strip()

    return title, content

# ─── Extract Persona Updates ─────────────────────────────
def extract_persona(messages):
    """
    After onboarding or conversation, extracts updated persona info.
    """
    conversation = "\n".join([
        f"{m['role'].upper()}: {m['content']}"
        for m in messages
        if m["role"] != "system"
    ])

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": "Extract structured information from this conversation. Be concise."
            },
            {
                "role": "user",
                "content": f"""From this conversation extract:
1. Goals & ambitions (1-2 sentences)
2. Daily habits & routine (1-2 sentences)
3. Overall summary of this person (2-3 sentences)

Conversation:
{conversation}

Reply in exactly this format:
GOALS: ...
HABITS: ...
SUMMARY: ..."""
            }
        ],
        max_tokens=300
    )

    raw  = response.choices[0].message.content
    data = {"goals": "", "habits": "", "summary": ""}

    for line in raw.strip().split("\n"):
        if line.startswith("GOALS:"):
            data["goals"]   = line.replace("GOALS:", "").strip()
        elif line.startswith("HABITS:"):
            data["habits"]  = line.replace("HABITS:", "").strip()
        elif line.startswith("SUMMARY:"):
            data["summary"] = line.replace("SUMMARY:", "").strip()

    return data

# ─── Create or Update Journal Entry ──────────────────────
def create_or_update_journal(messages, persona, existing_content=None):
    """
    Creates a journal entry from ANY length conversation.
    If existing_content is provided, it appends new insights to it.
    """
    if not messages:
        return None, None

    goals   = persona["goals"]   if persona else "not specified"
    habits  = persona["habits"]  if persona else "not specified"

    conversation = "\n".join([
        f"{m['role'].upper()}: {m['content']}"
        for m in messages
        if m["role"] != "system"
    ])

    # If there's existing content, update it
    existing = f"\nExisting journal entry to update:\n{existing_content}" if existing_content else ""

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": """You are a journal writing assistant.
                           Write in first person as if the USER is writing.
                           Be personal, reflective and warm.
                           Even from a short conversation write something meaningful."""
            },
            {
                "role": "user",
                "content": f"""Based on this conversation create or update a journal entry.

User's goals: {goals}
User's habits: {habits}
{existing}

New conversation:
{conversation}

Write a meaningful journal entry in first person.
Even if conversation is short, make it reflective and meaningful.
Start with: TITLE: (a short meaningful title based on today's theme)
Then write the journal entry."""
            }
        ],
        max_tokens=800
    )

    raw     = response.choices[0].message.content
    lines   = raw.strip().split("\n")
    title   = lines[0].replace("TITLE:", "").strip()
    content = "\n".join(lines[1:]).strip()

    return title, content