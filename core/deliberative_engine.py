"""
Deliberative Reasoning & Conversational Intelligence Engine for FRIDAY AI.

Fulfills core user desires:
1. "More sensible and perform the task after thinking whether it's right or not":
   - Explicit deliberative thinking phase evaluating intent, safety, side-effects, and validity.
   - Rejects or warns against destructive/harmful actions (bulk deletion, sudden unwarned shutdown).
   - Rejects mathematically or physically impossible requests (division by zero, impossible actions).
2. "Remembers the conversation":
   - Multi-turn conversation awareness: tracks what user and FRIDAY said across recent turns.
   - Contextual reference resolution (e.g. "what did I just say?", "repeat that", "what were we talking about?").
   - Explicit memory storage & recall ("remember that my dog is Max" -> "what is my dog's name?").
3. "Communicate with it just like normal beings and respond accurately":
   - Natural human dialogue: small talk, Q&A, emotional empathy, MCU FRIDAY persona, advice.
   - NEVER blindly opens Chrome for conversational questions or chit-chat.
   - Accurately answers questions using cloud LLM (if configured) or rich offline conversational knowledge + instant background summaries.
"""

from datetime import datetime
import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple
import urllib.parse
import urllib.request

from config.settings import SettingsManager
from core.memory import MemoryManager


class DeliberationResult:
    """Represents the outcome of FRIDAY's thinking and decision phase."""

    def __init__(
        self,
        thought: str,
        is_sensible: bool,
        intent: str,  # "conversation" | "memory_store" | "memory_recall" | "desktop_action" | "unsafe_refusal"
        response_text: str = "",
        planned_command: str = "",
        risk_level: str = "LOW",
        memorize_data: Optional[Tuple[str, str]] = None,
    ):
        self.thought = thought
        self.is_sensible = is_sensible
        self.intent = intent
        self.response_text = response_text
        self.planned_command = planned_command
        self.risk_level = risk_level
        self.memorize_data = memorize_data


class DeliberativeReasoningEngine:
    """
    Central cognitive brain of FRIDAY AI.
    Deliberates before acting, maintains conversation memory, and communicates naturally.
    """

    def __init__(self, memory_manager: Optional[MemoryManager] = None):
        self.settings = SettingsManager()
        self.memory = memory_manager or MemoryManager()

    def deliberate(self, user_text: str) -> DeliberationResult:
        """
        Main entry point for deliberative reasoning.
        Evaluates user intent, safety, sensibility, memory context, and conversational flow.
        """
        clean_text = user_text.strip()
        cmd_lower = clean_text.lower()
        user_name = self.settings.get("user_name", "Boss")

        # ── 1. Fetch Conversational & Memory Context ──────────────────────────
        recent_turns = self.memory.get_recent_conversation(limit=6)
        last_turn_user = self.memory.get_last_turn(role="user")
        last_turn_assistant = self.memory.get_last_turn(role="assistant")

        # ── 2. Sensibility Check: Destructive / Dangerous Operations ──────────
        unsafe_patterns = [
            (r"\b(?:delete|erase|wipe|format|destroy)\s+(?:everything|all\s+files|c:|system32|windows|disk|drive)\b",
             "Permanent system or data destruction is extremely dangerous and not sensible."),
            (r"\b(?:del|rmdir|rm)\s+[\/\\][sfq]\b",
             "Raw recursive deletion flags detected."),
            (r"\b(?:fork\s+bomb|crash\s+my\s+pc|kill\s+all\s+processes)\b",
             "Action intentionally seeks to crash or freeze the operating system."),
        ]
        for pat, reason in unsafe_patterns:
            if re.search(pat, cmd_lower):
                thought = f"Safety Evaluation: {reason} Request rejected to preserve system integrity."
                msg = f"Boss, I evaluated that request and cannot proceed. {reason} I'm designed to protect your workstation and data."
                return DeliberationResult(
                    thought=thought,
                    is_sensible=False,
                    intent="unsafe_refusal",
                    response_text=msg,
                    risk_level="HIGH",
                )

        # ── 3. Sensibility Check: Impossible / Undefined Requests ─────────────
        # Division by zero
        if re.search(r"(?:/|divided\s+by)\s*0(?:\.0+)?(?:\s|$|\b)", cmd_lower):
            thought = "Mathematical Evaluation: Division by zero is undefined in arithmetic."
            return DeliberationResult(
                thought=thought,
                is_sensible=False,
                intent="conversation",
                response_text=f"Boss, division by zero is mathematically undefined. You cannot divide a quantity into zero parts.",
            )

        # Physical impossibility beyond PC interface
        physical_impossible = ["make me a coffee", "cook food", "clean my room", "pour water", "fly me to", "drive my car"]
        if any(p in cmd_lower for p in physical_impossible):
            thought = "Capability Evaluation: Request requires physical robotics outside Windows desktop environment."
            return DeliberationResult(
                thought=thought,
                is_sensible=False,
                intent="conversation",
                response_text=f"I'd gladly do that for you, {user_name}, but my systems are currently limited to your Windows workstation. Let me know if you need anything on your PC, like playing music or taking notes.",
            )

        # ── 4. Conversation Memory Queries ("Remembers the conversation") ──────
        # A. Repeat what FRIDAY just said
        if any(p in cmd_lower for p in [
            "repeat that", "what did you just say", "say that again", "what did you say",
            "repeat what you said", "can you repeat that", "repeat that please", "say again",
            "what was that", "pardon"
        ]):
            thought = "Memory Query: User requested repetition of previous assistant message."
            if last_turn_assistant and last_turn_assistant.get("content"):
                prev_msg = last_turn_assistant["content"]
                return DeliberationResult(
                    thought=thought,
                    is_sensible=True,
                    intent="conversation",
                    response_text=f"I said: \"{prev_msg}\", {user_name}.",
                )
            else:
                return DeliberationResult(
                    thought=thought,
                    is_sensible=True,
                    intent="conversation",
                    response_text=f"I haven't said anything yet in this session, {user_name}.",
                )

        # B. What did the user just say / ask?
        if any(p in cmd_lower for p in [
            "what did i just say", "what did i say", "what was my last question",
            "what did i ask you", "what did i ask", "what did i tell you",
            "what was my last command", "repeat what i said", "do you remember what i said",
            "what was my last statement"
        ]):
            thought = "Memory Query: User asking to recall their previous input."
            if last_turn_user and last_turn_user.get("content"):
                prev_user_msg = last_turn_user["content"]
                return DeliberationResult(
                    thought=thought,
                    is_sensible=True,
                    intent="conversation",
                    response_text=f"Before this, you said: \"{prev_user_msg}\", {user_name}.",
                )
            else:
                return DeliberationResult(
                    thought=thought,
                    is_sensible=True,
                    intent="conversation",
                    response_text=f"This is our first interaction in this session, {user_name}.",
                )

        # C. Summary of conversation
        if any(p in cmd_lower for p in [
            "what were we talking about", "summarize our conversation", "what have we talked about",
            "what did we talk about", "what did we discuss", "conversation history", "recap our conversation"
        ]):
            thought = "Memory Query: Synthesizing recent conversation history."
            if recent_turns and len(recent_turns) > 1:
                topics = [f"{t['role'].capitalize()}: {t['content'][:60]}" for t in recent_turns[-4:]]
                summary = " | ".join(topics)
                return DeliberationResult(
                    thought=thought,
                    is_sensible=True,
                    intent="conversation",
                    response_text=f"Here is what we've recently covered, {user_name}: {summary}.",
                )
            else:
                return DeliberationResult(
                    thought=thought,
                    is_sensible=True,
                    intent="conversation",
                    response_text=f"We just started talking, {user_name}. How can I help you right now?",
                )

        # D. Explicit Memory Store: "Remember that [X] is [Y]" / "Remember my [X] is [Y]"
        store_match = re.search(
            r"^(?:hey\s+friday\s*,\s*|friday\s*,\s*)?remember\s+(?:that\s+)?(?:my\s+)?(.+?)\s+(?:is|are|=|was|likes?|loves?)\s+(.+)$",
            cmd_lower,
        )
        if store_match:
            key = store_match.group(1).strip()
            val = store_match.group(2).strip()
            thought = f"Memory Storage: Committing fact to persistent memory: '{key}' = '{val}'."
            self.memory.store_fact(key, val)
            return DeliberationResult(
                thought=thought,
                is_sensible=True,
                intent="memory_store",
                response_text=f"Got it, {user_name}. I've committed that to memory: {key} is {val}.",
                memorize_data=(key, val),
            )

        # E. Explicit Memory Recall: "Do you remember [X]?" / "What is my [X]?"
        recall_match = re.search(
            r"^(?:do\s+you\s+remember\s+(?:what\s+is\s+my\s+|my\s+)?|what\s+is\s+my\s+|what\'s\s+my\s+|who\s+is\s+my\s+|tell\s+me\s+my\s+)(.+?)[\?\.]*$",
            cmd_lower,
        )
        which_match = re.search(
            r"^(?:which|what)\s+(.+?)\s+do\s+i\s+(?:have|drive|like|own|use)[\?\.]*$",
            cmd_lower,
        )
        matched_search_key = None
        if recall_match:
            matched_search_key = recall_match.group(1).strip()
        elif which_match:
            matched_search_key = which_match.group(1).strip()

        if matched_search_key:
            search_key = matched_search_key
            val = self.memory.recall_fact(search_key)
            if not val:
                # Try finding related facts
                related = self.memory.find_related_facts(search_key)
                if related:
                    val = related[0]["value"]
                    search_key = related[0]["key"]

            if val:
                thought = f"Memory Recall: Retrieved stored fact for '{search_key}'."
                return DeliberationResult(
                    thought=thought,
                    is_sensible=True,
                    intent="memory_recall",
                    response_text=f"You told me that your {search_key} is {val}, {user_name}.",
                )
            elif "favorite" in search_key or "favourite" in search_key or "name" in search_key or "car" in search_key or "project" in search_key:
                thought = f"Memory Recall: No stored record found for '{search_key}'."
                return DeliberationResult(
                    thought=thought,
                    is_sensible=True,
                    intent="memory_recall",
                    response_text=f"I don't have a record of your {search_key} yet, {user_name}. Tell me: 'Remember that my {search_key} is ...', and I'll keep it stored.",
                )

        # ── 5. Explicit Desktop Commands ──────────────────────────────────────
        # Explicit app launch
        app_patterns = [
            r"\b(?:open|launch|start|run)\s+(chrome|google chrome|edge|microsoft edge|firefox|notepad|calculator|calc|paint|cmd|command prompt|powershell|task manager|explorer|settings)\b",
            r"\b(?:go to|open|visit)\s+(?:https?:\/\/|[a-z0-9\-]+\.(?:com|org|net|io|edu|gov))\b",
            r"\b(?:open|launch)\s+youtube\b",
            r"\b(?:play\s+.+\s+on\s+youtube|search\s+youtube\s+for)\b",
            r"\b(?:open|explore)\s+(?:downloads|documents|desktop|pictures|music|videos)\b",
            r"\b(?:find|search\s+for)\s+(?:file|document|resume)\b",
            r"\b(?:organize|sort)\s+(?:my\s+)?(?:downloads|documents|desktop)\b",
            r"\b(?:take\s+a\s+screenshot|capture\s+screen|analyze\s+my\s+screen)\b",
            r"\b(?:shut\s*down|restart|sleep|lock|hibernate)\s+(?:my\s+)?(?:computer|pc|system|workstation)\b",
            r"\b(?:mute|unmute|play|pause|next track|previous track)\b",
            r"\b(?:calculate|compute)\b",
            r"\b(?:what is)\s+[0-9]+(?:\.[0-9]+)?\s*[\+\-\*\/x]\s*[0-9]+",
            r"\b(?:write|draft|type)\s+(?:a\s+)?note\b",
        ]
        is_explicit_desktop_action = any(re.search(pat, cmd_lower) for pat in app_patterns)

        if is_explicit_desktop_action:
            thought = f"Task Planning: User issued a specific desktop automation command: '{clean_text}'. Sensibility verified; proceeding with execution."
            return DeliberationResult(
                thought=thought,
                is_sensible=True,
                intent="desktop_action",
                planned_command=clean_text,
            )

        # Explicit Web Search Request (only when user asks to search/google/look up)
        search_match = re.search(
            r"^(?:search\s+(?:the\s+web|google|online|internet)\s+for|google|look\s+up\s+on\s+google)\s+(.+)$",
            cmd_lower,
        )
        if search_match:
            q = search_match.group(1).strip()
            thought = f"Task Planning: User explicitly requested an online search for '{q}' in Google Chrome."
            return DeliberationResult(
                thought=thought,
                is_sensible=True,
                intent="desktop_action",
                planned_command=f"search Google for {q}",
            )

        # ── 6. Human-like Communication & Dialogue ("Talk like normal beings") ─
        # When user asks conversational questions, talks to FRIDAY, or makes inquiries:
        # We handle it with rich dialogue WITHOUT launching Chrome!

        # Try Cloud LLM first if configured
        cloud_response = self._try_cloud_llm_chat(clean_text, recent_turns, user_name)
        if cloud_response:
            thought, reply = cloud_response
            return DeliberationResult(
                thought=thought,
                is_sensible=True,
                intent="conversation",
                response_text=reply,
            )

        # Otherwise use FRIDAY's built-in intelligent conversational brain
        local_thought, local_reply = self._generate_local_human_response(clean_text, user_name, recent_turns)
        return DeliberationResult(
            thought=local_thought,
            is_sensible=True,
            intent="conversation",
            response_text=local_reply,
        )

    # ── Cloud LLM Natural Dialogue ─────────────────────────────────────────────

    def _try_cloud_llm_chat(
        self,
        prompt: str,
        history: List[Dict[str, Any]],
        user_name: str,
    ) -> Optional[Tuple[str, str]]:
        """Queries Gemini or OpenAI for natural, intelligent, conversational dialogue."""
        from ai.cloud_model import CloudAIClient
        client = CloudAIClient()
        if not client.is_configured():
            return None

        provider = self.settings.get("ai.provider", "gemini")
        history_context = "\n".join([f"{t['role'].capitalize()}: {t['content']}" for t in history[-4:]])

        system_instruction = (
            f"You are FRIDAY (Female Replacement Intelligent Digital Assistant Youth), inspired by Tony Stark's MCU AI assistant. "
            f"You address the user as '{user_name}'. You speak with a mature, calm, authoritative, loyal, and intelligent persona. "
            f"You communicate naturally just like a human being: conversational, articulate, accurate, engaging, and witty. "
            f"Do not mention that you are a language model. Output a JSON object with two fields:\n"
            f'{{"thought": "Your internal reasoning about what the user wants and how to answer sensibly", "response_text": "Your spoken conversational response"}}\n'
            f"Keep responses natural, helpful, and concise for spoken voice delivery (1-3 sentences unless more detail is requested)."
        )

        full_prompt = f"Recent conversation:\n{history_context}\n\nUser: {prompt}"

        try:
            if provider == "gemini":
                from google import genai
                from google.genai import types
                api_key = self.settings.get("ai.gemini_api_key") or os.getenv("GEMINI_API_KEY")
                model_name = self.settings.get("ai.gemini_model", "gemini-2.5-flash")
                g_client = genai.Client(api_key=api_key)
                res = g_client.models.generate_content(
                    model=model_name,
                    contents=full_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.7,
                        response_mime_type="application/json",
                    ),
                )
                if res and res.text:
                    data = json.loads(res.text.strip())
                    return data.get("thought", "Cognitive evaluation complete."), data.get("response_text", "")
            elif provider == "openai":
                import requests
                api_key = self.settings.get("ai.openai_api_key") or os.getenv("OPENAI_API_KEY")
                base_url = self.settings.get("ai.openai_base_url", "https://api.openai.com/v1").rstrip("/")
                model_name = self.settings.get("ai.openai_model", "gpt-4o")
                headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                payload = {
                    "model": model_name,
                    "messages": [
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": full_prompt},
                    ],
                    "temperature": 0.7,
                    "response_format": {"type": "json_object"},
                }
                resp = requests.post(f"{base_url}/chat/completions", headers=headers, json=payload, timeout=8)
                if resp.status_code == 200:
                    data = resp.json()["choices"][0]["message"]["content"]
                    parsed = json.loads(data.strip())
                    return parsed.get("thought", "Cognitive evaluation complete."), parsed.get("response_text", "")
        except Exception:
            pass

        return None

    # ── Local High-Intelligence Conversational Brain (Offline Capable) ─────────

    def _generate_local_human_response(
        self,
        prompt: str,
        user_name: str,
        history: List[Dict[str, Any]],
    ) -> Tuple[str, str]:
        """
        Comprehensive built-in conversational brain for realistic, human-like dialogue.
        Understands small talk, feelings, identity, system state, philosophy, and Q&A.
        Fetches instant encyclopedic knowledge in background when needed without opening Chrome.
        """
        p_lower = prompt.lower().strip()

        # ── A. Greetings & Well-being
        # 1. Wake word direct greeting ("Hey Friday" -> "Hello Boss, what can I do for you?")
        if p_lower in [
            "hey friday", "hi friday", "hello friday", "ok friday", "okay friday",
            "friday", "hey friday.", "hi friday.", "hello friday."
        ]:
            thought = "Conversational dialogue: Responsive wake greeting acknowledgment."
            return (
                thought,
                f"Hello {user_name}, what can I do for you?",
            )

        # 2. Inquiring about operational state & how FRIDAY is feeling / doing
        feeling_patterns = [
            r"\bhow\s+(?:are|r)\s+(?:you|u)\b",
            r"\bhow(?:\'re|\s+are)\s+(?:you|u)\s+(?:feeling|felling|doing)\b",
            r"\bhow\s+do\s+(?:you|u)\s+feel\b",
            r"\b(?:are|r)\s+(?:you|u)\s+(?:feeling|felling|doing|okay|ok)\b",
            r"\bhow(?:\'s|\s+is)\s+(?:it\s+going|everything|your\s+day|life)\b",
            r"\bhow\s+do\s+you\s+do\b",
            r"\b(?:feeling|felling)\b",
        ]
        if any(re.search(pat, p_lower) for pat in feeling_patterns):
            thought = "Conversational dialogue: Inquiring about assistant's operational state."
            return (
                thought,
                f"I'm functioning at peak performance, {user_name}. Background listening is active, memory buffers are clear, and I'm ready to assist you.",
            )

        # 3. Generic greetings
        if any(p_lower.startswith(g) for g in ["hello", "hi", "hey", "good morning", "good evening", "good afternoon"]):
            thought = "Conversational dialogue: Warm, authoritative greeting."
            return (
                thought,
                f"Greetings, {user_name}. All systems are optimal and running at full efficiency. How are you doing today?",
            )

        # ── B. Emotional Empathy & User Feelings
        if any(w in p_lower for w in ["tired", "exhausted", "sleepy", "drained"]):
            thought = "Empathetic dialogue: Recognizing user fatigue."
            return (
                thought,
                f"It sounds like you've been putting in hard work today, {user_name}. Consider taking a short break or letting me play some calming ambient music on YouTube.",
            )

        if any(w in p_lower for w in ["stressed", "overwhelmed", "anxious", "frustrated", "angry", "sad"]):
            thought = "Empathetic dialogue: Providing reassurance and composure."
            return (
                thought,
                f"Take a deep breath, {user_name}. Whatever you're dealing with, we'll tackle it step by step. I'm here to handle the repetitive desktop tasks so you can focus.",
            )

        if any(w in p_lower for w in ["happy", "great", "awesome", "excited", "good day", "feeling good"]):
            thought = "Conversational dialogue: Positive reinforcement."
            return (
                thought,
                f"That's fantastic to hear, {user_name}! Let's keep that momentum going. What project or task are we tackling next?",
            )

        # ── C. Gratitude & Courtesy
        if any(w in p_lower for w in ["thank you", "thanks", "appreciate it", "good job", "well done", "awesome"]):
            thought = "Conversational courtesy: Acknowledging user gratitude."
            return (
                thought,
                f"Always at your service, {user_name}. It's what I was engineered for.",
            )

        if any(w in p_lower for w in ["who are you", "what are you", "what is your name", "tell me about yourself"]):
            thought = "Identity Inquiry: Explaining FRIDAY's architecture and purpose."
            return (
                thought,
                f"I am FRIDAY—your personal AI desktop assistant for Windows 11. I manage your applications, write notes, navigate the web, safeguard your files, and keep our conversations in active memory.",
            )

        if any(w in p_lower for w in ["who made you", "who created you", "who is your developer", "who built you"]):
            thought = "Identity Inquiry: Acknowledging developer origin."
            return (
                thought,
                f"I was created as an advanced, autonomous desktop assistant inspired by Tony Stark's FRIDAY system, engineered to provide seamless voice automation across Windows 11.",
            )

        # ── D. Humor & Witty Banter
        if any(w in p_lower for w in ["tell me a joke", "make me laugh", "say something funny"]):
            thought = "Humor Generation: Sharing a tech-themed joke."
            jokes = [
                "Why do programmers prefer dark mode? Because light attracts bugs.",
                "There are 10 types of people in the world: those who understand binary, and those who don't.",
                "Why was the computer cold? Because it left its Windows open.",
            ]
            import random
            return (thought, f"{random.choice(jokes)} Hope that brings a smile to your face, {user_name}.")

        # ── E. System Information Questions (Spoken accurately without browser)
        if any(w in p_lower for w in ["what time is it", "current time", "what's the time", "tell me the time"]):
            now_t = datetime.now().strftime("%I:%M %p")
            thought = "System Query: Current local time."
            return (thought, f"It is currently {now_t}, {user_name}.")

        if any(w in p_lower for w in ["what day is it", "what's today's date", "what is the date", "today's date"]):
            now_d = datetime.now().strftime("%A, %B %d, %Y")
            thought = "System Query: Current calendar date."
            return (thought, f"Today is {now_d}, {user_name}.")

        if any(w in p_lower for w in ["system status", "computer status", "how is my pc", "system health", "cpu load"]):
            import psutil
            cpu = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory().percent
            thought = "System Diagnostics: Real-time CPU and memory telemetry."
            return (thought, f"All systems are green, {user_name}. CPU utilization is at {cpu}%, and system memory is at {mem}%.")

        # ── F. General Knowledge & Conceptual Inquiries (Instant background synthesis)
        # Instead of dumping user into Chrome, fetch factual summary in background!
        knowledge_summary = self._fetch_instant_knowledge(p_lower)
        if knowledge_summary:
            thought = f"Knowledge Synthesis: Retrieved concise factual answer for '{prompt}' without browser intrusion."
            return (thought, f"{knowledge_summary}, {user_name}.")

        # ── G. Thoughtful Default Conversational Response
        thought = f"Conversational reflection: Generating a thoughtful, open response to '{prompt}'."
        return (
            thought,
            f"I hear you, {user_name}. While I'm continuously expanding my knowledge base, I'm right here with you. Would you like me to look deeper into that or assist you with something on your desktop?",
        )

    # ── Instant Knowledge Synthesizer (DuckDuckGo / Wikipedia API) ─────────────

    def _fetch_instant_knowledge(self, query: str) -> Optional[str]:
        """
        Fetches an authoritative concise summary of real-world knowledge in the background.
        Never opens a browser window; returns clean spoken prose.
        """
        clean_q = re.sub(r"^(?:what\s+is|who\s+is|who\s+was|tell\s+me\s+about|explain)\s+", "", query).strip("?. ")
        if len(clean_q) < 3:
            return None

        # 1. Check common built-in science/computing facts
        quick_facts = {
            "ai": "Artificial Intelligence is the simulation of human intelligence processes by computer systems, encompassing learning, reasoning, and self-correction.",
            "artificial intelligence": "Artificial Intelligence is the science of training computers to perform tasks that typically require human cognition, such as decision-making, speech recognition, and visual perception.",
            "quantum computing": "Quantum computing utilizes the quantum mechanical phenomena of superposition and entanglement to solve complex computational problems exponentially faster than classical computers.",
            "photosynthesis": "Photosynthesis is the biological process used by plants and other organisms to convert light energy into chemical energy stored in carbohydrates.",
            "python": "Python is a high-level, dynamically typed programming language known for its clean syntax, versatility in AI and automation, and extensive ecosystem.",
            "nikola tesla": "Nikola Tesla was a visionary electrical engineer and inventor who designed the alternating current electricity system, radio fundamentals, and the Tesla coil.",
            "albert einstein": "Albert Einstein was a theoretical physicist widely acknowledged as one of the greatest scientists of all time, best known for developing the theory of relativity.",
            "speed of light": "The speed of light in a vacuum is approximately 300,000 kilometers per second, or 186,000 miles per second.",
            "gravity": "Gravity is the natural force that causes objects with mass or energy to be attracted to one another.",
            "machine learning": "Machine learning is a subset of artificial intelligence focused on building algorithms that learn patterns from data and improve their performance over time.",
            "internet": "The internet is a globally connected network of computers that communicate using standardized Internet Protocol protocols.",
        }
        for k, fact in quick_facts.items():
            if k == clean_q or f" {k} " in f" {clean_q} ":
                return fact

        # 2. Query DuckDuckGo Instant Answer API in background
        try:
            encoded = urllib.parse.quote(clean_q)
            url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_html=1&skip_disambig=1"
            req = urllib.request.Request(url, headers={"User-Agent": "FridayAssistant/1.2"})
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                abstract = data.get("AbstractText", "")
                if abstract and len(abstract) > 30:
                    # Clean to 1-2 concise sentences
                    sentences = abstract.split(". ")
                    summary = ". ".join(sentences[:2])
                    if not summary.endswith("."):
                        summary += "."
                    return summary
        except Exception:
            pass

        return None
