"""
Tests for the dialog state machine and slot filling.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestDialogStateMachine:
    """Tests for dialog state transitions."""

    def setup_method(self):
        from backend.conversation.state_machine import DialogStateMachine, DialogState
        from backend.conversation.context import ConversationContext
        self.DialogState = DialogState
        self.sm = DialogStateMachine()
        self.ctx = ConversationContext(session_id="test-session")

    def test_initial_state_is_greeting(self):
        assert self.sm.get_state() == self.DialogState.GREETING

    def test_greeting_to_intent_detected(self):
        new_state = self.sm.transition("user_message", self.ctx)
        assert new_state == self.DialogState.INTENT_DETECTED

    def test_intent_to_slot_filling(self):
        self.sm.transition("user_message", self.ctx)  # -> INTENT_DETECTED
        new_state = self.sm.transition("slots_needed", self.ctx)
        assert new_state == self.DialogState.SLOT_FILLING

    def test_intent_to_action_when_complete(self):
        self.sm.transition("user_message", self.ctx)  # -> INTENT_DETECTED
        new_state = self.sm.transition("slots_complete", self.ctx)
        assert new_state == self.DialogState.ACTION_EXECUTION

    def test_slot_filling_retry(self):
        self.sm.transition("user_message", self.ctx)  # -> INTENT_DETECTED
        self.sm.transition("slots_needed", self.ctx)   # -> SLOT_FILLING
        new_state = self.sm.transition("slot_filled", self.ctx)
        # Can stay in SLOT_FILLING or move to ACTION_EXECUTION
        assert new_state in (self.DialogState.SLOT_FILLING, self.DialogState.ACTION_EXECUTION)

    def test_action_to_follow_up(self):
        self.sm.transition("user_message", self.ctx)
        self.sm.transition("slots_complete", self.ctx)
        new_state = self.sm.transition("response_sent", self.ctx)
        assert new_state == self.DialogState.FOLLOW_UP

    def test_follow_up_to_new_question(self):
        self.sm.transition("user_message", self.ctx)
        self.sm.transition("slots_complete", self.ctx)
        self.sm.transition("response_sent", self.ctx)
        new_state = self.sm.transition("new_question", self.ctx)
        assert new_state == self.DialogState.INTENT_DETECTED

    def test_escalation_from_any_state(self):
        new_state = self.sm.transition("escalate", self.ctx)
        assert new_state == self.DialogState.ESCALATED

    def test_terminal_state_check(self):
        self.sm.transition("escalate", self.ctx)
        assert self.sm.is_terminal()

    def test_reset(self):
        self.sm.transition("user_message", self.ctx)
        self.sm.reset()
        assert self.sm.get_state() == self.DialogState.GREETING


class TestSlotFiller:
    """Tests for slot filling engine."""

    def setup_method(self):
        from backend.conversation.slot_filler import SlotFiller
        self.filler = SlotFiller()

    def test_get_required_slots_order_status(self):
        slots = self.filler.get_required_slots("order_status")
        assert isinstance(slots, list)
        if slots:  # If order_status has required slots
            assert "order_id" in slots

    def test_needs_slot_filling(self):
        needs = self.filler.needs_slot_filling("order_status")
        assert isinstance(needs, bool)

    def test_get_missing_slots(self):
        missing = self.filler.get_missing_slots("order_status", {})
        required = self.filler.get_required_slots("order_status")
        assert len(missing) == len(required)

    def test_try_fill_slots(self):
        entities = {"order_id": "#QD-1234"}
        filled = self.filler.try_fill_slots("order_status", entities, {})
        if self.filler.needs_slot_filling("order_status"):
            assert "order_id" in filled

    def test_all_slots_filled(self):
        required = self.filler.get_required_slots("order_status")
        if required:
            filled = {slot: "test_value" for slot in required}
            assert self.filler.all_slots_filled("order_status", filled)

    def test_get_slot_prompt(self):
        required = self.filler.get_required_slots("order_status")
        if required:
            prompt = self.filler.get_slot_prompt("order_status", required[0])
            assert isinstance(prompt, str)
            assert len(prompt) > 0

    def test_unknown_intent_returns_empty(self):
        slots = self.filler.get_required_slots("nonexistent_intent")
        assert slots == [] or slots is None or len(slots) == 0

    def test_get_follow_up(self):
        follow_up = self.filler.get_follow_up("order_status")
        assert isinstance(follow_up, str)


class TestConversationContext:
    """Tests for conversation context management."""

    def setup_method(self):
        from backend.conversation.context import ConversationContext
        self.ctx = ConversationContext(session_id="test-123")

    def test_initial_state(self):
        assert self.ctx.session_id == "test-123"
        assert len(self.ctx.turns) == 0
        assert self.ctx.active_intent is None
        assert self.ctx.escalated is False
        assert self.ctx.resolved is False

    def test_add_turn(self):
        self.ctx.add_turn("user", "Hello!", intent="greeting", confidence=0.9, sentiment=0.5)
        assert len(self.ctx.turns) == 1
        assert self.ctx.turns[0]["role"] == "user"
        assert self.ctx.turns[0]["content"] == "Hello!"

    def test_sentiment_history(self):
        self.ctx.add_turn("user", "Hello!", sentiment=0.5)
        self.ctx.add_turn("user", "This is bad", sentiment=-0.7)
        trajectory = self.ctx.get_sentiment_trajectory()
        assert len(trajectory) == 2
        assert trajectory[0] == 0.5
        assert trajectory[1] == -0.7

    def test_get_recent_turns(self):
        for i in range(15):
            self.ctx.add_turn("user", f"Message {i}")
        recent = self.ctx.get_recent_turns(5)
        assert len(recent) == 5

    def test_reset_intent(self):
        self.ctx.active_intent = "order_status"
        self.ctx.filled_slots = {"order_id": "#QD-1234"}
        self.ctx.reset_intent()
        assert self.ctx.active_intent is None
        assert len(self.ctx.filled_slots) == 0

    def test_to_dict_and_back(self):
        from backend.conversation.context import ConversationContext
        self.ctx.add_turn("user", "Test message", intent="greeting")
        self.ctx.active_intent = "greeting"
        data = self.ctx.to_dict()
        restored = ConversationContext.from_dict(data)
        assert restored.session_id == "test-123"
        assert len(restored.turns) == 1
        assert restored.active_intent == "greeting"

    def test_context_summary(self):
        self.ctx.add_turn("user", "Hello!")
        self.ctx.add_turn("assistant", "Hi there!")
        summary = self.ctx.get_context_summary()
        assert isinstance(summary, str)
        assert "Hello" in summary
