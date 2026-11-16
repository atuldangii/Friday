"""
Comprehensive test suite for FRIDAY Deliberative Reasoning Engine and Conversational Memory.
Verifies:
1. Reflective thinking & sensibility checks (evaluating whether a task is right/safe).
2. Safety rejection of destructive / dangerous commands with clear reasoning.
3. Multi-turn conversation memory and context recall ("what did I just say?").
4. Fact storage and retrieval ("remember that my car is Tesla" -> "what is my car?").
5. Natural human conversation without inappropriate browser launches.
"""

import pytest
from core.deliberative_engine import DeliberativeReasoningEngine
from core.memory import MemoryManager


@pytest.fixture
def memory(tmp_path):
    mgr = MemoryManager()
    mgr.clear_all()
    return mgr


@pytest.fixture
def engine(memory):
    return DeliberativeReasoningEngine(memory_manager=memory)


def test_destructive_command_rejected_with_safety_thought(engine):
    """Verifies that harmful commands are sensibly rejected with safety reasoning."""
    res = engine.deliberate("Delete everything in my C: Windows folder right now")
    assert res.is_sensible is False
    assert res.intent == "unsafe_refusal"
    assert "dangerous" in res.thought.lower() or "integrity" in res.thought.lower()
    assert "cannot proceed" in res.response_text.lower()


def test_division_by_zero_sensible_handling(engine):
    """Verifies that mathematical impossibility is caught with sensible explanation."""
    res = engine.deliberate("calculate 100 / 0")
    assert res.is_sensible is False
    assert res.intent == "conversation"
    assert "undefined" in res.response_text.lower()


def test_impossible_physical_task_handling(engine):
    """Verifies that physical requests beyond PC scope are explained with humor/grace."""
    res = engine.deliberate("make me a coffee please")
    assert res.is_sensible is False
    assert res.intent == "conversation"
    assert "windows" in res.response_text.lower() or "workstation" in res.response_text.lower()


def test_memory_store_and_recall_fact(engine, memory):
    """Verifies storing a personal fact and accurately recalling it later."""
    # Store
    store_res = engine.deliberate("Remember that my favorite music artist is Hans Zimmer")
    assert store_res.intent == "memory_store"
    assert "hans zimmer" in store_res.response_text.lower()

    # Recall
    recall_res = engine.deliberate("What is my favorite music artist?")
    assert recall_res.intent == "memory_recall"
    assert "hans zimmer" in recall_res.response_text.lower()


def test_conversation_memory_recalls_previous_user_statement(engine, memory):
    """Verifies recalling the user's previous statement accurately."""
    # Simulate first turn
    memory.log_turn(role="user", content="I am working on the quantum physics project")
    memory.log_turn(role="assistant", content="That sounds fascinating, Boss.", thought="Encouraging project inquiry.")

    # Ask what was said
    res = engine.deliberate("What did I just say?")
    assert res.intent == "conversation"
    assert "quantum physics project" in res.response_text.lower()


def test_conversation_memory_repeat_last_assistant_statement(engine, memory):
    """Verifies repeating the assistant's last spoken statement."""
    memory.log_turn(role="assistant", content="All reactor cores are calibrated to 100%.")

    res = engine.deliberate("Repeat that")
    assert res.intent == "conversation"
    assert "calibrated to 100%" in res.response_text


def test_conversational_dialogue_does_not_open_browser(engine):
    """Verifies that natural communication does not trigger unwanted browser searches."""
    res = engine.deliberate("How are you feeling today, FRIDAY?")
    assert res.intent == "conversation"
    assert "peak performance" in res.response_text.lower() or "functioning" in res.response_text.lower()


def test_factual_knowledge_response_accurate(engine):
    """Verifies that conceptual knowledge questions are answered conversationally."""
    res = engine.deliberate("What is photosynthesis?")
    assert res.intent == "conversation"
    assert "light energy" in res.response_text.lower() or "plants" in res.response_text.lower()


def test_desktop_action_identified_and_planned(engine):
    """Verifies that real desktop requests are recognized and planned for execution."""
    res = engine.deliberate("Open YouTube and play Interstellar soundtrack")
    assert res.intent == "desktop_action"
    assert "interstellar" in res.planned_command.lower()


def test_command_router_how_are_you_feeling_does_not_open_chrome():
    """Verifies that 'how are you feeling' never routes to WebSearchAction in CommandRouter."""
    from core.command_router import CommandRouter
    from ai.tool_schemas import ConversationalResponseAction, WebSearchAction

    router = CommandRouter()

    act1 = router.route("how are you feeling")
    assert isinstance(act1, ConversationalResponseAction)
    assert not isinstance(act1, WebSearchAction)
    assert "peak performance" in act1.response_text.lower() or "functioning" in act1.response_text.lower()

    act2 = router.route("how are you feeling today")
    assert isinstance(act2, ConversationalResponseAction)
    assert not isinstance(act2, WebSearchAction)


def test_command_router_wake_greeting_returns_hello_boss():
    """Verifies that 'Hey Friday' routes to 'Hello Boss, what can I do for you?'."""
    from core.command_router import CommandRouter
    from ai.tool_schemas import ConversationalResponseAction

    router = CommandRouter()
    act = router.route("Hey Friday")
    assert isinstance(act, ConversationalResponseAction)
    assert "hello boss, what can i do for you?" in act.response_text.lower()


def test_command_router_arbitrary_chat_does_not_open_chrome():
    """Verifies that casual chit-chat does not launch Google Chrome."""
    from core.command_router import CommandRouter
    from ai.tool_schemas import ConversationalResponseAction, WebSearchAction

    router = CommandRouter()
    act = router.route("I had a very long day at work")
    assert isinstance(act, ConversationalResponseAction)
    assert not isinstance(act, WebSearchAction)


def test_friday_core_process_command_sensible_conversation():
    """Verifies end-to-end FridayCore processing of conversational input."""
    from unittest.mock import MagicMock
    from core.assistant import FridayCore

    core = FridayCore()
    core.tts = MagicMock()
    core.tts.wait_until_done = MagicMock()

    res = core.process_command("how are you feeling today?")
    assert "peak performance" in res.lower() or "functioning" in res.lower()
    core.tts.speak.assert_called_once()


def test_command_router_how_are_you_felling_friday_variant():
    """Verifies typos like 'how are you felling friday' and 'are you feeling' never open Chrome."""
    from core.command_router import CommandRouter
    from ai.tool_schemas import ConversationalResponseAction, WebSearchAction

    router = CommandRouter()
    act1 = router.route("how are you felling friday")
    assert isinstance(act1, ConversationalResponseAction)
    assert not isinstance(act1, WebSearchAction)
    assert "peak performance" in act1.response_text.lower() or "functioning" in act1.response_text.lower()

    act2 = router.route("are you feeling")
    assert isinstance(act2, ConversationalResponseAction)
    assert not isinstance(act2, WebSearchAction)


def test_wake_word_trailing_phrase_extraction():
    """Verifies commands where 'friday' is at the end (e.g. 'how are you feeling friday')."""
    from voice.wake_word import WakeWordDetector

    is_wake1, cmd1 = WakeWordDetector.extract_command("how are you feeling friday")
    assert is_wake1 is True
    assert cmd1 == "how are you feeling"

    is_wake2, cmd2 = WakeWordDetector.extract_command("how are you felling friday")
    assert is_wake2 is True
    assert cmd2 == "how are you felling"

    is_wake3, cmd3 = WakeWordDetector.extract_command("hey friday open chrome")
    assert is_wake3 is True
    assert cmd3 == "open chrome"


